---
name: verify-apply
description: Apply corrections from filter-verify (verification_result.json) or data-verify (data_verify_result.json) to filter_result.json. User specifies source type explicitly. Applies field-level and structural corrections, performs inline verification for new/modified settings, writes change log.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Bash(rm *), Bash(mkdir *), Bash(find *), Bash(ls *), Bash(git clone *), Bash(GIT_SSL_NO_VERIFY=1 git clone *), Bash(wget *), Bash(curl *), Bash(tar *), Bash(unzip *), Bash(gunzip *), Bash(cp *), Bash(mv *), Bash(du *), Bash(wc *), Bash(python *), Bash(python3 *)
---

# Verify-Apply Skill

Apply verification corrections to `filter_result.json`. Reads a verification result JSON, applies every correction/finding, and writes a change log.

## Core Principle: Pipeline Continuity

**After apply, `filter_result.json` must be directly consumable by the next pipeline stage — no re-runs of previous skills required.**

- filter-verify apply → output must match paper-filter output structure (ready for data-check)
- data-verify apply → output must match data-check output structure (ready for task-build)

This means any new or structurally modified evaluation setting must have the same completeness as what the corresponding upstream skill would produce.

> **Note:** If any concepts, operations, requirements, or explanations are unclear during implementation or adjustment, please refer to the documentation in the `paper-filter` and `data-check` skills for detailed guidance.

## Input Requirements

Before invoking this skill, provide:
1. **Source type**: `filter-verify` or `data-verify`
2. **Verification**: Path to verification JSON
3. **Target**: Path to `filter_result.json` to be modified

## Workflow

### Phase 1: Load

1. Read the verification JSON
2. Read the target `filter_result.json`
3. Read [references/apply_rules.md](references/apply_rules.md) — use the section matching the specified source type

### Phase 2: Apply Corrections

#### For filter-verify source

Apply every correction from checks with `status: "fail"`.

1. Iterate `checks[].corrections[]`, apply each using `path`, `action`, `recommended` as defined in apply_rules.md § Field-Level
2. If `verdict.override` is not null, apply the judgment override as defined in apply_rules.md § Judgment Override

#### For data-verify source

Apply every finding from checks with `status: "fail"` or `status: "warning"`.

1. V1/V3/V5 findings: field-level updates using `field` + `recommended_value` as defined in apply_rules.md § V1/V3/V5
2. V2 findings: structural operations on `evaluation_settings[]`/`rejected_settings[]` as defined in apply_rules.md § V2
3. V4 findings: file operations on `data/` directory as defined in apply_rules.md § V4


### Phase 3: Output

1. Write the modified `filter_result.json` atomically (collect all changes, write once)
2. Write change log to the same directory as the target:
   - filter-verify source → `filter_verify_apply_log.txt`
   - data-verify source → `data_verify_apply_log.txt`

```text
Source: {source_type} ({verification_file_name})
Applied: {timestamp}

Summary: {Whether modifications were made for all verification issues}

[{check_id}]: {Description of what was modified/done}
[{check_id}]: {Description of what was modified/done}
...
```
