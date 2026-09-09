#!/usr/bin/env python3
"""
Extract links from structured HTML tags.

Utilizes Nature/Springer HTML <section data-title="..."> tags
to deterministically categorize links into data_availability / code_availability / other.
"""

import json
import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    sys.exit(1)


# Link type identification rules
LINK_TYPE_PATTERNS = {
    "github": [r'github\.com', r'gitlab\.com', r'bitbucket\.org'],
    "huggingface": [r'huggingface\.co'],
    "zenodo": [r'zenodo\.org', r'10\.5281/zenodo'],
    "google_drive": [r'drive\.google\.com', r'docs\.google\.com'],
    "dropbox": [r'dropbox\.com'],
    "codeocean": [r'codeocean\.com', r'24433/co'],
}

# Skip links in these sections
SKIP_SECTIONS = {
    "Inline Recommendations", "References", "Author information",
    "Ethics declarations", "Additional information",
    "Rights and permissions",
    "About this article", "Peer review", "Extended data",
}

# data-title -> internal section name
AVAILABILITY_SECTION_MAP = {
    "Data availability": "data_availability",
    "Code availability": "code_availability",
    "Data and code availability": "data_availability",
    "Data and materials availability": "data_availability",
    "Software availability": "code_availability",
    "Supplementary information": "supplementary_information",
}


def truncate_context(text: str, max_length: int = 400) -> str:
    """Intelligently truncate context text at word boundaries."""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space].strip()
    return truncated.strip()


def classify_link(url: str) -> str:
    """Classify link type based on URL patterns."""
    url_lower = url.lower()
    for link_type, patterns in LINK_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return link_type
    return "other"


def _get_section_for_tag(tag) -> str | None:
    """
    Traverse up the DOM to find the nearest <section data-title="..."> ancestor,
    returning the mapped section name, or None to indicate skipping.
    """
    for ancestor in tag.parents:
        if ancestor.name != "section":
            continue
        title = ancestor.get("data-title", "")
        if not title:
            # <section> without data-title (e.g. "further reading") -> Skip
            return None
        if title in SKIP_SECTIONS:
            return None
        if title in AVAILABILITY_SECTION_MAP:
            return AVAILABILITY_SECTION_MAP[title]
        return "other"
    return "other"


def _get_context(tag) -> str:
    """Get plain text of parent <p> as context."""
    p = tag.find_parent("p")
    if p:
        text = p.get_text(separator=" ", strip=True)
        return truncate_context(' '.join(text.split()), 400)
    return ""


def _is_citation_ref(tag) -> bool:
    """Determine if it is a link in a citation marker (pure numeric citation in <sup>)."""
    if tag.get("data-test") == "citation-ref":
        return True
    # Inside <sup>, href points to #ref-CR
    parent_sup = tag.find_parent("sup")
    if parent_sup:
        href = tag.get("href", "")
        if "#ref-CR" in href or "#ref-" in href:
            return True
    return False


def extract_links(html_path: str) -> dict:
    """
    Extract links from structured HTML tags.

    Args:
        html_path: HTML file path

    Returns:
        dict: {links: [...], data_availability: [...], code_availability: [...]}
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Restrict to article body to avoid navigation, footer, sidebar links
    article_body = soup.find("div", class_="c-article-body")
    if article_body is None:
        # Fallback for simplified HTML without full page chrome
        article_body = soup

    links = []
    seen_urls = {}  # url -> index in links list
    url_avail_sections = {}  # url -> set of availability sections

    for a_tag in article_body.find_all('a', href=True):
        href = a_tag['href']

        # Filter non-http links
        if not href.lower().startswith(('http://', 'https://')):
            continue

        # Skip citation marker links
        if _is_citation_ref(a_tag):
            continue

        # Check section
        section = _get_section_for_tag(a_tag)
        if section is None:
            # In SKIP_SECTIONS, skip
            continue

        url = href
        context = _get_context(a_tag)

        # Record availability section (same URL can appear in both data and code)
        if section in ("data_availability", "code_availability"):
            if url not in url_avail_sections:
                url_avail_sections[url] = set()
            url_avail_sections[url].add(section)

        if url in seen_urls:
            # Deduplicate: If new location has more specific section, update existing record
            if section != "other":
                idx = seen_urls[url]
                if links[idx]["section"] == "other":
                    links[idx]["section"] = section
                    links[idx]["context"] = context
            continue

        seen_urls[url] = len(links)
        links.append({
            "url": url,
            "type": classify_link(url),
            "context": context,
            "section": section,
        })

    print(f"Found {len(links)} links from HTML")

    # Build availability lists from url_avail_sections (same URL can be in both lists)
    data_availability = []
    code_availability = []
    seen_data = set()
    seen_code = set()
    for url, sections in url_avail_sections.items():
        if "data_availability" in sections and url not in seen_data:
            data_availability.append(url)
            seen_data.add(url)
        if "code_availability" in sections and url not in seen_code:
            code_availability.append(url)
            seen_code.add(url)

    return {
        "links": links,
        "data_availability": data_availability,
        "code_availability": code_availability,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_links.py <html_path> <output_path>")
        print("")
        print("Arguments:")
        print("  html_path   Path to the HTML file")
        print("  output_path Path for output JSON file")
        print("")
        print("Example:")
        print("  python extract_links.py paper.html output/links.json")
        sys.exit(1)

    html_path = sys.argv[1]
    output_path = sys.argv[2]

    if not Path(html_path).exists():
        print(f"Error: HTML file not found: {html_path}")
        sys.exit(1)

    print(f"Extracting links from: {html_path}")

    try:
        result = extract_links(html_path)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\nExtraction complete:")
        print(f"  Total links: {len(result['links'])}")
        print(f"  Data availability links: {len(result['data_availability'])}")
        print(f"  Code availability links: {len(result['code_availability'])}")
        print(f"  Output: {output_path}")

    except Exception as e:
        print(f"Error extracting links: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
