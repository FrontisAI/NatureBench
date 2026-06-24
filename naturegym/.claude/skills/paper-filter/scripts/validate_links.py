#!/usr/bin/env python3
"""
Script to validate data link accessibility.
Used in Level 3 filtering to check if data is accessible with zero interaction.

If the current environment uses an HTTPS proxy (e.g. Clash, V2Ray),
the proxy's MITM certificate may cause SSL verification failures.
Set the environment variable to skip SSL verification in this case:

    export VALIDATE_LINKS_NO_SSL_VERIFY=1
    python validate_links.py ...

Or run once:

    VALIDATE_LINKS_NO_SSL_VERIFY=1 python validate_links.py ...
"""

import argparse
import json
import os
import re
import sys
import time
import warnings
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs


def _log(msg: str):
    """Output logs to stderr avoiding interference with stdout JSON output."""
    print(msg, file=sys.stderr)


def _extract_content_length(response) -> Optional[int]:
    """Extract Content-Length from HTTP response headers.

    Returns the file size in bytes, or None if:
    - Content-Length is absent or invalid
    - Content-Type is text/html (response is a web page, not a file)
    """
    # HTML pages return Content-Length of the page itself, not the actual file.
    # Discard to avoid recording landing pages, confirmation pages, etc. as file sizes.
    content_type = response.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        return None
    cl = response.headers.get('Content-Length')
    if cl is not None:
        try:
            size = int(cl)
            return size if size > 0 else None
        except (ValueError, TypeError):
            return None
    return None

try:
    import requests
    import urllib3
except ImportError:
    _log("Error: requests library not installed. Run: pip install requests")
    sys.exit(1)

# SSL verification control: Set VALIDATE_LINKS_NO_SSL_VERIFY=1 to skip SSL verification
# Useful when using proxies (like Clash) for HTTPS decryption
SSL_VERIFY = os.environ.get("VALIDATE_LINKS_NO_SSL_VERIFY", "0") != "1"

if not SSL_VERIFY:
    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _log("Warning: SSL verification is disabled (VALIDATE_LINKS_NO_SSL_VERIFY=1)")


# Domain patterns requiring authentication
AUTH_REQUIRED_PATTERNS = [
    "physionet.org",  # MIMIC etc. medical data
    "synapse.org",    # Synapse platform
    "dbgap.ncbi.nlm.nih.gov",  # dbGaP
    "ega-archive.org",  # European Genome-phenome Archive
    "ukbiobank.ac.uk",  # UK Biobank
]

# Cloud storage domain patterns
CLOUD_STORAGE_PATTERNS = {
    "drive.google.com": "google_drive",
    "docs.google.com": "google_drive",
    "dropbox.com": "dropbox",
    "pan.baidu.com": "baidu_pan",
    "onedrive.live.com": "onedrive",
    "1drv.ms": "onedrive",
    "mega.nz": "mega",
    "box.com": "box",
}

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 5, 10]  # Retry interval (seconds)

# Default timeout (seconds)
DEFAULT_TIMEOUT = 60
DOI_TIMEOUT = 90  # DOI links have multi-level redirects requiring longer timeout


def check_google_drive(url: str, timeout: int = 30) -> dict:
    """Check accessibility of Google Drive links."""
    result = {
        "url": url,
        "status": "error",
        "http_code": None,
        "notes": None,
        "final_url": None,
        "cloud_type": "google_drive",
        "file_size": None,
        "file_size_source": None
    }

    # Extract file ID
    file_id = None
    if "/file/d/" in url:
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
    elif "id=" in url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        file_id = params.get("id", [None])[0]

    if not file_id:
        result["notes"] = "Cannot extract file ID from Google Drive URL"
        return result

    # Construct direct download link for checking
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PaperFilterBot/1.0)"}
        response = requests.head(direct_url, timeout=timeout, allow_redirects=True, headers=headers, verify=SSL_VERIFY)
        result["http_code"] = response.status_code
        result["final_url"] = response.url

        if response.status_code == 200:
            result["status"] = "accessible"
            result["notes"] = "Google Drive public link"
            file_size = _extract_content_length(response)
            if file_size is not None:
                result["file_size"] = file_size
                result["file_size_source"] = "content_length"
        elif response.status_code in [401, 403]:
            result["status"] = "requires_auth"
            result["notes"] = "Google Drive link requires authentication or is not shared publicly"
        elif response.status_code == 404:
            result["status"] = "not_found"
            result["notes"] = "Google Drive file not found"
        else:
            # Try GET request to check for confirmation page
            get_response = requests.get(direct_url, timeout=timeout, headers=headers, stream=True, verify=SSL_VERIFY)
            content = ""
            for chunk in get_response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    content += chunk if isinstance(chunk, str) else chunk.decode('utf-8', errors='ignore')
                    if len(content) > 10000:
                        break

            if "download" in content.lower() or "confirm" in content.lower():
                result["status"] = "accessible"
                result["notes"] = "Google Drive public link (large file with confirmation page)"
                # Content-Length here is the HTML page size, not the actual file — leave file_size as None
            elif "sign in" in content.lower() or "request access" in content.lower():
                result["status"] = "requires_auth"
                result["notes"] = "Google Drive link requires authentication"
            else:
                result["status"] = "accessible"
                result["notes"] = "Google Drive link appears accessible"

    except Exception as e:
        result["notes"] = f"Error checking Google Drive: {str(e)[:100]}"

    return result


def check_baidu_pan(url: str, timeout: int = 30) -> dict:
    """Check accessibility of Baidu Netdisk links."""
    result = {
        "url": url,
        "status": "error",
        "http_code": None,
        "notes": None,
        "final_url": None,
        "cloud_type": "baidu_pan",
        "file_size": None,
        "file_size_source": None
    }

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, verify=SSL_VERIFY)
        result["http_code"] = response.status_code
        result["final_url"] = response.url

        content = response.text.lower()

        if response.status_code == 200:
            # Check if extraction code is required
            if "请输入提取码" in response.text or "输入提取码" in response.text:
                result["status"] = "requires_auth"
                result["notes"] = "Baidu Netdisk link requires extraction code"
            elif "文件不存在" in response.text or "已过期" in response.text:
                result["status"] = "not_found"
                result["notes"] = "Baidu Netdisk file not found or expired"
            elif "登录" in response.text and "下载" not in response.text:
                result["status"] = "requires_auth"
                result["notes"] = "Baidu Netdisk link requires login"
            else:
                result["status"] = "accessible"
                result["notes"] = "Baidu Netdisk public link"
        else:
            result["status"] = "error"
            result["notes"] = f"HTTP {response.status_code}"

    except Exception as e:
        result["notes"] = f"Error checking Baidu Pan: {str(e)[:100]}"

    return result


def check_dropbox(url: str, timeout: int = 30) -> dict:
    """Check accessibility of Dropbox links."""
    result = {
        "url": url,
        "status": "error",
        "http_code": None,
        "notes": None,
        "final_url": None,
        "cloud_type": "dropbox",
        "file_size": None,
        "file_size_source": None
    }

    # Convert to direct download link
    direct_url = url.replace("?dl=0", "?dl=1").replace("www.dropbox.com", "dl.dropboxusercontent.com")
    if "?dl=" not in direct_url:
        direct_url += "?dl=1"

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PaperFilterBot/1.0)"}
        response = requests.head(direct_url, timeout=timeout, allow_redirects=True, headers=headers, verify=SSL_VERIFY)
        result["http_code"] = response.status_code
        result["final_url"] = response.url

        if response.status_code == 200:
            result["status"] = "accessible"
            result["notes"] = "Dropbox public link"
            file_size = _extract_content_length(response)
            if file_size is not None:
                result["file_size"] = file_size
                result["file_size_source"] = "content_length"
        elif response.status_code in [401, 403]:
            result["status"] = "requires_auth"
            result["notes"] = "Dropbox link requires authentication"
        elif response.status_code == 404:
            result["status"] = "not_found"
            result["notes"] = "Dropbox file not found"
        else:
            result["status"] = "error"
            result["notes"] = f"HTTP {response.status_code}"

    except Exception as e:
        result["notes"] = f"Error checking Dropbox: {str(e)[:100]}"

    return result


def _is_retryable_error(exc: Exception) -> bool:
    """Determine if exception is likely retryable (temporary network issue)."""
    return isinstance(exc, (requests.exceptions.Timeout,
                            requests.exceptions.ConnectionError))


def _check_response_content(url: str, timeout: int, headers: dict, result: dict) -> dict:
    """
    HTTP 2xx is directly marked as accessible.
    """
    result["status"] = "accessible"
    return result


def _try_get_fallback(url: str, timeout: int, headers: dict, result: dict) -> dict:
    """
    When HEAD returns unexpected status code, fallback to GET request.
    """
    get_response = requests.get(url, timeout=timeout, allow_redirects=True,
                                headers=headers, stream=True, verify=SSL_VERIFY)
    result["http_code"] = get_response.status_code
    result["final_url"] = get_response.url

    if 200 <= get_response.status_code <= 206:
        # Extract Content-Length from GET response
        file_size = _extract_content_length(get_response)
        if file_size is not None:
            result["file_size"] = file_size
            result["file_size_source"] = "content_length"
        return _check_response_content(url, timeout, headers, result)
    elif get_response.status_code == 401:
        result["status"] = "requires_auth"
        result["notes"] = "HTTP 401 Unauthorized"
    elif get_response.status_code == 403:
        result["status"] = "requires_auth"
        result["notes"] = "HTTP 403 Forbidden"
    elif get_response.status_code == 404:
        result["status"] = "not_found"
        result["notes"] = "HTTP 404 Not Found"
    else:
        result["status"] = "error"
        result["notes"] = f"Unexpected status code: {get_response.status_code} (after GET fallback)"

    return result


def check_url(url: str, timeout: int = None) -> dict:
    """
    Check accessibility of a single URL. Supports retry mechanism.

    Returns:
        dict: {
            "url": str,
            "status": "accessible" | "requires_auth" | "not_found" | "error" | "redirect_to_auth",
            "http_code": int | None,
            "notes": str | None,
            "final_url": str | None,
            "cloud_type": str | None,
            "file_size": int | None,
            "file_size_source": str | None
        }
    """
    # Auto-select timeout: Longer timeout for DOI links
    if timeout is None:
        if "doi.org" in url:
            timeout = DOI_TIMEOUT
        else:
            timeout = DEFAULT_TIMEOUT

    result = {
        "url": url,
        "status": "error",
        "http_code": None,
        "notes": None,
        "final_url": None,
        "cloud_type": None,
        "file_size": None,
        "file_size_source": None
    }

    parsed = urlparse(url)

    # Check if a known auth-required domain
    for pattern in AUTH_REQUIRED_PATTERNS:
        if pattern in parsed.netloc:
            result["status"] = "requires_auth"
            result["notes"] = f"Domain {pattern} typically requires authentication"
            return result

    # Check if a cloud storage link, use specific check function
    for pattern, cloud_type in CLOUD_STORAGE_PATTERNS.items():
        if pattern in parsed.netloc:
            if cloud_type == "google_drive":
                return check_google_drive(url, timeout)
            elif cloud_type == "baidu_pan":
                return check_baidu_pan(url, timeout)
            elif cloud_type == "dropbox":
                return check_dropbox(url, timeout)
            else:
                # Other cloud storage uses generic check
                result["cloud_type"] = cloud_type
                break

    # Generic URL check (with retry)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PaperFilterBot/1.0)"
    }

    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            # Send HEAD request first
            response = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers, verify=SSL_VERIFY)
            result["http_code"] = response.status_code
            result["final_url"] = response.url

            if 200 <= response.status_code <= 206:
                # 2xx series uniformly considered accessible
                # Extract Content-Length for file size estimation
                file_size = _extract_content_length(response)
                if file_size is not None:
                    result["file_size"] = file_size
                    result["file_size_source"] = "content_length"

                # Check for redirect to auth page
                if response.url != url:
                    final_parsed = urlparse(response.url)
                    for pattern in AUTH_REQUIRED_PATTERNS:
                        if pattern in final_parsed.netloc:
                            result["status"] = "redirect_to_auth"
                            result["notes"] = f"Redirected to authentication domain: {final_parsed.netloc}"
                            return result

                # Try GET request to check content
                return _check_response_content(url, timeout, headers, result)

            elif response.status_code == 401:
                result["status"] = "requires_auth"
                result["notes"] = "HTTP 401 Unauthorized"
                return result  # Deterministic error, no retry

            elif response.status_code == 403:
                # HEAD returning 403 might mean HEAD not supported, try GET fallback
                return _try_get_fallback(url, timeout, headers, result)

            elif response.status_code == 404:
                result["status"] = "not_found"
                result["notes"] = "HTTP 404 Not Found"
                return result  # Deterministic error, no retry

            elif response.status_code == 405:
                # 405 Method Not Allowed: Server doesn't support HEAD, use GET fallback
                return _try_get_fallback(url, timeout, headers, result)

            elif response.status_code in [301, 302, 307, 308]:
                result["status"] = "error"
                result["notes"] = f"Redirect not followed: {response.status_code}"
                return result  # Deterministic error, no retry

            else:
                # Other unexpected status codes: Try GET fallback first
                return _try_get_fallback(url, timeout, headers, result)

        except Exception as e:
            last_exception = e
            if _is_retryable_error(e) and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                _log(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s ({type(e).__name__})")
                time.sleep(wait)
                continue
            else:
                # Non-temporary error or retries exhausted
                break

    # Reach here means retries exhausted or non-retryable exception encountered
    if last_exception is not None:
        retries_used = min(attempt + 1, MAX_RETRIES)
        if isinstance(last_exception, requests.exceptions.Timeout):
            result["status"] = "error"
            result["notes"] = f"Request timeout after {retries_used} retries, may be a temporary network issue"
        elif isinstance(last_exception, requests.exceptions.ConnectionError):
            result["status"] = "error"
            result["notes"] = f"Connection error after {retries_used} retries, may be a temporary network issue: {str(last_exception)[:80]}"
        elif isinstance(last_exception, requests.exceptions.RequestException):
            result["status"] = "error"
            result["notes"] = f"Request error: {str(last_exception)[:100]}"
        else:
            result["status"] = "error"
            result["notes"] = f"Unexpected error: {str(last_exception)[:100]}"

    return result


def validate_links(links: list[str], delay: float = 1.0) -> dict:
    """
    Validate accessibility of multiple links.

    Args:
        links: List of URLs
        delay: Request interval (seconds) to avoid ban

    Returns:
        dict: {
            "total": int,
            "accessible": int,
            "requires_auth": int,
            "not_found": int,
            "error": int,
            "results": list[dict]
        }
    """
    results = []
    stats = {
        "total": len(links),
        "accessible": 0,
        "requires_auth": 0,
        "not_found": 0,
        "error": 0,
    }

    for i, url in enumerate(links):
        _log(f"Checking [{i+1}/{len(links)}]: {url[:80]}...")

        result = check_url(url)
        results.append(result)

        # Update stats
        if result["status"] == "accessible":
            stats["accessible"] += 1
        elif result["status"] in ["requires_auth", "redirect_to_auth"]:
            stats["requires_auth"] += 1
        elif result["status"] == "not_found":
            stats["not_found"] += 1
        else:
            stats["error"] += 1

        # Delay to avoid ban
        if i < len(links) - 1:
            time.sleep(delay)

    return {
        **stats,
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate data link accessibility for zero-interaction acquisition check.",
        epilog="Examples:\n"
               "  python validate_links.py https://example.com/data.zip https://zenodo.org/record/xxx\n"
               "  python validate_links.py --file links.json\n"
               "  python validate_links.py --file links.json --output results.json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "urls", nargs="*", metavar="URL",
        help="URLs to validate (primary usage mode)",
    )
    parser.add_argument(
        "--file", "-f", dest="file", metavar="PATH",
        help="Read URLs from a JSON file instead of arguments. "
             "Supported formats: [\"url\", ...], [{\"url\": ...}, ...], "
             "{\"links\": [...], ...}",
    )
    parser.add_argument(
        "--output", "-o", dest="output", metavar="PATH",
        help="Save JSON results to file (default: stdout)",
    )

    args = parser.parse_args()

    # Determine link list
    links = []
    if args.urls:
        links = args.urls
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            _log(f"Error: File not found: {file_path}")
            sys.exit(1)

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                links = data
            elif all(isinstance(item, dict) for item in data):
                links = [item.get("url") for item in data if item.get("url")]
            else:
                links = [str(item) for item in data]
        elif isinstance(data, dict):
            raw_links = data.get("links", [])
            if raw_links and isinstance(raw_links[0], str):
                links = raw_links
            elif raw_links and isinstance(raw_links[0], dict):
                links = [item.get("url") for item in raw_links if item.get("url")]
            else:
                links = raw_links
        else:
            _log("Error: Invalid JSON format")
            sys.exit(1)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if not links:
        _log("Warning: No links to validate")
        result = {"total": 0, "accessible": 0, "requires_auth": 0, "not_found": 0, "error": 0, "results": []}
    else:
        _log(f"Validating {len(links)} links...")
        result = validate_links(links)

    # Output JSON result
    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_json)
        _log(f"\nResults saved to: {output_path}")
    else:
        print(output_json)

    # Output summary to stderr
    _log(f"\n--- SUMMARY ---")
    _log(f"Total: {result['total']}  Accessible: {result['accessible']}  "
         f"Auth: {result['requires_auth']}  NotFound: {result['not_found']}  Error: {result['error']}")

    if result['accessible'] == result['total']:
        sys.exit(0)
    elif result['accessible'] > 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
