# Output Format Definition

## File Naming

- Filtering decision result: `filter_result.json`

---

## filter_result.json Structure

```json
{
  "paper_id": "string",
  "paper_title": "string",
  "filter_timestamp": "ISO 8601 datetime",

  "task_info": {
    "task_type": "string (task type, e.g., 'protein structure prediction', 'image classification')",
    "algorithm": "string (core algorithm name proposed by the paper; include both base and variant names if the paper uses named variants)",
    "metrics": [
      {
        "name": "string (metric name, e.g., 'Accuracy', 'F1-Score')",
        "score_source": "string (location where this metric's scores appear, e.g., 'Table 2', 'Figure 3')"
      }
    ],
    "sota": "string (SOTA method name, same as algorithm)",
    "baseline": ["string (list of baseline method names, optional, may be empty [])"],
    "data": {
      "pattern": "string (dataset pattern, e.g., 'Multiple Independent', 'Shared Training', 'Combined Training', 'Paired Combinations', 'Single Dataset')",
      "size_tier": "S | M | L | null (data size tier: S < 1GB, M 1-50GB, L > 50GB; null if Rule 3.6 not reached)",
      "evaluation_settings": [
        {
          "name": "string (setting identifier)",
          "description": "string (setting overview: version info, sample size, completeness status [D_dev, D_eval, score_source], etc.)",
          "d_dev": {
            "name": "string (dataset name, e.g., 'ImageNet-1k', 'PDBbind v2020')",
            "description": "string (development data overview: training set, validation set, pre-trained model, etc.)",
            "source": {
              "paper_reference": {
                "section": "string (paper section, e.g., 'Data Availability', 'Methods', 'Supplementary')",
                "evidence": "string (quote or description from paper)"
              },
              "url": "string (data link, multiple links can be separated by commas or newlines)",
              "url_source": "string (where URL was found, e.g., 'paper Data Availability section', 'repo README.md', 'Supplementary Table S1'. If multiple URLs, specify source for each)",
              "acquisition_scenario": "in_repo | download_script | external_link | generated | restructured",
              "instruction": "string (acquisition steps)"
            }
          },
          "d_eval": {
            "name": "string (test set name/version, e.g., 'Test Set A', 'Shared Task Test')",
            "description": "string (overall description of evaluation data)",
            "x_test": "string (problem definition: data input to the model)",
            "y_ref": "string (answer definition: Reference or Oracle)",
            "source": {
              "paper_reference": {
                "section": "string (paper section)",
                "evidence": "string (quote or description from paper)"
              },
              "url": "string (data link)",
              "url_source": "string (where URL was found)",
              "acquisition_scenario": "in_repo | download_script | external_link | generated | restructured",
              "instruction": "string (acquisition steps)"
            }
          }
        }
      ],
      "rejected_settings": [
        {
          "name": "string (setting identifier)",
          "failure_reason": "string (why this setting failed)"
        }
      ],
      "setting_dependencies": [
        {
          "source_setting": "string (source setting name, must match an evaluation_settings[].name)",
          "dependent_settings": ["string (must match evaluation_settings[].name or rejected_settings[].name)"],
          "dependency_type": "pretrained_model",
          "description": "string (e.g., 'Settings B/C fine-tune the model pretrained in Setting A')"
        }
      ]
    },
    "dependencies": ["string (list of additional libraries/packages that may need to be installed, e.g., 'PyTorch>=1.9', 'scanpy', 'RDKit', 'Rosetta')"]
  },



  "filtering_process": [
    {
      "level_id": 1,
      "level_name": "Task Nature Filtering",
      "passed": "boolean",
      "rules": [
        {
          "rule_id": "1.1",
          "rule_name": "ML Task Extractability",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string",
          "category": ["string (can select multiple, options: algorithmic_innovation | problem_formulation | methodological_adaptation | rejected_validation_tool_usage | rejected_non_computational | rejected_non_ml_factor_comparison | rejected_intermediate_data_evaluation | rejected_attribution_explainability | rejected_general_methodology | rejected_hardware_dependent | rejected_other_out_of_scope)"]
        }
      ]
    },
    {
      "level_id": 2,
      "level_name": "Evaluation System Validity Filtering",
      "passed": "boolean | null",
      "rules": [
        {
          "rule_id": "2.1",
          "rule_name": "Performance Absoluteness",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string",
          "metrics_identified": ["string"]
        },
        {
          "rule_id": "2.2",
          "rule_name": "Metric Determinism",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string"
        }
      ]
    },
    {
      "level_id": 3,
      "level_name": "Data and Process Completeness Filtering",
      "passed": "boolean | null",
      "rules": [
        {
          "rule_id": "3.1",
          "rule_name": "Zero-Interaction Acquisition",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string (must include link verification results)",
          "links_checked": [
            {
              "url": "string",
              "status": "accessible | requires_auth | redirect_to_auth | not_found | error",
              "http_code": "number | null",
              "notes": "string | null",
              "final_url": "string | null (final URL after redirects)",
              "cloud_type": "string | null (google_drive | baidu_pan | dropbox | onedrive | mega | box | null)",
              "file_size": "number | null (file size in bytes from Content-Length header)",
              "file_size_source": "string | null (how file_size was obtained, e.g., 'content_length')"
            }
          ]
        },
        {
          "rule_id": "3.2",
          "rule_name": "Initial State Completeness",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string (describe inspection results for each dependency)",
          "dependencies_status": {
            "training_data": "available | missing | partial | not_required",
            "validation_data": "available | missing | partial | not_required",
            "pretrained_model": "available | missing | not_required",
            "external_resources": "string | null (other external dependencies such as config files, vocabulary, simulators, etc.)"
          }
        },
        {
          "rule_id": "3.3",
          "rule_name": "Evaluation Loop Completeness",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string"
        },
        {
          "rule_id": "3.4",
          "rule_name": "Data Consistency",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string (compare paper claims vs data source inspection)"
        },
        {
          "rule_id": "3.5",
          "rule_name": "Partial Experiment Closure",
          "passed": "boolean",
          "reason": "string",
          "evaluation_settings": [
            {
              "name": "string (setting name)",
              "complete": "boolean",
              "success_analysis": "string | null (string if complete=true, otherwise null)",
              "failure_reason": "string | null (string if complete=false, otherwise null)"
            }
          ],
          "complete_count": "number",
          "total_count": "number"
        },
        {
          "rule_id": "3.6",
          "rule_name": "Data Scale Feasibility",
          "passed": "boolean",
          "reason": "string",
          "evidence": "string",
          "size_tier": "S | M | L | null",
          "estimation_confidence": "high | medium | low | indeterminate",
          "estimated_total_bytes": "number | null",
          "estimated_total_size": "string | null (human-readable, e.g., '2.5 GB')",
          "per_url_estimates": [
            {
              "url": "string",
              "estimated_bytes": "number | null",
              "source": "string (content_length | github_api | zenodo_api | figshare_api | huggingface_api)",
              "confidence": "string (high | medium)"
            }
          ]
        }
      ]
    }
  ],

  "final_result": {
    "passed": "boolean",
    "decision_summary": "string (brief summary of the filtering decision)",
    "stopped_at": "string | null (e.g., 'Level 1 - Rule 1.1', null when passed)",
    "review_notes": ["string (optional, only present when passed == true and there are noteworthy items for human review)"]
  }
}
```

---

## Field Descriptions

### task_info

Core task information extracted during filtering, extracted while making judgments:

| Field | Description | Extraction Timing |
|-------|-------------|-------------------|
| task_type | Task type/definition | Level 1 |
| algorithm | Core algorithm name proposed by the paper | Level 1 |
| metrics | List of evaluation metrics and score source | Level 2 |
| sota | Method name | Level 2 |
| baseline | Method name (optional, may be empty) | Level 2 |
| data.pattern | Dataset pattern (e.g., 'Multiple Independent', 'Shared Training') | Level 3 |
| data.evaluation_settings[] | Array of settings that **passed Rule 3.5**, each containing d_dev and d_eval | Level 3 |
| data.rejected_settings[] | Array of settings that **failed Rule 3.5**, each with name and failure_reason | Level 3 |
| data.setting_dependencies[] | Cross-setting dependency chain (e.g., pretrain→finetune). Optional, only present when detected | Level 3 |
| dependencies | List of additional libraries/packages that may need to be installed | Level 3 |
| data.size_tier | Data size tier: S (< 1GB), M (1-50GB), L (> 50GB); null if Rule 3.6 not reached | Level 3 (Rule 3.6) |

Notes:
- Specific scores are not extracted, only score source locations are recorded
- If a field is rejected before its corresponding Level, that field may be empty

### acquisition_scenario

Data acquisition scenario classification, used to guide subsequent task construction:

| Scenario | Description | Lightweight Check Method |
|----------|-------------|--------------------------|
| in_repo | Data directly in repository | View repo directory structure |
| download_script | Has download script | Check for download.sh/get_data.py |
| external_link | Download from external link | Verify link accessibility |
| generated | Needs to run script to generate | Check for generate_data.py |
| restructured | Needs to restructure raw data | Check restructure script + raw data source |

### final_result.stopped_at
Records where filtering stopped:
- `null`: All passed
- `"Level 1 - Rule 1.1"`: Rejected at Rule 1.1 of Level 1
- `"Level 2 - Rule 2.2"`: Rejected at Rule 2.2 of Level 2

### final_result.review_notes

Optional. Only present when `passed == true` and there are noteworthy items that may benefit from human review. An array of strings, each identifying a specific rule and what is worth verifying — e.g., genuinely conflicting evidence between paper text and repository contents, or a critical detail that could not be corroborated at this inspection stage.

Do NOT use review_notes to express general unease about data acquisition difficulty, non-ideal link types, or downstream reproduction complexity. If a rule passed, the judgment stands; review_notes are for flagging specific, verifiable discrepancies.

### Null Value Handling

- If a Level was not executed (because previous Level was rejected), that Level's `passed` is set to `null`, `rules` array is empty
- If a field's information cannot be extracted from the paper, leave it as `null` or empty (`[]` / `{}`). Do NOT fabricate, guess, or force-fill.
- `setting_dependencies` is optional — absent (not `null` or `[]`) when no cross-setting dependencies are detected.
