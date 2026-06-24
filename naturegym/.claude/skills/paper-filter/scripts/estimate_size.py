#!/usr/bin/env python3
"""
Zero-download data size estimation script.

Aggregates size estimates from multiple sources:
1. Content-Length from HTTP HEAD (via validate_links.py output)
2. Platform API queries (GitHub, HuggingFace, Zenodo, Figshare)
3. Paper text parsing (regex matching size mentions)

Outputs a size tier (S/M/L) and confidence level for use in Rule 3.6.

Usage:
    python estimate_size.py --links-result <validate_links_output.json> [--paper-text <text.md>] [--output result.json]
"""

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

SSL_VERIFY = os.environ.get("VALIDATE_LINKS_NO_SSL_VERIFY", "0") != "1"


def _log(msg: str):
    print(msg, file=sys.stderr)


try:
    import requests
    import urllib3
except ImportError:
    _log("Error: requests library not installed. Run: pip install requests")
    sys.exit(1)

if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Size tier thresholds
S_MAX_BYTES = 1 * 1024 * 1024 * 1024        # 1 GB
L_MIN_BYTES = 50 * 1024 * 1024 * 1024       # 50 GB

# Compression ratios for estimating decompressed size
COMPRESSION_RATIOS = {
    ".gz": 3,
    ".tgz": 3,
    ".tar.gz": 3,
    ".zip": 3,
    ".bz2": 5,
    ".tar.bz2": 5,
    ".xz": 5,
    ".tar.xz": 5,
    ".zst": 3,
    ".tar.zst": 3,
    ".7z": 5,
    ".lz4": 2,
}

# GitHub repo packfile compression multiplier
# The GitHub API 'size' field returns the compressed packfile size in KB.
# Actual git clone size is typically 5-15x larger. We use 10x as a conservative midpoint.
GITHUB_REPO_SIZE_MULTIPLIER = 10

# API request timeout
API_TIMEOUT = 30
# Cache for GitHub API (repo_full_name -> size_kb)
_github_cache: dict[str, Optional[int]] = {}


def _format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes < 1024 * 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024 * 1024):.1f} TB"


def _get_compression_ratio(url: str) -> int:
    """Get decompression multiplier based on file extension in URL."""
    path = urlparse(url).path.lower()
    # Check longer extensions first
    for ext in sorted(COMPRESSION_RATIOS.keys(), key=len, reverse=True):
        if path.endswith(ext):
            return COMPRESSION_RATIOS[ext]
    return 1


def _classify_tier(total_bytes: int) -> str:
    """Classify total size into S/M/L tier."""
    if total_bytes <= S_MAX_BYTES:
        return "S"
    elif total_bytes < L_MIN_BYTES:
        return "M"
    else:
        return "L"


# --- Source 1: Content-Length from validate_links output ---

def estimate_from_content_length(links_result: dict) -> list[dict]:
    """Extract file sizes from validate_links.py output.

    Returns per-URL estimates from Content-Length headers.
    """
    estimates = []
    results = links_result.get("results", [])

    for entry in results:
        url = entry.get("url", "")
        file_size = entry.get("file_size")

        if file_size is not None and file_size > 0:
            ratio = _get_compression_ratio(url)
            estimated = file_size * ratio
            estimates.append({
                "url": url,
                "estimated_bytes": estimated,
                "raw_bytes": file_size,
                "source": "content_length",
                "confidence": "high",
                "compression_ratio": ratio,
            })

    return estimates


# --- Source 2: Platform API queries ---

def _query_github_api(owner: str, repo: str) -> Optional[int]:
    """Query GitHub API for repository size (returns estimated clone size in bytes).

    The GitHub API 'size' field is the compressed packfile size in KB.
    We apply GITHUB_REPO_SIZE_MULTIPLIER to approximate the actual clone size.
    """
    cache_key = f"{owner}/{repo}"
    if cache_key in _github_cache:
        return _github_cache[cache_key]

    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            timeout=API_TIMEOUT,
            headers={"Accept": "application/vnd.github.v3+json"},
            verify=SSL_VERIFY,
        )
        if resp.status_code == 200:
            size_kb = resp.json().get("size", 0)
            size_bytes = size_kb * 1024 * GITHUB_REPO_SIZE_MULTIPLIER
            _github_cache[cache_key] = size_bytes
            return size_bytes
        elif resp.status_code == 403:
            _log(f"  GitHub API rate limited for {cache_key}")
        else:
            _log(f"  GitHub API returned {resp.status_code} for {cache_key}")
    except Exception as e:
        _log(f"  GitHub API error for {cache_key}: {e}")

    _github_cache[cache_key] = None
    return None


def _query_zenodo_api(record_id: str) -> Optional[int]:
    """Query Zenodo API for total file sizes in a record."""
    try:
        resp = requests.get(
            f"https://zenodo.org/api/records/{record_id}",
            timeout=API_TIMEOUT,
            verify=SSL_VERIFY,
        )
        if resp.status_code == 200:
            files = resp.json().get("files", [])
            total = sum(f.get("size", 0) for f in files)
            return total if total > 0 else None
    except Exception as e:
        _log(f"  Zenodo API error for record {record_id}: {e}")
    return None


def _query_figshare_api(article_id: str) -> Optional[int]:
    """Query Figshare API for total file sizes."""
    try:
        resp = requests.get(
            f"https://api.figshare.com/v2/articles/{article_id}",
            timeout=API_TIMEOUT,
            verify=SSL_VERIFY,
        )
        if resp.status_code == 200:
            files = resp.json().get("files", [])
            total = sum(f.get("size", 0) for f in files)
            return total if total > 0 else None
    except Exception as e:
        _log(f"  Figshare API error for article {article_id}: {e}")
    return None


def _query_huggingface_api(repo_id: str, repo_type: str = "datasets") -> Optional[int]:
    """Query HuggingFace API for total file sizes."""
    try:
        resp = requests.get(
            f"https://huggingface.co/api/{repo_type}/{repo_id}",
            timeout=API_TIMEOUT,
            headers={"Accept": "application/json"},
            verify=SSL_VERIFY,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Try siblings (file listing)
            siblings = data.get("siblings", [])
            if siblings:
                total = sum(s.get("size", 0) for s in siblings if s.get("size"))
                if total > 0:
                    return total
            # Try cardData.dataset_size
            card = data.get("cardData", {})
            if card and card.get("dataset_size"):
                return card["dataset_size"]
    except Exception as e:
        _log(f"  HuggingFace API error for {repo_id}: {e}")
    return None


def estimate_from_platform_apis(url_pairs: list[tuple[str, str | None]]) -> list[dict]:
    """Query platform APIs for size information.

    Identifies platform-specific URLs and queries their APIs.
    Deduplicates by platform resource ID to avoid double-counting.

    Args:
        url_pairs: List of (original_url, final_url) tuples. final_url may be None.
                   Both URLs are checked for platform patterns (handles DOI redirects).
    """
    estimates = []
    seen = set()  # Track (platform, resource_id) to avoid duplicates

    for original_url, final_url in url_pairs:
        # Check both original and final URL for platform patterns
        urls_to_check = [original_url]
        if final_url and final_url != original_url:
            urls_to_check.append(final_url)

        for url in urls_to_check:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            path = parsed.path

            # GitHub
            if "github.com" in host:
                match = re.match(r'/([^/]+)/([^/]+)', path)
                if match:
                    owner, repo = match.group(1), match.group(2).rstrip('.git')
                    key = ("github", f"{owner}/{repo}")
                    if key not in seen:
                        seen.add(key)
                        size = _query_github_api(owner, repo)
                        if size is not None:
                            estimates.append({
                                "url": original_url,
                                "estimated_bytes": size,
                                "source": "github_api",
                                "confidence": "medium",
                            })
                        time.sleep(0.5)
                    break  # Don't check final_url if original matched

            # Zenodo
            elif "zenodo.org" in host:
                match = re.search(r'/records?/(\d+)', path)
                if match:
                    record_id = match.group(1)
                    key = ("zenodo", record_id)
                    if key not in seen:
                        seen.add(key)
                        size = _query_zenodo_api(record_id)
                        if size is not None:
                            estimates.append({
                                "url": original_url,
                                "estimated_bytes": size,
                                "source": "zenodo_api",
                                "confidence": "high",
                            })
                        time.sleep(0.5)
                    break

            # Figshare
            elif "figshare.com" in host:
                match = re.search(r'/articles/[^/]+/(\d+)', path)
                if match:
                    article_id = match.group(1)
                    key = ("figshare", article_id)
                    if key not in seen:
                        seen.add(key)
                        size = _query_figshare_api(article_id)
                        if size is not None:
                            estimates.append({
                                "url": original_url,
                                "estimated_bytes": size,
                                "source": "figshare_api",
                                "confidence": "high",
                            })
                        time.sleep(0.5)
                    break

            # HuggingFace
            elif "huggingface.co" in host:
                match = re.match(r'/(datasets|models)/([^/]+/[^/]+)', path)
                if match:
                    repo_type, repo_id = match.group(1), match.group(2)
                    key = ("huggingface", f"{repo_type}/{repo_id}")
                    if key not in seen:
                        seen.add(key)
                        size = _query_huggingface_api(repo_id, repo_type)
                        if size is not None:
                            estimates.append({
                                "url": original_url,
                                "estimated_bytes": size,
                                "source": "huggingface_api",
                                "confidence": "medium",
                            })
                        time.sleep(0.5)
                    break

    return estimates


# --- Source 3: Paper text parsing ---

# Pattern to match size mentions like "50 GB", "1.5 TB", "200 MB"
SIZE_PATTERN = re.compile(
    r'(\d+[\.,]?\d*)\s*(TB|GB|MB|tb|gb|mb|Tb|Gb|Mb|terabytes?|gigabytes?|megabytes?)',
    re.IGNORECASE
)

SIZE_UNITS = {
    "tb": 1024 ** 4,
    "terabyte": 1024 ** 4,
    "terabytes": 1024 ** 4,
    "gb": 1024 ** 3,
    "gigabyte": 1024 ** 3,
    "gigabytes": 1024 ** 3,
    "mb": 1024 ** 2,
    "megabyte": 1024 ** 2,
    "megabytes": 1024 ** 2,
}

# Context patterns that indicate the mention refers to dataset size
DATASET_CONTEXT_PATTERNS = [
    r'dataset',
    r'data\s*set',
    r'training\s+data',
    r'test\s+data',
    r'corpus',
    r'benchmark',
    r'download',
    r'total\s+size',
    r'comprises',
    r'containing',
    r'consists?\s+of',
]
DATASET_CONTEXT_RE = re.compile('|'.join(DATASET_CONTEXT_PATTERNS), re.IGNORECASE)

# Context patterns that indicate the mention is NOT about dataset size (false positives)
EXCLUDE_CONTEXT_PATTERNS = [
    r'\bRAM\b',
    r'\bmemory\b',
    r'\bGPU\s+memory\b',
    r'\bVRAM\b',
    r'\bdisk\s+space\b',
    r'\bstorage\s+capacity\b',
    r'\bserver\b',
    r'\bmachine\b',
    r'\bhardware\b',
    r'\bparameters?\b',
    r'\bweights?\b',
    r'\bmodel\s+size\b',
]
EXCLUDE_CONTEXT_RE = re.compile('|'.join(EXCLUDE_CONTEXT_PATTERNS), re.IGNORECASE)


def estimate_from_paper_text(text: str) -> list[dict]:
    """Parse paper text for data size mentions.

    Returns estimates from text mentions with surrounding context.
    Only includes mentions that appear near dataset-related keywords.
    """
    estimates = []
    seen_values = set()

    for match in SIZE_PATTERN.finditer(text):
        value_str = match.group(1).replace(',', '.')
        unit = match.group(2).lower()

        try:
            value = float(value_str)
        except ValueError:
            continue

        if value <= 0:
            continue

        multiplier = SIZE_UNITS.get(unit)
        if multiplier is None:
            continue

        estimated_bytes = int(value * multiplier)

        # Avoid duplicates (same numeric value)
        if estimated_bytes in seen_values:
            continue

        # Check surrounding context (200 chars before and after)
        start = max(0, match.start() - 200)
        end = min(len(text), match.end() + 200)
        context = text[start:end]

        if not DATASET_CONTEXT_RE.search(context):
            continue

        # Exclude mentions about RAM, GPU memory, model size, etc.
        if EXCLUDE_CONTEXT_RE.search(context):
            continue

        seen_values.add(estimated_bytes)

        # Extract a short text snippet for reporting
        snippet_start = max(0, match.start() - 40)
        snippet_end = min(len(text), match.end() + 40)
        snippet = text[snippet_start:snippet_end].replace('\n', ' ').strip()

        estimates.append({
            "text": snippet,
            "estimated_bytes": estimated_bytes,
            "confidence": "low",
        })

    return estimates


# --- Aggregation ---

def aggregate_estimates(
    content_length_estimates: list[dict],
    api_estimates: list[dict],
    paper_text_estimates: list[dict],
) -> dict:
    """Aggregate estimates from all sources into a final result.

    Priority: Content-Length > Platform API > Paper text.
    Uses the highest-confidence source available.
    """
    per_url_estimates = []

    # Merge content_length and api estimates, preferring content_length
    url_to_cl = {}
    for est in content_length_estimates:
        url_to_cl[est["url"]] = est
        per_url_estimates.append({
            "url": est["url"],
            "estimated_bytes": est["estimated_bytes"],
            "source": est["source"],
            "confidence": est["confidence"],
        })

    for est in api_estimates:
        if est["url"] not in url_to_cl:
            per_url_estimates.append({
                "url": est["url"],
                "estimated_bytes": est["estimated_bytes"],
                "source": est["source"],
                "confidence": est["confidence"],
            })

    # Determine total and method
    total_bytes = None
    method = "indeterminate"
    confidence = "indeterminate"

    if content_length_estimates:
        # Sum content-length estimates (deduplicated by URL)
        cl_total = sum(e["estimated_bytes"] for e in content_length_estimates)
        # If API estimates cover URLs not in content-length, add them
        api_extra = sum(
            e["estimated_bytes"] for e in api_estimates
            if e["url"] not in url_to_cl
        )
        total_bytes = cl_total + api_extra

        total_urls = len(content_length_estimates) + len([
            e for e in api_estimates if e["url"] not in url_to_cl
        ])
        all_urls = len(set(
            [e["url"] for e in content_length_estimates] +
            [e["url"] for e in api_estimates]
        ))

        if all_urls > 0 and len(content_length_estimates) / max(all_urls, 1) >= 0.8:
            confidence = "high"
            method = "content_length"
        else:
            confidence = "medium"
            method = "mixed"

    elif api_estimates:
        total_bytes = sum(e["estimated_bytes"] for e in api_estimates)
        confidence = "medium"
        method = "api"

    elif paper_text_estimates:
        # Use the largest paper text estimate as the total
        total_bytes = max(e["estimated_bytes"] for e in paper_text_estimates)
        confidence = "low"
        method = "paper_text"

    # Build result
    result = {
        "per_url_estimates": per_url_estimates,
        "paper_text_estimates": [
            {"text": e["text"], "estimated_bytes": e["estimated_bytes"], "confidence": e["confidence"]}
            for e in paper_text_estimates
        ],
        "total_estimated_bytes": total_bytes,
        "total_estimated_size": _format_size(total_bytes) if total_bytes is not None else None,
        "estimation_method": method,
        "confidence": confidence,
        "size_tier": _classify_tier(total_bytes) if total_bytes is not None else None,
        "tier_thresholds": {
            "S_max_bytes": S_MAX_BYTES,
            "L_min_bytes": L_MIN_BYTES,
        },
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Zero-download data size estimation for Rule 3.6.",
        epilog="Examples:\n"
               "  python estimate_size.py --links-result validate_output.json\n"
               "  python estimate_size.py --links-result validate_output.json --paper-text text.md\n"
               "  python estimate_size.py --links-result validate_output.json --paper-text text.md --output size.json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--links-result", required=True, metavar="PATH",
        help="Path to validate_links.py JSON output",
    )
    parser.add_argument(
        "--paper-text", metavar="PATH",
        help="Path to paper text file (preprocessed/text.md) for text-based estimation",
    )
    parser.add_argument(
        "--output", "-o", metavar="PATH",
        help="Save JSON results to file (default: stdout)",
    )

    args = parser.parse_args()

    # Load validate_links output
    links_path = Path(args.links_result)
    if not links_path.exists():
        _log(f"Error: File not found: {links_path}")
        sys.exit(1)

    with open(links_path, 'r', encoding='utf-8') as f:
        links_result = json.load(f)

    # Source 1: Content-Length
    _log("Estimating from Content-Length headers...")
    cl_estimates = estimate_from_content_length(links_result)
    _log(f"  Found {len(cl_estimates)} URLs with Content-Length")

    # Source 2: Platform APIs
    all_url_pairs = [
        (r["url"], r.get("final_url"))
        for r in links_result.get("results", [])
    ]
    _log("Querying platform APIs...")
    api_estimates = estimate_from_platform_apis(all_url_pairs)
    _log(f"  Got {len(api_estimates)} API estimates")

    # Source 3: Paper text
    paper_estimates = []
    if args.paper_text:
        text_path = Path(args.paper_text)
        if text_path.exists():
            _log("Parsing paper text for size mentions...")
            with open(text_path, 'r', encoding='utf-8') as f:
                paper_text = f.read()
            paper_estimates = estimate_from_paper_text(paper_text)
            _log(f"  Found {len(paper_estimates)} text mentions")
        else:
            _log(f"Warning: Paper text file not found: {text_path}")

    # Aggregate
    result = aggregate_estimates(cl_estimates, api_estimates, paper_estimates)

    # Output
    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_json)
        _log(f"\nResults saved to: {output_path}")
    else:
        print(output_json)

    # Summary
    _log(f"\n--- SIZE ESTIMATION SUMMARY ---")
    _log(f"Method: {result['estimation_method']}")
    _log(f"Confidence: {result['confidence']}")
    _log(f"Total: {result['total_estimated_size'] or 'indeterminate'}")
    _log(f"Tier: {result['size_tier'] or 'indeterminate'}")


if __name__ == "__main__":
    main()
