# Output Format: verification_result.json

## Structure

```json
{
  "paper_id": "string",
  "verify_timestamp": "ISO 8601",

  "paper_summary": "string (3-5 sentences: problem, method, data, metrics, conclusions)",

  "verdict": {
    "judgment_correct": "boolean",
    "override": "null | object",
    "correction_count": "number"
  },

  "checks": [
    {
      "id": "C1",
      "status": "pass | fail",
      "detail": "string (1-2 sentence summary)",
      "corrections": []
    }
  ]
}
```

---

## verdict

| Field | Type | Description |
|-------|------|-------------|
| `judgment_correct` | boolean | Whether the pass/reject judgment in filter_result.json is correct |
| `override` | null or object | Populated when the judgment should be flipped; format below |
| `correction_count` | number | Total number of corrections across all checks |

### override format (only when judgment_correct = false)

```json
{
  "to": "reject",
  "rule": "1.1",
  "category": "rejected_other_out_of_scope",
  "reason": "string"
}
```

---

## checks

Array containing 10 check results (C1-C10).

### Basic structure

When status is `pass`, no corrections field:

```json
{
  "id": "C1",
  "status": "pass",
  "detail": "MolMap + MolMapNet are genuine original ML contributions"
}
```

When status is `fail`, includes corrections array:

```json
{
  "id": "C6",
  "status": "fail",
  "detail": "PRC-AUC metric missing",
  "corrections": [
    {
      "severity": "normal",
      "path": "task_info.metrics",
      "action": "add",
      "current": null,
      "recommended": "{ \"name\": \"PRC-AUC\", \"score_source\": \"Table 2 (MUV, PCBA, ChEMBL)\" }",
      "reason": "MUV/PCBA/ChEMBL in Table 2 use PRC-AUC",
      "evidence": "Table 2 column headers"
    }
  ]
}
```

---

## correction fields

| Field | Type | Description |
|-------|------|-------------|
| `severity` | string | `critical` (flips pass/reject or fundamental error) or `normal` |
| `path` | string | JSON path in filter_result.json |
| `action` | string | `update` / `add` / `remove` |
| `current` | string or null | Summary of current value (null for `add` actions) |
| `recommended` | string | Recommended value |
| `reason` | string | Why this correction is needed |
| `evidence` | string | Specific paper evidence (section names, table numbers, quotes) |

### Special fields for C10 (Intra-Setting Terminology Consistency)

When C10 detects terminology inconsistencies within a setting, corrections may include an additional field:

| Field | Type | Description |
|-------|------|-------------|
| `related_field` | string (optional) | JSON path to the field that this field should be consistent with |

Example:
```json
{
  "severity": "normal",
  "path": "task_info.data.evaluation_settings[0].d_eval.x_test",
  "action": "update",
  "current": "Raw scATAC-seq count matrix",
  "recommended": "Preprocessed scATAC-seq count matrix",
  "reason": "Terminology inconsistent with d_dev.description which states the data is preprocessed",
  "evidence": "Methods section confirms data is preprocessed before input",
  "related_field": "task_info.data.evaluation_settings[0].d_dev.description"
}
```

---

## Constraints

- `checks` array contains C1-C10 in order (10 items total)
- When status is pass, omit the corrections field
- All 7 fields in each correction must be filled
- `evidence` must cite specific paper content
- No risks or blind_spots fields
