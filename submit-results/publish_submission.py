#!/usr/bin/env python3
"""Check a public submission PR and prepare its paired leaderboard/News update."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from compute_scores import calculate_report, format_summary
from validate_submission import (
    DOMAIN_TRACKS,
    SUPPORTED_TRACKS,
    ValidationReport,
    default_case_metadata_path,
    format_report,
    load_results_csv,
    load_track_case_metadata,
    validate_metadata,
)

PAGE_PREFIX = "window.NATUREBENCH_DATA = "
SITE_URL = "https://frontisai.github.io/NatureBench/"
NEWS_HEADING = "## 📰News\n"
SUBMISSION_FILES = ("submission.yaml", "results.csv")
SUBMISSION_PATH = re.compile(r"submissions/([a-z0-9-]+)/([a-z0-9][a-z0-9-]{0,99})/(submission\.yaml|results\.csv)")
DISTRIBUTION_LABELS = {
    "no_score": "No score",
    "invalid": "Invalid",
    "g_lt_minus_0_5": "g < -0.5",
    "g_minus_0_5_to_0": "-0.5 <= g < 0",
    "g_0_to_0_1": "0 <= g <= 0.1",
    "g_0_1_to_0_5": "0.1 < g <= 0.5",
    "g_gt_0_5": "g > 0.5",
}
LEADERBOARD_METRICS = {
    "invalid_count": "invalid",
    "match_sota": "matchSota",
    "surpass_sota": "surpassSota",
    "mean_g_all": "meanAll",
    "median_g_all": "medianAll",
    "median_g_valid": "medianValid",
    "completion_rate": "completionRate",
    "score_rate": "scoreRate",
}


@dataclass
class Entry:
    key: str
    track: str
    revision: str
    metadata: dict
    report: dict
    scores: dict


def load_entry(directory: Path, track: str, submission_id: str) -> Entry:
    prefix = f"submissions/{track}/{submission_id}"
    if track not in SUPPORTED_TRACKS or not SUBMISSION_PATH.fullmatch(f"{prefix}/results.csv"):
        raise ValueError(f"Invalid track or submission directory: {prefix}")
    files = [directory / name for name in SUBMISSION_FILES]
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise ValueError(f"{prefix}: expected regular submission.yaml and results.csv files")
    metadata_file, results_file = files
    validation = ValidationReport()
    metadata = validate_metadata(metadata_file, validation, public_only=True)
    if validation.ok and metadata["evaluation"]["track"] != track:
        validation.error("evaluation.track must match the directory track")
    if not validation.ok:
        raise ValueError(format_report(validation))
    cases = load_track_case_metadata(default_case_metadata_path(), track)
    records = load_results_csv(results_file, cases, validation)
    if not validation.ok:
        raise ValueError(format_report(validation))
    report = calculate_report(records, cases, track)
    scores = {}
    for case_id, record in sorted(records.items()):
        state = "none" if record.best_score is None else record.judge_verdict
        scores[case_id] = {"state": state, "value": record.best_score}
    digest = hashlib.sha256()
    for path in files:
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return Entry(f"{track}/{submission_id}", track, digest.hexdigest(), metadata, report, scores)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def check_pr(base: str, head: str) -> Entry:
    for sha in (base, head):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Expected a full commit SHA for the base and head")
    paths = git("diff", "--no-renames", "--name-only", "-z", f"{base}...{head}", "--")
    changed = [path.decode("utf-8") for path in paths.split(b"\0") if path]
    matches = [SUBMISSION_PATH.fullmatch(path) for path in changed]
    if not matches or not all(matches):
        raise ValueError("A submission PR may change only its submission.yaml and results.csv")
    directories = {(match[1], match[2]) for match in matches}
    if len(directories) != 1:
        raise ValueError("A submission PR must cover one track and one submission directory")
    (track, submission_id), = directories
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for filename in SUBMISSION_FILES:
            path = f"submissions/{track}/{submission_id}/{filename}"
            tree_item = git("ls-tree", head, "--", path)
            if not tree_item.startswith(b"100644 blob "):
                raise ValueError(f"{path}: expected a regular file in the PR")
            blob = f"{head}:{path}"
            if int(git("cat-file", "-s", blob)) > 2_000_000:
                raise ValueError(f"{path}: public submission files must be under 2 MB")
            (directory / filename).write_bytes(git("show", blob))
        return load_entry(directory, track, submission_id)


def read_page(content: bytes) -> dict:
    body = content.decode("utf-8").strip()
    if not body.startswith(PAGE_PREFIX) or not body.endswith(";"):
        raise ValueError("Expected naturebench-data.js to assign window.NATUREBENCH_DATA")
    return json.loads(body[len(PAGE_PREFIX):-1])


def replace_item(items: list[dict], field: str, item: dict, previous: str | None = None) -> None:
    for index, existing in enumerate(items):
        if existing[field] == (previous or item[field]):
            items[index] = item
            return
    items.append(item)


def render_entry(page: dict, entry: Entry) -> str:
    submission, evaluation = (entry.metadata[name] for name in ("submission", "evaluation"))
    model, agent = (submission[name].strip() for name in ("model", "agent"))
    config_id = f"submission:{entry.key}"
    # The page uses name as the per-case score key, independently of the display name.
    name = f"{model} ({agent}) [{entry.key}]"
    previous = next((row["name"] for row in page["models"] if row["id"] == config_id), None)
    timeout = evaluation["timeout_seconds"]
    fallback_budget = f"{timeout // 3600} h / task" if timeout % 3600 == 0 else f"{timeout} s / task"
    fallback_access = "Web search enabled" if evaluation["web_search"] else "Web search tools disabled"
    configuration = {
        "id": config_id,
        "name": name,
        "displayName": model.removeprefix("Claude ") if model.startswith("Claude Opus ") else model,
        "agent": agent,
        "runSource": {"label": submission["organization"].strip(), "url": submission["url"].strip()},
        "setupDifferences": evaluation["setup_differences"],
        "solvingBudget": evaluation.get("solving_budget", fallback_budget),
        "compute": evaluation["compute"],
        "externalAccess": evaluation.get("external_access", fallback_access),
        "validityJudge": evaluation["judge_model"],
    }
    if evaluation["deviations_from_reference"].strip().lower() != "none":
        configuration["notes"] = evaluation["deviations_from_reference"]
    replace_item(page["models"], "id", configuration)
    metrics = entry.report["overall"]
    row = {
        "name": name,
        "harness": agent,
        "configurationId": config_id,
        **{target: metrics[key] for key, target in LEADERBOARD_METRICS.items()},
        "scores": entry.scores,
    }
    if entry.track in DOMAIN_TRACKS:
        row["tracks"] = ["domain"]
        row["domains"] = [DOMAIN_TRACKS[entry.track]]
    else:
        row["tracks"] = ["full", "naturebench-25"] if entry.track == "full" else [entry.track]
    replace_item(page["leaderboard"], "configurationId", row)
    if entry.track == "full":
        bins = [
            {"label": label, "count": metrics["distribution"][key],
             "percent": round(100 * metrics["distribution"][key] / metrics["task_count"], 1)}
            for key, label in DISTRIBUTION_LABELS.items()
        ]
        replace_item(page["distributions"], "name", {"name": name, "bins": bins}, previous)
    return config_id


def news_marker(key: str, release: dict) -> str:
    return f'<!-- naturebench-release:{key}@{release["generation"]}-{release["revision"]} -->'


def news_item(entry: Entry, publication: dict) -> str:
    submission, evaluation = (entry.metadata[name] for name in ("submission", "evaluation"))
    title = " + ".join(" ".join(submission[key].split()) for key in ("agent", "model"))
    title = html.escape(title).replace("@", "&#64;")
    title = re.sub(r"([\\`*_\[\]])", r"\\\1", title)
    labels = {"full": "Full 90-task", "naturebench-25": "NatureBench-25", **DOMAIN_TRACKS}
    if entry.track in DOMAIN_TRACKS:
        link = SITE_URL + "#domains"
    else:
        setup = "all" if evaluation["setup_differences"] else "reference"
        link = f"{SITE_URL}?track={entry.track}&setup={setup}#leaderboard"
    marker = news_marker(entry.key, publication)
    verb = "updated" if publication["correction"] else "published"
    return (
        f'- **🏆 [{publication["date"]}] We {verb} externally submitted '
        f'[results]({link}) for {title} on the {labels[entry.track]} leaderboard.** {marker}'
    )


def render_news(original: str, pending: dict) -> str:
    if not pending:
        return original
    additions = [
        release["news"] for key, release in pending.items()
        if news_marker(key, release) not in original
    ]
    if not additions:
        return original
    if original.count(NEWS_HEADING) != 1:
        raise ValueError("Expected a single News heading in the main README")
    head, section = original.split(NEWS_HEADING, 1)
    return head + NEWS_HEADING + "\n" + "\n".join(reversed(additions)) + "\n" + section.removeprefix("\n")


def prepare(
    directories: list[Path], page_path: Path, news_path: Path, plan_path: Path, today: date
) -> dict:
    entries = [load_entry(directory, directory.parent.name, directory.name) for directory in directories]
    page = read_page(page_path.read_bytes())
    original_news = news_path.read_text(encoding="utf-8")
    releases = page.get("submissionReleases", {})
    pending = {
        key: release for key, release in releases.items()
        if news_marker(key, release) not in original_news
    }
    changed = [entry for entry in entries if releases.get(entry.key, {}).get("revision") != entry.revision]
    page_changed = not pending and bool(changed)
    remaining = bool(pending and changed)
    if page_changed:
        for entry in changed:
            previous = releases.get(entry.key)
            release = {
                "revision": entry.revision,
                "generation": previous["generation"] + 1 if previous else 1,
                "date": today.isoformat(),
                "configurationId": render_entry(page, entry),
                "correction": previous is not None,
            }
            release["news"] = news_item(entry, release)
            releases[entry.key] = release
            pending[entry.key] = release
    news = render_news(original_news, pending)
    if page_changed:
        page["submissionReleases"] = releases
        rendered = PAGE_PREFIX + json.dumps(page, ensure_ascii=False, indent=2, allow_nan=False) + ";\n"
        page_path.write_text(rendered, encoding="utf-8")
    if news != original_news:
        news_path.write_text(news, encoding="utf-8")
    plan = {
        "pending": pending, "page_changed": page_changed,
        "news_changed": news != original_news, "remaining": remaining,
    }
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def update_news(plan_path: Path, news_path: Path) -> None:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    original = news_path.read_text(encoding="utf-8")
    updated = render_news(original, plan["pending"])
    if updated != original:
        news_path.write_text(updated, encoding="utf-8")


def verify_page(plan_path: Path, url: str, attempts: int = 1, delay: int = 8) -> str:
    pending = json.loads(plan_path.read_text(encoding="utf-8"))["pending"]
    if not pending:
        return "No pending publication"
    for attempt in range(attempts):
        try:
            nonce = f"?publication={time.time_ns()}" if url.startswith("https://") else ""
            with urlopen(url + nonce, timeout=15) as response:
                page = read_page(response.read())
            releases = page.get("submissionReleases", {})
            row_ids = {row["configurationId"] for row in page["leaderboard"] if "configurationId" in row}
            if all(
                releases.get(key) == release and release["configurationId"] in row_ids
                for key, release in pending.items()
            ):
                return f"Verified {len(pending)} already prepared leaderboard release(s) online"
        except (OSError, URLError, ValueError):
            pass
        if attempt < attempts - 1:
            time.sleep(delay)
    raise ValueError("Expected leaderboard revision is not live")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check-pr")
    check.add_argument("--base", required=True)
    check.add_argument("--head", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("--submissions", required=True, type=Path)
    build.add_argument("--page", required=True, type=Path)
    build.add_argument("--news", required=True, type=Path)
    build.add_argument("--plan", required=True, type=Path)
    news = commands.add_parser("update-news")
    news.add_argument("--plan", required=True, type=Path)
    news.add_argument("--news", required=True, type=Path)
    verify = commands.add_parser("verify-page")
    verify.add_argument("--plan", required=True, type=Path)
    verify.add_argument("--url", required=True)
    verify.add_argument("--attempts", type=int, default=1)
    args = parser.parse_args()
    try:
        if args.command == "check-pr":
            entry = check_pr(args.base, args.head)
            print(f"Submission: {entry.key}\n{format_summary(entry.report)}")
        elif args.command == "prepare":
            directories = sorted({path.parent for path in args.submissions.glob("*/*/submission.yaml")})
            plan = prepare(directories, args.page, args.news, args.plan, datetime.now(timezone.utc).date())
            print(f"Prepared {len(plan['pending'])} paired leaderboard and News update(s)")
        elif args.command == "update-news":
            update_news(args.plan, args.news)
        else:
            print(verify_page(args.plan, args.url, args.attempts))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
