# Output Schema: filter_result.json Extension

The data-check skill **updates** the existing `filter_result.json` produced by paper-filter. It adds new top-level fields, enriches `task_info.data` with per-setting verification results, and appends Level 4 to the `filtering_process` array.

**Write strategy**: Collect all results during processing. Write the complete update to `filter_result.json` atomically at the end to avoid partial/inconsistent states.

---

## New Top-Level Fields

These fields are added alongside the existing `paper_id`, `paper_title`, `filter_timestamp`, `task_info`, `filtering_process`, and `final_result`.

### data_check_timestamp

```json
"data_check_timestamp": "ISO 8601 datetime (when data-check was performed)"
```

### repositories

```json
"repositories": [
  {
    "url": "string (repository URL)",
    "name": "string (repository name, e.g., 'scDeepCluster')",
    "clone_path": "string (local path relative to output_dir, e.g., 'repositories/scDeepCluster')",
    "status": "success | failed | skipped",
    "error": "string | null (error message if failed)",
    "commit_hash": "string | null (HEAD commit hash if success)"
  }
]
```

Notes:
- `skipped`: repository was determined to be a duplicate of another already-cloned repo
- `clone_path` is relative to the output directory

---

## Updates to task_info.data

The existing `task_info.data` structure is **enriched** (not replaced). Paper-filter's original fields are preserved; data-check adds a `verification` block to each passing evaluation setting, and may move settings between `evaluation_settings[]` and `rejected_settings[]` based on Level 4 results.

### evaluation_settings[] — verification block

**CRITICAL**: The `verification` block must be added at the TOP LEVEL of each setting entry, NOT inside `d_dev` or `d_eval`.

```json
{
  "name": "Setting 1: 10X PBMC",
  "description": "string (may be updated if corrections found)",
  "d_dev": { "... (may be corrected)" },
  "d_eval": { "... (may be corrected)" },
  "recovered_from_rejected": "boolean (only present if true)",
  "verification": {  // ← HERE at setting top level
    "data_path": "string (relative to output_dir, e.g., 'data/cpdb_ppi_network')",
    "total_size": "string (human-readable, e.g., '2.3 GB', '150 MB')",
    "total_size_bytes": "number (total data size in bytes)",
    "separability": {
      "difficulty": {
        "overall": "trivial | simple | moderate | complex | ambiguous | infeasible | not_applicable",
        "dev_eval": "trivial | simple | moderate | complex | ambiguous | infeasible | not_applicable",
        "eval_decomposition": "trivial | simple | moderate | complex | ambiguous | infeasible | not_applicable",
        "difficulty_reason": "string (overall difficulty level assessment rationale)"
      },
      "dev_eval": {
        "d_dev_files": { "relative/path/to/file": "role and key info", "...": "..." },
        "d_eval_files": { "relative/path/to/file": "role and key info", "...": "..." },
        "split_procedure": "string (step-by-step instructions including output format)"
      },
      "eval_decomposition": {
        "x_test": {
          "files": { "relative/path/to/file": "which part and role", "...": "..." },
          "extraction": "string (step-by-step extraction instructions including output format)",
          "sample_count": "number"
        },
        "y_ref": {
          "files": { "relative/path/to/file": "which part and role", "...": "..." },
          "extraction": "string (step-by-step extraction instructions including output format)",
          "sample_count": "number"
        }
      }
    }
  }
}
```

Notes:
- `verification` is added to settings that remain in `evaluation_settings[]` (i.e., those that pass Level 4). Failed settings are moved to `rejected_settings[]` — see Setting Status Changes below.
- `data_path` points to the setting's data directory; all acquired files for this setting are stored there
- `data_path` should use anonymized directory names (algorithm name removed)
- `separability` documents how splits *can* be performed — no actual splitting is done. For difficulty level definitions see [check_rules.md](check_rules.md) Check 4.3.

### Setting Status Changes

Data-check may change the status of settings in both directions: recovering previously rejected settings into `evaluation_settings[]`, or moving previously accepted settings to `rejected_settings[]`.

#### Recovered settings (Level 3 rejected → Level 4 recoverable)

When a previously rejected setting is found to be acquirable after re-examination:
- A new entry is **added** to `evaluation_settings[]` with `"recovered_from_rejected": true` and a full `verification` block
- The original entry is **removed** from `rejected_settings[]`

#### Newly rejected settings (Level 3 passed → Level 4 failed)

When a previously accepted setting fails Level 4 verification:
- The original entry is **removed** from `evaluation_settings[]`
- A new entry is **added** to `rejected_settings[]` recording the Level 4 failure:

```json
{
  "name": "string (same as the evaluation_settings entry)",
  "failure_reason": "string (Level 4 failure description)",
  "rejected_at": "level_4"
}
```

- **Data cleanup**: The `data/{setting_dir}` directory associated with the newly rejected setting MUST be completely deleted from disk.

#### Unchanged rejected settings

Settings that remain rejected after re-examination keep their original entry with an added `recheck` string detailing why they remain rejected.

```json
{
  "name": "string (original, preserved)",
  "failure_reason": "string (original, preserved)",
  "recheck": "string (details of re-examination why it's still rejected)"
}
```

### task_info Corrections

When data-check discovers errors in `task_info`, it corrects them **in place** in filter_result.json and logs all corrections to a separate `data_check_corrections.txt` file in the Paper Folder for human review.

Correction rules:

1. **Only correct with concrete evidence**: e.g., data shape contradicts recorded size, a table clearly reports scores but isn't listed in `score_source`
2. **Preserve correct values**: never modify fields that are already accurate
3. **Correctable fields include**:
   - `metrics[].score_source`: if scores are found in additional tables/figures
   - `evaluation_settings[].description`: if actual data details differ from described
   - `evaluation_settings[].d_dev` and `evaluation_settings[].d_eval`: if actual data sources, acquisition methods, or component definitions differ from recorded
   - `data.pattern`: if actual dataset relationships differ from classified pattern
   - `data.setting_dependencies`: if Phase 4 discovers cross-setting dependencies not identified upstream (add), or if Phase 4 finds that a recorded dependency is incorrect — e.g., the pretrained model actually comes from external published work, not from Algorithm A in another setting (remove/correct)
4. **Non-correctable fields**: `paper_id`, `paper_title`, `algorithm`, `sota`, `baseline` (these require paper re-reading, not data inspection)

The corrections log format (`data_check_corrections.txt`):

```text
data-check corrections
Generated: {timestamp}

[Phase {N}] {field}: {old_value} → {new_value}
  Reason: {concrete evidence for the correction}
```

---

## Level 4 in filtering_process

Appended as the 4th element of the `filtering_process` array. Each check produces a **decision summary** only — structured verification data lives in `task_info.data` enrichment (above).

```json
{
  "level_id": 4,
  "level_name": "Deep Data Verification",
  "passed": "boolean",
  "rules": [
    {
      "rule_id": "4.1",
      "rule_name": "Data Acquisition Verification",
      "passed": "boolean",
      "reason": "string",
      "evidence": "string"
    },
    {
      "rule_id": "4.2",
      "rule_name": "Initial State Integrity",
      "passed": "boolean",
      "reason": "string",
      "evidence": "string"
    },
    {
      "rule_id": "4.3",
      "rule_name": "Data Separability Verification",
      "passed": "boolean",
      "reason": "string",
      "evidence": "string"
    },
    {
      "rule_id": "4.4",
      "rule_name": "Data Consistency",
      "passed": "boolean",
      "reason": "string",
      "evidence": "string"
    },
    {
      "rule_id": "4.5",
      "rule_name": "Partial Experiment Closure",
      "passed": "boolean",
      "unified": "boolean (true if all passing settings share the same core codebase and evaluation metrics)",
      "reason": "string",
      "evidence": "string"
    }
  ]
}
```

Notes:
- `reason`: Concise pass/fail explanation
- `evidence`: Key facts — file paths, sizes, sample counts, error messages. For Check 4.5, list each setting's pass/fail status.

---

## Updated final_result

The existing `final_result` is updated (not replaced) with additional fields:

```json
"final_result": {
  "passed": "boolean (original filter decision — unchanged)",
  "decision_summary": "string (original — unchanged)",
  "stopped_at": "string | null (original — unchanged)",
  "review_notes": ["string (original — unchanged, if present)"],

  "data_check_passed": "boolean (Level 4 overall result)",
  "complete_settings_count": "number (settings with verification.status == complete)",
  "total_settings_count": "number (all evaluation_settings, including recovered)",
  "data_check_summary": "string (brief summary of data verification outcome)",
  "check_review_notes": ["string (only present when data_check_passed == false)"]
}
```

Notes:
- The original fields are **preserved unchanged** for backward compatibility
- `complete_settings_count` includes settings recovered from `rejected_settings`
- `check_review_notes`: Only present when `data_check_passed == false`. An array of strings describing issues that may be resolvable with human intervention (e.g., data source temporarily unavailable)

---

## Complete Updated filter_result.json Structure (Summary)

```json
{
  "paper_id": "string",
  "paper_title": "string",
  "filter_timestamp": "ISO 8601 datetime",
  "data_check_timestamp": "ISO 8601 datetime",

  "task_info": {
    "task_type": "string",
    "algorithm": "string",
    "metrics": [{ "name": "string", "score_source": "string (may be corrected)" }],
    "sota": "string",
    "baseline": ["string"],
    "data": {
      "pattern": "string (may be corrected)",
      "evaluation_settings": [
        {
          "name": "string",
          "description": "string (may be updated)",
          "d_dev": { "... (may be corrected)" },
          "d_eval": { "... (may be corrected)" },
          "recovered_from_rejected": "boolean (only if true)",
          "verification": {
            "data_path": "string",
            "total_size": "string",
            "total_size_bytes": "number",
            "separability": { "difficulty": { "..." }, "dev_eval": { "..." }, "eval_decomposition": { "..." } }
          }
        }
      ],
      "rejected_settings": [
        {
          "name": "string",
          "failure_reason": "string",
          "recheck": "string (details for unchanged Level 3 rejections)",
          "rejected_at": "level_4 (for Level 4 rejections)"
        }
      ]
    },
    "dependencies": ["string"]
  },

  "repositories": [ "..." ],

  "filtering_process": [
    { "level_id": 1, "..." : "(unchanged)" },
    { "level_id": 2, "..." : "(unchanged)" },
    { "level_id": 3, "..." : "(unchanged)" },
    { "level_id": 4, "level_name": "Deep Data Verification",
      "passed": "boolean",
      "rules": [
        { "rule_id": "4.x", "passed": "boolean", "reason": "string", "evidence": "string" },
        { "rule_id": "4.5", "passed": "boolean", "unified": "boolean", "reason": "string", "evidence": "string" }
      ]
    }
  ],

  "final_result": {
    "passed": "boolean (original)",
    "decision_summary": "string (original)",
    "stopped_at": "string | null (original)",
    "review_notes": ["string (original, if present)"],
    "data_check_passed": "boolean (new)",
    "complete_settings_count": "number (new)",
    "total_settings_count": "number (new)",
    "data_check_summary": "string (new)",
    "check_review_notes": ["string (new, only when data_check_passed == false)"]
  }
}
```

---

## Null Value Handling

- If data-check has not been run, the fields `data_check_timestamp`, `repositories`, `verification`, `recheck`, and the Level 4 entry will not exist (absent, not null)
- Within data-check fields, use `null` for values that could not be determined (e.g., `commit_hash` when clone failed)
- When `separability.difficulty.overall` is `"infeasible"`, the sub-item fields (`split_procedure`, `extraction`) may still be present with explanatory content describing why separation is not possible
