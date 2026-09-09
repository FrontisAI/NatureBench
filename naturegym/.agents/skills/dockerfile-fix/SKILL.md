---
name: dockerfile-fix
description: Fix Dockerfile issues identified by batch_verify.sh. Reads verify_result.txt to diagnose import failures, version conflicts, and missing dependencies, then repairs the Dockerfile and updates packages.json. May also fix scripts (Script-First Rule) when packages are unavailable.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Write, Edit
---

# Dockerfile Fix Skill

Fix Dockerfile issues discovered by runtime verification (batch_verify.sh). This skill diagnoses actual import failures, version conflicts, and missing dependencies from `verify_result.txt`, then repairs the Dockerfile, updates `packages.json`, and optionally fixes scripts when packages are unavailable.

## Input

User provides:
1. **task_package_path**: Path to the task package directory (containing `problem/`, `evaluation/`, `environment/`)
2. **dockerfile_name** (optional): Name of the Dockerfile to fix. Default: `Dockerfile.v3`. Can also be `Dockerfile` or any other name.

## Prerequisites

The following files must exist in `{task_package_path}/environment/`:
- `verify_result.txt` — output from batch_verify.sh, with status "has failures" or "build failed"
- `packages.json` — package manifest (see `environment_guide.md` Step 4)
- `{dockerfile_name}` — the Dockerfile to fix

## Reference Materials

Read these before starting:
- [environment_guide.md](.claude/skills/task-build/references/environment_guide.md) — Dockerfile generation logic, known compatibility issues, Script-First Rule, version conflict handling
- [Dockerfile.base.v3](.claude/skills/task-build/references/Dockerfile.base.v3) — base image packages and versions
- [base_packages.json](.claude/skills/task-build/references/base_packages.json) — base package list with import names

## Procedure

### Phase 1: Diagnose

0. **Carry-forward check (mandatory before diagnosis)**: if `dockerfile_fix_log.txt` already records prior fix rounds for this Dockerfile, diff the *current* `Dockerfile.v3` against the prior round's fixes. If the current Dockerfile is missing pins/RUN steps that earlier rounds added, the verify pipeline regressed to an earlier Dockerfile state — **first re-merge all prior fixes into the current Dockerfile, then proceed to diagnose only the new failures**. Do not start diagnosing fresh as if no history exists; you will keep re-deriving the same fixes round after round.

1. Read `environment/verify_result.txt` and extract every FAIL line and its detailed error.

2. Classify each failure into an error type:

| Type | Pattern | Example |
|------|---------|---------|
| A: ABI/binary incompatibility | `numpy.dtype size changed`, `undefined symbol` | catboost with numpy 2.x, `torch_scatter` with wrong torch/CUDA wheel |
| B: Missing dependency | `No module named 'xxx'` | missing setuptools, zarr |
| C: Runtime environment missing | `missing MuJoCo`, `expected to find the file` | mujoco-py without MuJoCo binary |
| D: API incompatibility | `has no attribute`, `is not a`, TorchScript errors | elmoformanylangs with torch 2.6 |
| E: Backend/config conflict | `Unsupported backend`, configuration errors | dask-expr with old spatialdata |
| F: Build failure | `conflicting dependencies`, `Cannot install` | leidenalg vs louvain igraph conflict |

3. Identify **root causes** vs **symptoms**. Many failures are cascading — a single root cause (e.g., DGL overwriting torch) can cause 5+ symptom failures (torchvision, torchaudio, lightning, timm, etc.). Group symptoms under their root cause.

   **Known-issues grep pass (mandatory, before writing any fix strategy)**: for every failing package name AND every distinctive error-message phrase (e.g., `numpy.dtype size changed`, `No module named 'pkg_resources'`, `has no attribute 'StringDType'`, `has no attribute 'xe'`), `grep` the "Known compatibility notes and issues" section of `environment_guide.md`. A hit is a **root-cause description**, not a hint — apply the prescribed fix verbatim (including its placement requirements, e.g., "final RUN pip install", "force-reinstall --no-deps"). Skipping this pass is the most common way fixes under-repair: the symptom disappears but the real root cause (e.g., jax resolver drift behind a numpy ABI error) keeps reappearing in the next verify cycle. Also check for ecosystem-wide rules ("Torch ecosystem lock", "JAX ecosystem lock") — if any member of the ecosystem is among the failures, the lock rule applies to the whole chain, not just the listed package.

   **Key diagnostic pattern — Torch ABI pollution**: When you see torchvision, torchaudio, lightning, timm, or PyG extension packages (torch-scatter, torch-sparse, etc.) all failing simultaneously with `undefined symbol`, ABI mismatch, or import errors, the most likely root cause is that a task package (typically DGL or another torch ecosystem package installed from a mismatched wheel index) silently replaced the base image's `torch==2.6.0+cu118` with a different version. **First diagnostic step**: check the Dockerfile for any pip install that uses a torch wheel index other than `torch-2.6/cu118` (e.g., `torch-2.4/cu118`, `cu124`, `cu126`). If found, that single install is the root cause — fix it by switching to the correct `torch-2.6/cu118` wheel index, and all downstream failures resolve automatically.

4. For each failure, determine the package's **tier** from `packages.json`:
   - Tier 1 (evaluator import): **must fix** — evaluator won't run without it
   - Tier 2 (solver script import): **must fix** — solver scripts won't run without it
   - Tier 3 (paper core dependency): **should fix** — important for solver
   - Tier 4 (domain common tool): **best effort** — can be removed if fix is too costly

### Phase 2: Plan Fixes

For each root cause, select a fix strategy in priority order. **Always consider whether the fix itself could introduce new problems** — check Requires-Dist of any new package against base versions.

**Core principle: Never override base packages.** Overriding base packages (e.g., downgrading numpy) risks cascading failures across catboost, scipy, scikit-learn, h5py, torch, and other C-extension packages. Instead, find compatible versions of the *task* packages, or use Script-First Rule + alternatives.

#### Strategy 1: Change Version (preferred)

Find a version of the problematic package that is compatible with the base image. Check:
- Does the new version's `Requires-Dist` include `numpy==1.26.4`, `torch==2.6.0`, etc.?
- Does it have a wheel for Python 3.11?
- If it is a torch ecosystem package with compiled extensions, does the wheel also match the base CUDA variant (`cu118` in `v3`)?
- Use PyPI metadata or `pip install --dry-run` logic to verify.

Example: `dgl==2.4.0` (torch-2.4 wheel) → `dgl==2.5.0` from the `torch-2.6/cu118` wheel index

#### Strategy 2: Add Missing Dependency

Install packages that were removed as a side effect of other installations.
- After adding, verify the new package doesn't conflict with base (check its Requires-Dist).

Example: Add `setuptools` after DGL installation

#### Strategy 3: Add Environment Variable / System Dependency

For runtime configuration or system-level issues only. Not for Python package conflicts.

Example: `ENV DASK_DATAFRAME__QUERY_PLANNING=False` for dask-expr conflict
Example: Download MuJoCo binary + set `LD_LIBRARY_PATH`

#### Strategy 4: Script-First Rule + Replace with Alternative

When a package genuinely cannot be installed (no compatible version exists for Python 3.11 + base):

1. **Find an alternative** that provides equivalent functionality:
   - Prefer packages already in the base image (no Dockerfile change needed, best option)
   - Otherwise, find a compatible replacement and add it to Dockerfile
   - The alternative must be verified compatible with base (check Requires-Dist)
2. **Modify the script** that imports the unavailable package to use the alternative
3. **Update Dockerfile**: remove the unavailable package, add the alternative (if not already in base)
4. **Update packages.json** accordingly

**This strategy applies to ALL tiers**, including Tier 1/2 (evaluator/solver scripts). For Tier 1/2, fixing the script is mandatory — these packages cannot simply be removed because the evaluator or solver will crash without them. The script must be updated to use the alternative.

Example: `elmoformanylangs` (incompatible with torch 2.6) → replace script to use `transformers` (already in base) for embeddings

#### Strategy 5: Remove Package (when no alternative exists)

When Strategy 1-4 cannot resolve the issue — no compatible version, no alternative, and the package is not a Tier 1/2 hard requirement:

- **Tier 3/4**: Remove from Dockerfile and packages.json. Add a Dockerfile comment explaining why, and note in the fix log that this was a solver convenience package that could not be made compatible.
- **Tier 1/2**: **Never simply remove.** Must use Strategy 4 (Script-First Rule) to replace the import, or escalate to Strategy 6.

#### Strategy 6: Standalone Dockerfile (last resort)

When strategies 1-5 cannot resolve the conflicts — the base image is fundamentally incompatible with the task's requirements. Create a standalone Dockerfile following `environment_guide.md` "When to Use a Standalone Dockerfile":
- Do NOT inherit from `naturebench-base:v3`
- Start from `nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04`
- Replicate the Python 3.11 venv pattern (`/opt/py311` on PATH)
- Install only the packages this task needs
- Use this path when the task genuinely requires a different CUDA family (for example, packages that only publish CUDA 12.x wheels)
- Update `packages.json` with `"from_base": false` and empty `base_packages`

### Phase 3: Execute Fixes

1. **Modify the Dockerfile**: Apply all planned fixes. Preserve existing comments. Add new comments explaining each fix.

2. **Fix scripts if needed** (Strategy 4): Modify `evaluation/evaluator.py` or scripts in `problem/data/`. Verify syntax with `python -m py_compile`.

3. **Update packages.json**: Sync with the modified Dockerfile:
   - Add new packages to `task_packages`
   - Remove deleted packages from `task_packages`
   - Update versions for changed packages
   - If switched to standalone Dockerfile: set `"from_base": false`, clear `base_packages`, list all packages in `task_packages`

### Phase 4: Output Fix Log

Write `environment/dockerfile_fix_log.txt`:

```
=== Dockerfile Fix Log ===
Task: <task_package_path>
Dockerfile: <dockerfile_name>
Date: <ISO 8601 timestamp>

--- Failures Diagnosed ---
  [ROOT CAUSE] <root cause description>
    Type: <A|B|C|D|E|F>
    Symptoms: <list of packages that failed due to this root cause>
  [ROOT CAUSE] <another root cause>
    ...

--- Fixes Applied ---
  1. <what was changed>
     Strategy: <1-6>
     Reason: <why this fix was chosen>
  2. ...
  3. [SCRIPT FIX] <file>: <what was changed>
     Reason: <why script fix was needed>

--- Packages Removed ---
  <package>: <reason> (Tier <N>)

--- Packages Updated in packages.json ---
  Added: <list>
  Removed: <list>
  Changed: <list>

--- Unresolved (Manual Review Needed) ---
  <issue>: <why it couldn't be auto-fixed>
```

## Critical Rules

- **Two-strikes rule (switch strategy, don't micro-adjust)**: If the *same package* has failed in two consecutive fix rounds — even with different symptoms — stop iterating on the current strategy. The right next move is almost always "change the pinned version" (upgrade to a version where the underlying bug is fixed upstream, or downgrade to the last version without the problem), or "remove the package via Script-First Rule." Do **not** keep tweaking sed patches, pre-install ordering, env vars, or `--no-build-isolation` flags after two failed rounds — those are symptom-level levers and compound fragility. Verified failure modes this rule would have caught:
  - Case 503: four rounds iterating on sed-patch placement / path-discovery for `squidpy==1.5.0`. Correct move on round 2 would have been "upgrade squidpy to a version that no longer imports SparseCSCView."
  - Cases 881 & 939: both pre-installed `setuptools` before `pybedtools==0.10.0` to fix a PEP 517 isolated-build error. Pre-install cannot reach the isolated build env. Correct move was "upgrade to `pybedtools==0.12.0` which ships a wheel."
- **Read pip resolver errors literally**: pip's `ResolutionImpossible` output names the exact requester and requirement. Two patterns with opposite fixes:
  - `X depends on Y<A,>=B` + `no matching distributions available for your environment: Y` → **the requester X is the problem**. Change X's version (usually downgrade one minor) — do not hunt for a Y in the range, it does not exist for this Python/platform. (Verified: case 926, `squidpy 1.6.6 depends on imagecodecs<2026,>=2025.8.2` + no cp311-linux wheel → downgrade squidpy, not chase imagecodecs.)
  - `X requires Y>=A, but Y==B is installed` (no "no matching distributions" line) → **Y is satisfiable**, the conflict is between X's requirement and the currently-pinned Y. Adjust either side.
- **Diagnose root causes, not symptoms**: Don't fix torchvision, torchaudio, lightning, timm separately when they all fail because of a DGL installation issue. Fix DGL, and the rest resolve automatically.
- **Check fix side effects**: Every fix can introduce new problems. Always check whether a new package version or added dependency conflicts with base packages.
- **Never override base packages**: Downgrading or upgrading base packages (numpy, torch, scipy, etc.) risks cascading C-extension failures across the entire environment. Always find compatible task package versions instead.
- **Never use `--no-deps`**: It silently breaks the runtime environment.
- **Pin all versions**: Every package in Dockerfile must have `==X.Y.Z`.
- **Sync packages.json**: After any Dockerfile change, packages.json must be updated to match.
- **Script-First Rule for Tier 1/2**: When a Tier 1/2 package can't be installed, fix the importing script to use an alternative (preferably already in base). Never simply remove a Tier 1/2 package.
- **Prefer base alternatives**: When replacing a package, first check if base already provides equivalent functionality (e.g., `transformers` is in base and can often replace specialized embedding libraries).
- **Preserve existing Dockerfile structure**: Don't reorganize or rewrite the entire Dockerfile. Make targeted fixes to the specific lines/packages that cause failures.
- **Tier-aware removal**: Tier 3/4 packages can be removed when no compatible version or alternative exists. Tier 1/2 packages must always be resolved via Script-First Rule or standalone Dockerfile — never silently removed.
