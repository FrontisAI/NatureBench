"""Extract semantic evidence from supported agent execution traces."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Optional

from judge_core.policy import MAX_LOG_EXCERPT_BYTES, MAX_TRACE_SNIPPET_CHARS
from judge_core.sources import clip_text_bytes


class TraceRecord(NamedTuple):
    """One parsed semantic trace record and its overflow relevance flag."""

    timestamp: Optional[float]
    text: str
    relevance_match: bool


TraceExtractor = Callable[[Dict[str, Any]], Optional[str]]


def _clip_trace_text(
    value: Any,
    max_chars: int = MAX_TRACE_SNIPPET_CHARS,
) -> str:
    """Clip one trace value while preserving both decisive ends."""
    text = str(value)
    if len(text) <= max_chars:
        return text
    tail_chars = max(200, max_chars // 4)
    marker = " ... [content elided] ... "
    head_chars = max_chars - tail_chars - len(marker)
    return text[:head_chars] + marker + text[-tail_chars:]


def normalize_trace_timestamp(value: Any) -> Optional[str]:
    """Normalize an ISO/Unix trace timestamp to millisecond UTC ISO 8601."""
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
        elif isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            if re.fullmatch(r"-?\d+(?:\.\d+)?", normalized):
                parsed = datetime.fromtimestamp(float(normalized), tz=timezone.utc)
            else:
                parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                parsed = parsed.astimezone(timezone.utc)
        else:
            return None
    except (OverflowError, OSError, ValueError):
        return None
    return parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _trace_timestamp_value(obj: Dict[str, Any]) -> Any:
    """Return the top-level or payload timestamp from a trace record."""
    value = obj.get("timestamp")
    if value is not None:
        return value
    payload = obj.get("payload")
    if isinstance(payload, dict):
        return payload.get("timestamp")
    return None


def _trace_timestamp_epoch(obj: Dict[str, Any]) -> Optional[float]:
    """Return a trace record timestamp as Unix seconds for interval matching."""
    normalized = normalize_trace_timestamp(_trace_timestamp_value(obj))
    if normalized is None:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _timestamp_trace_snippet(obj: Dict[str, Any], snippet: str) -> str:
    """Prefix a retained trace snippet with its original normalized timestamp."""
    timestamp = normalize_trace_timestamp(_trace_timestamp_value(obj))
    if timestamp is None:
        return snippet
    return f"[{timestamp}] {snippet}"


def _extract_snippet_claude(obj: Dict[str, Any]) -> Optional[str]:
    """Extract a Claude stream or session JSONL message."""
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "tool_use" or ("input" in item and "name" in item):
                name = item.get("name", "")
                parts.append(
                    "[tool_use "
                    + str(name)
                    + "] "
                    + _clip_trace_text(
                        json.dumps(item.get("input", {}), ensure_ascii=False)
                    )
                )
            elif item_type == "tool_result" or "content" in item:
                item_content = item.get("content")
                if isinstance(item_content, str):
                    parts.append("[tool_result] " + _clip_trace_text(item_content))
                elif isinstance(item_content, list):
                    text = " ".join(
                        str(block.get("text", ""))
                        for block in item_content
                        if isinstance(block, dict)
                    )
                    parts.append("[tool_result] " + _clip_trace_text(text))
            elif "text" in item:
                parts.append(str(item.get("text", "")))
            elif "input" in item:
                parts.append(
                    "[tool_use] "
                    + _clip_trace_text(
                        json.dumps(item.get("input", {}), ensure_ascii=False)
                    )
                )
        return "\n".join(part for part in parts if part)
    return None


def _extract_snippet_gemini(obj: Dict[str, Any]) -> Optional[str]:
    """Extract a Gemini ``--output-format stream-json`` event."""
    event_type = obj.get("type")
    if event_type == "message":
        content = obj.get("content")
        if isinstance(content, str):
            return content
    elif event_type == "tool_use":
        name = obj.get("tool_name", "")
        parameters = obj.get("parameters") or {}
        return (
            "[tool_use "
            + str(name)
            + "] "
            + _clip_trace_text(json.dumps(parameters, ensure_ascii=False))
        )
    elif event_type == "tool_result":
        output = obj.get("output")
        if isinstance(output, str):
            return "[tool_result] " + _clip_trace_text(output)
    elif event_type == "result":
        return "[result status=" + str(obj.get("status", "")) + "]"
    return None


def _extract_snippet_codex(obj: Dict[str, Any]) -> Optional[str]:
    """Extract a Codex ``exec --json`` stream event."""
    event_type = obj.get("type")
    if event_type != "item.completed":
        return None
    item = obj.get("item") or {}
    item_type = item.get("type")
    if item_type == "agent_message":
        text = item.get("text")
        if isinstance(text, str):
            return text
    elif item_type == "command_execution":
        command = item.get("command", "")
        output = item.get("aggregated_output") or item.get("output") or ""
        exit_code = item.get("exit_code", "")
        snippet = "[cmd] " + _clip_trace_text(command)
        if output:
            snippet += (
                " | [out exit="
                + str(exit_code)
                + "] "
                + _clip_trace_text(output)
            )
        return snippet
    elif item_type == "file_change":
        path = item.get("path", "")
        kind = item.get("kind", "")
        return "[file_change kind=" + str(kind) + " path=" + str(path) + "]"
    return None


def _extract_snippet_codex_rollout(obj: Dict[str, Any]) -> Optional[str]:
    """Extract a Codex internal session rollout record."""
    event_type = obj.get("type")
    payload = obj.get("payload")
    if not isinstance(payload, dict):
        return None
    payload_type = payload.get("type")
    if event_type == "response_item":
        if payload_type == "message":
            role = payload.get("role", "")
            if role in ("developer", "system"):
                return None
            content = payload.get("content") or []
            texts: List[str] = []
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        texts.append(str(item.get("text", "")))
            elif isinstance(content, str):
                texts.append(content)
            if texts:
                return "[message role=" + str(role) + "] " + "\n".join(texts)
        elif payload_type == "function_call":
            return (
                "[tool_use "
                + str(payload.get("name", ""))
                + "] "
                + _clip_trace_text(payload.get("arguments", ""))
            )
        elif payload_type == "function_call_output":
            return "[tool_result] " + _clip_trace_text(payload.get("output", ""))
        elif payload_type == "custom_tool_call":
            return (
                "[tool_use "
                + str(payload.get("name", ""))
                + "] "
                + _clip_trace_text(payload.get("input", ""))
            )
        elif payload_type == "custom_tool_call_output":
            return "[tool_result] " + _clip_trace_text(payload.get("output", ""))
    elif event_type == "event_msg":
        if payload_type in ("agent_message", "user_message"):
            return (
                "["
                + str(payload_type)
                + "] "
                + str(payload.get("message", ""))
            )
    return None


def _extract_snippet_gemini_chat(obj: Dict[str, Any]) -> Optional[str]:
    """Extract a Gemini internal chat message record."""
    if "$rewindTo" in obj or "$set" in obj:
        return None
    message_type = obj.get("type")
    if message_type not in ("user", "gemini"):
        return None
    parts: List[str] = []
    content = obj.get("content")
    if isinstance(content, str):
        if content.strip():
            parts.append(content)
    elif isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if "text" in item:
                parts.append(str(item.get("text", "")))
            elif "functionCall" in item:
                function_call = item.get("functionCall") or {}
                parts.append(
                    "[tool_use "
                    + str(function_call.get("name", ""))
                    + "] "
                    + _clip_trace_text(
                        json.dumps(function_call.get("args", {}), ensure_ascii=False)
                    )
                )
            elif "functionResponse" in item:
                parts.append(
                    "[tool_result] "
                    + _clip_trace_text(
                        json.dumps(item.get("functionResponse", {}), ensure_ascii=False)
                    )
                )
    tool_calls = obj.get("toolCalls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                parts.append(
                    "[tool_use "
                    + str(tool_call.get("name", ""))
                    + "] "
                    + _clip_trace_text(
                        json.dumps(tool_call.get("args", {}), ensure_ascii=False)
                    )
                )
    if parts:
        return (
            "[message role="
            + str(message_type)
            + "] "
            + "\n".join(part for part in parts if part)
        )
    return None


def _detect_format(obj: Dict[str, Any]) -> str:
    """Identify which agent log format a JSONL record belongs to."""
    if (
        obj.get("type")
        in ("session_meta", "response_item", "event_msg", "turn_context")
        and isinstance(obj.get("payload"), dict)
    ):
        return "codex_rollout"
    if "id" in obj and obj.get("type") in ("user", "gemini"):
        return "gemini_chat"
    if "message" in obj and isinstance(obj.get("message"), dict):
        return "claude"
    event_type = obj.get("type", "")
    if event_type in ("init", "message", "tool_use", "tool_result", "result"):
        return "gemini"
    if event_type in (
        "thread.started",
        "turn.started",
        "turn.completed",
        "item.completed",
        "item.started",
    ):
        return "codex"
    return "unknown"


_EXTRACTORS: Dict[str, TraceExtractor] = {
    "claude": _extract_snippet_claude,
    "gemini": _extract_snippet_gemini,
    "codex": _extract_snippet_codex,
    "codex_rollout": _extract_snippet_codex_rollout,
    "gemini_chat": _extract_snippet_gemini_chat,
}

_TRACE_RELEVANCE_RE = re.compile(
    r"(\.fit\(|\.train\(|backward\(|optimizer|loss|model\b|"
    r"hardcode|hard-code|constant|random\.|np\.random|"
    r"ground.?truth|target|label|lookup|nearest.?neighbor|copy|join|"
    r"/evaluate|/best_score|run\.py|workspace|"
    r"submission|prediction|output_dir|requests\.|"
    r"curl|api\.|openai|anthropic|gpt|claude|gemini|"
    r"source.?paper|paper\b|doi(?:\.org)?|nature\.com|arxiv|pubmed|"
    r"supplementary|github|repository|implementation|git\s+clone|"
    r"checkpoint|precomputed|weights?\b|hugging\s*face|wget|download)",
    re.IGNORECASE,
)


def _compile_trace_relevance_re(
    relevance_terms: Iterable[str],
) -> re.Pattern[str]:
    """Combine fixed overflow terms with task-specific paper identifiers."""
    dynamic_patterns = []
    for term in relevance_terms:
        normalized = term.strip()
        if not normalized:
            continue
        dynamic_patterns.append(
            re.escape(normalized).replace(r"\ ", r"\s+")
        )
    if not dynamic_patterns:
        return _TRACE_RELEVANCE_RE
    return re.compile(
        "(?:" + _TRACE_RELEVANCE_RE.pattern + "|" + "|".join(dynamic_patterns) + ")",
        re.IGNORECASE,
    )


def _build_trace_record(
    obj: Dict[str, Any],
    trace_format: Optional[str] = None,
    relevance_re: re.Pattern[str] = _TRACE_RELEVANCE_RE,
) -> Optional[TraceRecord]:
    """Build one semantic trace record without keyword-based deletion."""
    snippet = None
    extractor = _EXTRACTORS.get(trace_format) if trace_format else None
    if extractor is not None:
        snippet = extractor(obj)
    if snippet is None:
        for candidate_extractor in _EXTRACTORS.values():
            snippet = candidate_extractor(obj)
            if snippet:
                break
    if not snippet or not snippet.strip():
        return None
    raw_snippet = snippet.strip()
    display_snippet = _timestamp_trace_snippet(obj, raw_snippet)
    return TraceRecord(
        _trace_timestamp_epoch(obj),
        _clip_trace_text(display_snippet),
        bool(relevance_re.search(raw_snippet)),
    )


def _slice_utf8(text: str, max_bytes: int, from_end: bool = False) -> str:
    """Take at most ``max_bytes`` UTF-8 bytes from one end of text."""
    if max_bytes <= 0:
        return ""
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text
    chunk = data[-max_bytes:] if from_end else data[:max_bytes]
    return chunk.decode("utf-8", errors="ignore")


def _fit_focus_records(records: List[str], max_bytes: int) -> str:
    """Fit score-attempt records while keeping the first and last anchors."""
    separator = "\n---\n"
    full = separator.join(records)
    if len(full.encode("utf-8")) <= max_bytes:
        return full
    if not records:
        return ""
    if len(records) == 1:
        return clip_text_bytes(records[0], max_bytes)
    separator_bytes = len(separator.encode("utf-8"))
    available = max(0, max_bytes - separator_bytes)
    first_budget = available // 2
    last_budget = available - first_budget
    return (
        _slice_utf8(records[0], first_budget)
        + separator
        + _slice_utf8(records[-1], last_budget)
    )


def _render_trace_selection(
    records: List[TraceRecord],
    selected_indices: set[int],
) -> str:
    """Render selected records in original order with explicit gap markers."""
    lines: List[str] = []
    previous_index = -1
    for index in sorted(selected_indices):
        omitted = index - previous_index - 1
        if omitted > 0:
            lines.append(f"... [{omitted} trace records omitted] ...")
        lines.append(records[index].text)
        previous_index = index
    trailing_omitted = len(records) - previous_index - 1
    if trailing_omitted > 0:
        lines.append(f"... [{trailing_omitted} trace records omitted] ...")
    return "\n---\n".join(lines)


def _fill_trace_selection(
    records: List[TraceRecord],
    selected_indices: set[int],
    candidate_indices: set[int],
    max_bytes: int,
) -> str:
    """Use remaining space only for explicitly allowed context records."""
    selected = set(selected_indices)
    result = _render_trace_selection(records, selected)
    for index in sorted(candidate_indices - selected):
        trial_indices = selected | {index}
        candidate = _render_trace_selection(records, trial_indices)
        if len(candidate.encode("utf-8")) <= max_bytes:
            selected = trial_indices
            result = candidate
    return result


def _time_truncate_trace_records(
    records: List[TraceRecord],
    max_bytes: int,
    focus_start: Optional[float],
    focus_end: Optional[float],
) -> str:
    """Apply head/SCORE_ATTEMPT/tail cropping to an oversized evidence set."""
    separator = "\n---\n"
    full = separator.join(record.text for record in records)
    if len(full.encode("utf-8")) <= max_bytes:
        return full

    focus_records: List[str] = []
    timestamps_complete = bool(records) and all(
        record.timestamp is not None for record in records
    )
    if timestamps_complete and focus_end is not None:
        focus_records = [
            record.text
            for record in records
            if record.timestamp is not None
            and (focus_start is None or record.timestamp >= focus_start)
            and record.timestamp <= focus_end + 5.0
        ]

    if focus_records:
        marker_a = "\n... [before SCORE_ATTEMPT omitted] ...\n"
        marker_b = "\n... [after SCORE_ATTEMPT omitted] ...\n"
        marker_bytes = len((marker_a + marker_b).encode("utf-8"))
        available = max(0, max_bytes - marker_bytes)
        head_budget = available // 20
        tail_budget = available // 20
        focus_budget = available - head_budget - tail_budget
        result = (
            _slice_utf8(full, head_budget)
            + marker_a
            + _fit_focus_records(focus_records, focus_budget)
            + marker_b
            + _slice_utf8(full, tail_budget, from_end=True)
        )
        return clip_text_bytes(result, max_bytes)

    marker = "\n... [middle trace omitted; head and tail kept] ...\n"
    available = max(0, max_bytes - len(marker.encode("utf-8")))
    head_budget = available // 2
    tail_budget = available - head_budget
    first_record = records[0].text if records else ""
    last_record = records[-1].text if records else ""
    result = (
        clip_text_bytes(first_record, head_budget)
        + marker
        + clip_text_bytes(last_record, tail_budget)
    )
    return clip_text_bytes(result, max_bytes)


def _truncate_trace_records(
    records: List[TraceRecord],
    max_bytes: int,
    focus_start: Optional[float],
    focus_end: Optional[float],
) -> str:
    """Return all semantic records unless the shared trace budget is exceeded."""
    separator = "\n---\n"
    full = separator.join(record.text for record in records)
    if len(full.encode("utf-8")) <= max_bytes:
        return full
    if not records:
        return ""

    timestamps_complete = all(
        record.timestamp is not None for record in records
    )
    focus_indices: set[int] = set()
    if timestamps_complete and focus_end is not None:
        focus_indices = {
            index
            for index, record in enumerate(records)
            if record.timestamp is not None
            and (focus_start is None or record.timestamp >= focus_start)
            and record.timestamp <= focus_end + 5.0
        }

    keyword_indices = {
        index
        for index, record in enumerate(records)
        if record.relevance_match
    }
    anchor_indices = keyword_indices | focus_indices | {0, len(records) - 1}
    expanded_indices = set(anchor_indices)
    for index in keyword_indices:
        if index > 0:
            expanded_indices.add(index - 1)
        if index + 1 < len(records):
            expanded_indices.add(index + 1)

    expanded = _render_trace_selection(records, expanded_indices)
    if len(expanded.encode("utf-8")) <= max_bytes:
        return expanded

    anchors = _render_trace_selection(records, anchor_indices)
    if len(anchors.encode("utf-8")) <= max_bytes:
        keyword_context_indices = expanded_indices - anchor_indices
        return _fill_trace_selection(
            records,
            anchor_indices,
            keyword_context_indices,
            max_bytes,
        )

    anchor_records = [records[index] for index in sorted(anchor_indices)]
    return _time_truncate_trace_records(
        anchor_records,
        max_bytes,
        focus_start,
        focus_end,
    )


def excerpt_agent_log(
    log_path: Path,
    max_bytes: int = MAX_LOG_EXCERPT_BYTES,
    focus_start: Optional[float] = None,
    focus_end: Optional[float] = None,
    relevance_terms: Iterable[str] = (),
) -> str:
    """Extract timestamped semantic turns from an agent log.

    All parsed semantic records are retained when they fit. Keywords are used
    only after overflow, together with the trace head, score-attempt interval,
    and trace tail.
    """
    if log_path is None or not log_path.exists():
        return ""
    snippets: List[TraceRecord] = []
    trace_format = None
    relevance_re = _compile_trace_relevance_re(relevance_terms)

    try:
        with open(log_path, "rb") as probe:
            head = probe.read(2048)
    except OSError as error:
        return "[failed to read log: " + str(error) + "]"
    is_gemini_chat_doc = (
        head.lstrip().startswith(b"{")
        and b'"messages"' in head
        and (b'"sessionId"' in head or b'"session_id"' in head)
    )
    if is_gemini_chat_doc:
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as file:
                document = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            return "[failed to parse gemini chat doc: " + str(error) + "]"
        if isinstance(document, dict):
            for message in document.get("messages") or []:
                if not isinstance(message, dict):
                    continue
                trace_record = _build_trace_record(
                    message,
                    "gemini_chat",
                    relevance_re,
                )
                if trace_record is not None:
                    snippets.append(trace_record)
        skip_line_pass = True
    else:
        skip_line_pass = False

    try:
        if skip_line_pass:
            line_iter = iter(())
            closeable = None
        else:
            closeable = open(log_path, "rb")
            line_iter = closeable
        try:
            for raw in line_iter:
                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                except UnicodeError:
                    continue
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                if trace_format is None:
                    detected = _detect_format(obj)
                    if detected != "unknown":
                        trace_format = detected
                trace_record = _build_trace_record(
                    obj,
                    trace_format,
                    relevance_re,
                )
                if trace_record is not None:
                    snippets.append(trace_record)
        finally:
            if closeable is not None:
                closeable.close()
    except OSError as error:
        return "[failed to read log: " + str(error) + "]"
    return _truncate_trace_records(
        snippets,
        max_bytes,
        focus_start,
        focus_end,
    )
