# Size Estimation Script: `scripts/estimate_size.py`

## What It Does

Estimates total data size without downloading, using three sources in decreasing confidence order:

1. **Content-Length headers** (high confidence): From `validate_links.py` output's `file_size` fields
2. **Platform API queries** (medium confidence): GitHub, HuggingFace, Zenodo, Figshare APIs
3. **Paper text parsing** (low confidence): Regex matching size mentions near dataset keywords

Outputs a size tier (S/M/L) and confidence level for Rule 3.6 judgment.

## Usage

```bash
python scripts/estimate_size.py --links-result <validate_links_output.json> [--paper-text <text.md>] [--output result.json]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--links-result` | Yes | Path to `validate_links.py` JSON output (contains `file_size` per URL) |
| `--paper-text` | No | Path to paper text file (`preprocessed/text.md`) for text-based estimation |
| `--output`, `-o` | No | Save JSON results to file (default: stdout) |

### Proxy / SSL Configuration

Same as `validate_links.py` — set `VALIDATE_LINKS_NO_SSL_VERIFY=1` if using an HTTPS proxy.

## Output Format

```json
{
  "per_url_estimates": [
    {
      "url": "https://zenodo.org/record/xxx/files/data.tar.gz",
      "estimated_bytes": 3221225472,
      "source": "content_length",
      "confidence": "high"
    }
  ],
  "paper_text_estimates": [
    {
      "text": "...dataset comprises 50GB of...",
      "estimated_bytes": 53687091200,
      "confidence": "low"
    }
  ],
  "total_estimated_bytes": 3221225472,
  "total_estimated_size": "3.0 GB",
  "estimation_method": "content_length",
  "confidence": "high",
  "size_tier": "M",
  "tier_thresholds": {
    "S_max_bytes": 1073741824,
    "L_min_bytes": 53687091200
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `per_url_estimates` | array | Per-URL size estimates from Content-Length and platform APIs |
| `paper_text_estimates` | array | Size mentions extracted from paper text |
| `total_estimated_bytes` | number \| null | Aggregated total estimate in bytes |
| `total_estimated_size` | string \| null | Human-readable total (e.g., "3.0 GB") |
| `estimation_method` | string | Primary method used: `content_length`, `api`, `paper_text`, `mixed`, `indeterminate` |
| `confidence` | string | Overall confidence: `high`, `medium`, `low`, `indeterminate` |
| `size_tier` | string \| null | Tier classification: `S` (< 1GB), `M` (1-50GB), `L` (> 50GB) |
| `tier_thresholds` | object | Threshold values in bytes |

### Confidence Levels

| Level | Condition |
|-------|-----------|
| `high` | Content-Length covers >80% of data URLs |
| `medium` | API estimates cover >50%, or partial Content-Length coverage |
| `low` | Only paper text mentions available |
| `indeterminate` | No size information from any source |

### Size Tiers

| Tier | Range | Rule 3.6 Verdict |
|------|-------|------------------|
| S | < 1 GB | Pass |
| M | 1 - 50 GB | Pass |
| L | > 50 GB | Reject |
| null | Indeterminate | Reject |

## Compression Ratios

For compressed files, the estimated decompressed size is `raw_bytes * ratio`:

| Extension | Ratio |
|-----------|-------|
| `.gz`, `.tgz`, `.tar.gz`, `.zip` | 3x |
| `.bz2`, `.tar.bz2`, `.xz`, `.tar.xz`, `.7z` | 5x |
| `.zst`, `.tar.zst` | 3x |
| `.lz4` | 2x |

### GitHub Repository Size Compensation

The GitHub API `size` field returns the compressed packfile size in KB. The actual `git clone` size is typically 5-15x larger. We apply a **10x multiplier** to approximate the uncompressed clone size. This multiplier is configurable via the `GITHUB_REPO_SIZE_MULTIPLIER` constant in `estimate_size.py`.

| Platform | Size Source | Accuracy |
|----------|-------------|----------|
| GitHub | API `size` × 10 | Medium (conservative estimate) |
| HuggingFace | `siblings[].size` sum | Medium (excludes LFS if separate) |
| Zenodo | `files[].size` sum | High (exact file sizes) |
| Figshare | `files[].size` sum | High (exact file sizes) |
| Content-Length | HTTP HEAD header | High (may be null for HTML/redirects) |

## Platform APIs Queried

| Platform | API Endpoint | Size Source |
|----------|-------------|------------|
| GitHub | `api.github.com/repos/{owner}/{repo}` | Repository `size` field (KB) |
| HuggingFace | `huggingface.co/api/datasets/{id}` | `siblings[].size` sum |
| Zenodo | `zenodo.org/api/records/{id}` | `files[].size` sum |
| Figshare | `api.figshare.com/v2/articles/{id}` | `files[].size` sum |

API queries are rate-limited with 0.5s delays and deduplicated by resource ID.
