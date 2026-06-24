# Data Acquisition Guide

Detailed specifications for repository cloning, data downloading, supplementary material acquisition, rejected settings re-examination, setting directory naming, and data cleanup in the data-check skill.

---

## 1. Repository Cloning

### Clone Command

```bash
GIT_SSL_NO_VERIFY=1 git clone --depth 1 <url> <output_dir>/repositories/<owner>_<repo_name>
```

- `GIT_SSL_NO_VERIFY=1`: Handle proxy/corporate environments where SSL verification fails
- `--depth 1`: Shallow clone to save space and time (only latest commit)
- Extract `<owner>_<repo_name>` from URL: last two path segments without `.git` suffix (prevents naming collisions)

### Purpose of Cloned Repositories

Repositories are cloned for **downstream pipeline use** — understanding evaluation code, algorithm implementation, data processing logic, and reproducing the experimental setup. They are **not** executed directly during the data-check phase (except for download/generation/restructure scripts when `acquisition_scenario` requires it).

### Multi-Repository Handling

Papers may have separate repositories for code and data:
- Clone all to `repositories/`, each in its own subdirectory
- If the same content appears across multiple sources:
  - Check which has more files / more recent activity
  - Keep the more complete one, skip the other (mark as `skipped`)
  - Prefer GitHub for code repos (has git history), Zenodo for data archives

### Clone Verification

After cloning, verify:
1. `<clone_path>/.git/` directory exists
2. `git -C <clone_path> rev-parse HEAD` returns a valid hash
3. Directory is non-empty (contains more than just `.git/`)

### Timeout Settings for Git

Use generous buffer and timeout settings for large repositories (e.g., `http.postBuffer`, `http.lowSpeedTime`). Set `timeout: 86400000` on the Bash call for clone commands.

---

## 2. Data Download Specifications

### Core-Priority Download Order

Before downloading, sort `evaluation_settings` by priority:

1. **P1 (Core)**: Settings whose results appear in the paper's main-body result sources
2. **P2 (Secondary)**: All other passed settings

**How to determine P1 vs P2** (infer from existing data, no extra schema field):

**Step 1 — Classify score_sources by importance:**

Parse each `task_info.metrics[].score_source` string into individual references and classify:

| Category | Pattern examples | Weight |
|----------|-----------------|--------|
| **Main-body** | `Table 1`, `Table 2`, `Fig. 3`, `Figure 1` (no qualifying prefix) | High |
| **Extended/Supplementary** | `Extended Data Fig. 1`, `Supplementary Table S1`, `Supplementary Fig. 4`, `SI Table 2` | Low |
| **Text reference** | `Results section`, `main text` | Medium |

A single `score_source` string may contain multiple references (comma- or "and"-separated). Parse each one individually.

**Step 2 — Match settings to score_sources:**

For each setting, check its `description` and `name` for overlap with the classified sources:
- **Explicit table/figure mention**: description says "results reported in Table 2" → matches that source
- **Dataset name in score_source**: `score_source: "Table 1 (CIFAR-10)"` → matches a setting named "CIFAR-10"  
- **Dataset name in description + source**: setting description mentions "CIFAR-10" and a `score_source` contains "CIFAR-10" → match
- **Semantic signals in description**: description contains phrases like "main results", "primary benchmark", "core evaluation" → likely P1; phrases like "ablation", "supplementary experiment", "auxiliary test" → likely P2
- **Only/default setting**: if there is only one evaluation setting, it is automatically P1

**Step 3 — Assign priority:**

- **P1**: Setting matches at least one **main-body** score_source (high weight), OR has strong semantic signals of being a core evaluation, OR is the only/default setting
- **P2**: Setting only matches extended/supplementary sources, or has no clear match to any main-body source
- **Default P1**: If matching is ambiguous (all settings look equally core, or none clearly match), treat **all** as P1 — never risk deprioritizing a core setting

Process P1 settings first. When Tier M size limits trigger, core settings are already complete — only secondary settings are truncated.

This ordering applies to all tiers but only affects outcomes for Tier M with large cumulative downloads.

### Download Mandate (Tier-Conditional)

Download behavior depends on `task_info.data.size_tier` from `filter_result.json`:

| Tier | Policy |
|------|--------|
| **S** (< 1 GB) | Unconditional full download. "Data too large" is NEVER acceptable. |
| **M** (1-50 GB) | Full download with cumulative size monitoring. If actual cumulative download exceeds **100 GB**, stop remaining settings and move them to `rejected_settings[]` with `failure_reason: "Skipped due to cumulative download size exceeding 100 GB limit (Tier M safeguard)"`. Already-completed settings are not affected. |
| **L** (> 50 GB) | Should not reach data-check (rejected at paper-filter). If encountered, treat as Tier M with 100 GB hard limit. |
| **null** (legacy) | Backward compatible — treat as Tier M (full download with 100 GB cumulative limit). |

For all tiers: if required components for a setting are not fully downloaded, verification for that setting **must fail**.

### Foreground Execution & Timeout

**ALL download and acquisition Bash calls MUST run in the foreground.** Never use `run_in_background: true` for any download, clone, script execution, or data acquisition command.

- Every long-running Bash call (downloads, clones, script execution) **MUST** set `timeout: 86400000` (24 hours). Without an explicit timeout the Bash tool defaults to 2 minutes, which will silently kill the process mid-download.
- Do NOT proceed to the next step until the Bash call has returned and the downloaded file has been verified (existence + non-zero size).

### Idempotent Acquisition (Resume Support)

Data acquisition MUST be idempotent — re-running data-check on the same output directory skips already-completed work:

- **Repositories**: If `<output_dir>/repositories/<owner>_<repo_name>/.git/` exists **and** `git -C <path> rev-parse HEAD` returns a valid commit hash, skip cloning. Otherwise delete the incomplete directory and re-clone (git clone is not resumable).
- **Downloads**: Always use `wget -c` (resume) so that partially downloaded files continue from where they left off rather than restarting. If a file already exists and its size matches the expected size (from HTTP `Content-Length`), skip the download entirely.
- **Copied data**: If `data/<setting_dir>/` already contains the expected files, skip the copy.
- **Generated/restructured data**: If the output files already exist and are non-empty, skip re-execution.

This ensures that if a session times out mid-download (e.g., a multi-day dataset), the next invocation of data-check resumes from where it left off rather than starting over.

### By Acquisition Scenario

#### `in_repo` — Data in Cloned Repository

1. Locate data files within `repositories/<owner>_<repo_name>/` based on `source.instruction`
2. Copy (not move) to `data/<setting_dir>/`, keeping hidden files
3. Preserve internal directory structure

```bash
cp -a repositories/<owner>_<repo_name>/<data_path>/. data/<setting_dir>/
```

#### `download_script` — Repository Has Download Script

1. Locate the script in the cloned repository (common names: `download.sh`, `get_data.py`, `download_data.py`, `setup_data.sh`)
2. Inspect the script to understand:
   - Where it downloads to (may need to redirect output)
   - What dependencies it requires
   - Whether it has a `--output` or `--data_dir` argument
3. Install required dependencies if needed
4. Execute with output directed to `data/<setting_dir>/`
5. If the script downloads to a fixed location, copy results to `data/<setting_dir>/` after execution

**Safety**: Read the script before running. Do not execute scripts that install system packages, modify system files, or perform unrelated operations.

#### `external_link` — Direct URL Download

Download from URL to `data/<setting_dir>/` using `wget` or `curl`. Key requirements:
- **Resume**: Always use `wget -c` (or `curl -C -`) to support interrupted/partial downloads
- **Timeout**: Set `timeout: 86400000` on the Bash call (see §Foreground Execution & Timeout above)
- **Retries and stall detection**: Use robust retry settings:
  ```bash
  wget -c \
    --tries=20 --retry-connrefused \
    --wait=10 --waitretry=30 \
    --read-timeout=120 --timeout=60 \
    --no-check-certificate \
    --progress=dot:giga \
    <url>
  ```
  - `--read-timeout=120`: abort if no data flows for 2 minutes (default 900s is too long for proxied stalls)
  - `--waitretry=30`: wait up to 30s between retries
  - `--no-check-certificate`: required when proxy/MITM interferes with SSL
- **Verification**: Check file existence and size after each download
- **Proxy bypass fallback**: If a download stalls or hangs (no progress for several minutes) with SSL/proxy errors, retry with proxy disabled:
  ```bash
  curl --noproxy '*' -C - -L -o <output> <url>
  # or:
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY \
    wget -c --no-check-certificate <url>
  ```
  This is especially useful for AWS S3 (Mendeley Data redirects), Zenodo CDN, and Figshare, which often don't require proxy access.

#### `generated` — Run Generation Script

1. Locate generation script in repository
2. Install required dependencies if needed
3. Execute with output directed to `data/<setting_dir>/`
4. Verify generated files exist and are non-empty

#### `restructured` — Download + Restructure

Raw data requires format conversion or structural reorganization to reach a usable initial state (e.g., merging scattered files, converting formats). This does **NOT** include algorithm-specific feature engineering or data transformations that are part of algorithm A's pipeline.

1. First acquire raw data using one of the above methods
2. Locate the restructuring script in repository (e.g., `process_raw.py`, `convert.py`)
3. Install required dependencies if needed
4. Execute with raw data as input, output to `data/<setting_dir>/`
5. Verify restructured output

### Decompression & Recursive Unpacking

Automatically decompress archives after download. Before decompressing, verify archive integrity using `inspect_data.py verify-archive`; if corrupted, re-download. **Recursive Unpacking Rule**: Recursively extract nested archives (e.g., a `.zip` inside a `.tar.gz`) until all fundamental base files are exposed. After verifying contents are accessible, you **MUST delete** the original archives.

### Shared Data

Data should be placed exactly where it belongs for its evaluation setting (`data/{setting_dir}/`) to maintain independent directory structures.
We do **not** use a central `shared/` folder. If a data file (e.g., a massive pre-trained backbone or a universal raw dataset) is genuinely shared across multiple evaluation settings, **a separate copy MUST be placed inside each dataset instance's folder** (`data/{setting_dir}/`). 

This physical duplication ensures that each evaluation setting remains completely self-contained and independently executable.

### Shared Data Download Deduplication

When multiple settings share the same data source URL (`d_dev.source.url` or `d_eval.source.url`):

1. Download to the first setting's directory (per normal acquisition flow)
2. For subsequent settings sharing the same URL, copy locally from the already-downloaded setting instead of re-downloading: `cp -r` (or `cp -l` for hard links on large files)
3. Each setting directory still contains a complete, independent copy — the self-contained principle is maintained

This optimization reduces network downloads for papers with shared datasets (common in "Shared Training" pattern). It is transparent to downstream tools — the directory structure is identical to individual downloads.

### Maximum Scope Principle

When the original authors applied multiple data usage methods to the same data instance — involving different data scopes (e.g., one variant uses a subset of columns while another uses all, or one uses the main file while another additionally uses supplementary files) — always acquire the **broadest scope** (the superset). The task environment should contain all data that was available to the original authors; the algorithm under evaluation decides what to use.

---

## 3. Supplementary Materials

When the paper's main text and preprocessed data do not provide sufficient detail for verification:

1. Check `preprocessed/links.json` for supplementary material links (section: `supplementary_information`)
2. Download supplementary PDFs/files to a temporary location
3. Use the original paper PDF/HTML as fallback if supplementary links are not separately available
4. Extract relevant information (dataset versions, sample counts, score tables) for consistency verification
5. **Delete** the downloaded supplementary files after information extraction is complete

---

## 4. Rejected Settings Re-examination

After repositories are cloned (Phase 2), re-examine each entry in `rejected_settings[]`:

### Procedure

1. **Read the original `failure_reason`** for the rejected setting
2. **Check if cloning resolved the issue**:
   - If rejection was "data not found in repository" → inspect the actual cloned repo for data files
   - If rejection was "link inaccessible" → the link was already checked in Level 3; focus on whether the data exists through alternative paths in the repo
   - If rejection was "download script untested" → now you can inspect and potentially run the script
3. **Attempt acquisition** if the data appears available
4. **Record result**:
   - **If recoverable** → promote to `evaluation_settings[]` (and remove from `rejected_settings[]`) with full acquisition + verification
   - **If not recoverable** → keep in `rejected_settings[]` with an added `recheck` string detailing the result

### What NOT to recover

- Settings rejected for non-data reasons (e.g., metrics not applicable) should NOT be re-examined for data
- Settings where data requires authentication/login remain rejected
- Do not force-recover settings by accepting partial/toy data

---

## 5. Setting Directory Naming

**Anonymization Rule**: Remove algorithm names from directory paths to maintain task anonymity.

Convert setting name to a filesystem-safe, anonymized directory name:

1. Extract algorithm name from `task_info.algorithm` and `task_info.sota`
2. Remove algorithm name and connecting words ("on", "using", "with", "via") from setting name
3. Keep data features (dataset name, network type, experimental conditions)
4. Lowercase the entire string
5. Replace non-alphanumeric characters (except underscores) with underscores
6. Collapse consecutive underscores into one
7. Strip leading/trailing underscores

Examples:
| Setting Name | Directory Name |
|--|--|
| `EMOGI on CPDB PPI Network` | `cpdb_ppi_network` |
| `DeepWalk using 10X PBMC` | `10x_pbmc` |
| `Model A on CIFAR-10 classification` | `cifar_10_classification` |

**Important**: The anonymized directory name is used in `verification.data_path`. The original setting name in `task_info` remains unchanged.

---

## 6. Data Cleanup Rules

After all data is acquired and verified, clean the `data/` directory.

**Conceptual Cleanup (Whitelist Approach)**:
- The `data/` directory must ONLY contain the Initial State (`d_dev`) and the Evaluation Target (`D_eval`).
- Any file classified as `algorithm_preprocessing_output`, `algorithm_output`, or `irrelevant` (see [references/check_rules.md](references/check_rules.md) §Data Component Classification) does not belong in the data environment and **MUST BE DELETED**.

### Common Artifacts to Remove (Blacklist Examples)
- Output Model Checkpoints: `.ckpt`, `.pth`, `.pt`, `weights/`, `checkpoints/`, `saved_models/` (unless it's an `external_resource` listed in `d_dev`)
- Experiment Outputs & Viz: `predictions.*`, `results.*`, `scores.*`, `metrics.*`, `output.*`, `figures/`, `plots/`, generated `*.png`/`*.jpg`
- Logs & Caches: `*.log`, `logs/`, `tensorboard/`, `wandb/`, `runs/`, `__pycache__/`, `*.pyc`, `.cache/`, `.pytest_cache/`
- Training configurations and temporary files: `config.yaml`, `args.json`, `*.tmp`, `*.bak`, `.DS_Store`

### Preserve (Whitelist Examples)
- D_dev/D_eval fundamental data (`initial_state`, `data_preparation`): `.h5`, `.csv`, `.json`, `.txt`, `.fasta`, `.pdb`, original images, etc.
- External resources (`external_resource`): pre-trained models, embeddings, knowledge bases, vocabularies
- Splitting metadata: `train_ids.txt`, `split.json`, `test_indices.npy`

### Do NOT

- Split or reorganize data files (all splitting is deferred to task package construction)
- Rename data files
- Merge files from different settings
- Convert file formats

