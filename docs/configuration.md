# Configuration: Agents, Network, and Evaluation Service

## Agent and Network Configuration

NatureBench starts the agent CLI inside Docker containers. Before running, prepare the corresponding authentication method and network access on the host.

### Claude Code

The public release pipeline uses environment variables for Claude Code. After they are set on the host, `solve.py` passes them into task containers:

```bash
export ANTHROPIC_API_KEY=...
export ANTHROPIC_BASE_URL=...
```

This release does not provide mounting logic for official Claude Code web login state. To use Claude Code, use the API environment variables above or extend the container-side CLI login-state handling yourself.

### Codex CLI

Codex supports two authentication modes.

**device-auth login**

First complete official login once on the host:

```bash
codex login --device-auth
ls ~/.codex/auth.json
```

Use the following runtime parameters:

```bash
--agent codex \
--codex-auth-mode device-auth \
--codex-auth-dir ~/.codex
```

`--codex-auth-dir` defaults to the host `~/.codex`. The pipeline copies `auth.json` (and `config.toml` if present) into a per-task `.codex_state/` and writes new sessions to that task's result directory.

**API-key mode**

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=...
```

Add this runtime parameter:

```bash
--codex-auth-mode api-key
```

### Gemini CLI

The public release pipeline uses environment variables for Gemini CLI:

```bash
export GEMINI_API_KEY=...
export GOOGLE_GEMINI_BASE_URL=...
```

This release does not provide unified mounting logic for official Gemini CLI login state. To use Gemini CLI, use the API environment variables above or extend the container-side CLI login-state handling yourself.

### Post-hoc Judge

If post-hoc judge is enabled, you can configure a separate judge endpoint. If unset, it falls back to `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL`:

```bash
export JUDGE_API_KEY=...
export JUDGE_BASE_URL=...
```

## Evaluation Service and State

NatureBench agent containers cannot directly access `evaluation/`. Instead, they submit outputs to a host-side evaluation service and receive scores from it. The evaluation service has two modes: external and internal.

**External evaluation service**

This is the recommended mode for formal runs:

```bash
--start-eval-services \
--eval-env-mapping ./eval_env_mapping.json
```

`--start-eval-services` launches independent `eval_service.py` processes per `eval_env_mapping.json`, and `--eval-env-mapping` tells `solve.py` which port each task registers with (in this release all 90 tasks map to the `naturebench-eval` environment on port `8321`). The service runs independently of `solve.py`, keeps serving later commands, and can use its own conda environment.

Its behavior:

- **State (in memory):** per-`(case_id, batch_name)` attempt count, best attempt and score, and timers.
- **Logging:** appends every `/evaluate` call to the task's `submissions.jsonl`, and writes `result.json` and `run_summary.json` when a task finishes.
- **Reuse:** start the service once; later resume commands reuse its state by dropping `--start-eval-services` while keeping `--eval-env-mapping`.
- **Restart:** restarting clears in-memory state (it does not replay `submissions.jsonl`). To restart, first stop the old process via the PIDs in `eval_logs/eval_service_pids.txt` rather than binding a second service to the same port.

**Internal evaluation service**

Fallback when `--eval-env-mapping` is not provided: `solve.py` starts a background service inside the current process, using `--eval-port` for its port. Suitable for very small smoke tests or debugging only, because it:

- disappears when the current `solve.py` process exits;
- cannot preserve timers, best scores, or submission history across commands;
- requires the main environment itself to satisfy evaluator dependencies.

Formal evaluation and resume runs should use external mode.
