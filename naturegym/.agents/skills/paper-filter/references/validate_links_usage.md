# Link Validation Script: `scripts/validate_links.py`

## What It Does

Verifies zero-interaction accessibility of given URLs. Sends HTTP requests to each URL and determines whether it can be directly downloaded without login, application, or signing agreements.

Checks performed:
- HTTP status codes (any 2xx is treated as reachable)
- Whether the URL redirects to a login/application page
- Whether page content contains authentication keywords (e.g., "request access", "sign in")
- Specialized checks for cloud storage links (Google Drive, Baidu Pan, Dropbox)

The script has built-in retry logic (up to 3 attempts for timeouts and connection errors). DOI links automatically use a longer timeout (90s).

## Proxy / SSL Configuration

If the environment uses an HTTPS proxy (e.g. Clash, V2Ray, mitmproxy), the proxy's MITM certificate may cause SSL verification failures. Set the following environment variable to skip SSL verification:

```bash
export VALIDATE_LINKS_NO_SSL_VERIFY=1
python scripts/validate_links.py URL1 URL2 ...
```

Or as a one-liner:

```bash
VALIDATE_LINKS_NO_SSL_VERIFY=1 python scripts/validate_links.py URL1 URL2 ...
```

## Usage

**Pass URLs as arguments (recommended)**:

```bash
python scripts/validate_links.py URL1 URL2 URL3 ...
```

**Read from a JSON file**:

```bash
python scripts/validate_links.py --file data_links.json
```

Optional arguments:
- `--output PATH`: Write JSON results to a file (default: stdout)

Log/progress messages go to stderr and do not interfere with JSON parsing on stdout.

## Output Format

The script outputs the following JSON on stdout:

```json
{
  "total": 3,
  "accessible": 2,
  "requires_auth": 1,
  "not_found": 0,
  "error": 0,
  "results": [
    {
      "url": "https://zenodo.org/record/xxx",
      "status": "accessible",
      "http_code": 200,
      "notes": null,
      "final_url": "https://zenodo.org/record/xxx",
      "cloud_type": null
    },
    {
      "url": "https://figshare.com/articles/xxx",
      "status": "accessible",
      "http_code": 202,
      "notes": null,
      "final_url": "https://figshare.com/articles/xxx",
      "cloud_type": null
    },
    {
      "url": "https://physionet.org/content/mimiciii/",
      "status": "requires_auth",
      "http_code": null,
      "notes": "Domain physionet.org typically requires authentication",
      "final_url": null,
      "cloud_type": null
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | The original input URL |
| `status` | string | Accessibility verdict (see table below) |
| `http_code` | number \| null | Actual HTTP status code |
| `notes` | string \| null | Additional details (error reason, retry info, etc.) |
| `final_url` | string \| null | Final URL after redirects |
| `cloud_type` | string \| null | Cloud storage type (google_drive / baidu_pan / dropbox / onedrive / mega / box) |
| `file_size` | number \| null | File size in bytes from Content-Length header. Null when: server doesn't send Content-Length (chunked transfer), cloud storage returns HTML instead of file (Baidu Pan, Google Drive confirmation pages), or request failed |
| `file_size_source` | string \| null | How file_size was obtained (currently always `"content_length"` when non-null) |

### Status Values

| status | Meaning | Rule 3.1 Verdict |
|--------|---------|------------------|
| `accessible` | Directly downloadable, no authentication needed | Pass |
| `requires_auth` | Requires login or access application | Reject |
| `redirect_to_auth` | Redirects to an authentication page | Reject |
| `not_found` | Link is dead (404) | Reject |
| `error` | Network error/timeout (after retries) | Reject |

## Important: Only Pass Data-Relevant URLs

**Do not pass the preprocessed `links.json` file directly to this script.** `links.json` contains all links extracted from the paper (code repositories, cited papers, funding agency pages, etc.), most of which are unrelated to data acquisition.

Correct workflow:
1. Identify the source links needed for D_dev and D_eval
2. Pass only those data source links as arguments to the script
3. Record the script's `results` array as-is into the `links_checked` field
