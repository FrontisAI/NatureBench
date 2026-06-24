#!/usr/bin/env python3
"""
Extract text content from HTML and output as Markdown.

Utilizes Nature/Springer HTML <section data-title="..."> structure,
iterating through sections and converting effectively to clean Markdown.
"""

import json
import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    print("Error: beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    sys.exit(1)


# Skip these sections (consistent with extract_links)
SKIP_SECTIONS = {
    "Inline Recommendations", "References", "Author information",
    "Ethics declarations", "Additional information",
    "Supplementary information", "Rights and permissions",
    "About this article", "Peer review", "Extended data",
}


def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove excess blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove excess inline spaces
    text = re.sub(r' {3,}', '  ', text)
    return text.strip()


def _convert_element(el) -> str:
    """
    Recursively convert HTML elements to Markdown text.
    """
    if isinstance(el, NavigableString):
        return str(el)

    if not isinstance(el, Tag):
        return ""

    tag_name = el.name

    # Pure numeric citation markers in <sup> → Delete
    if tag_name == "sup":
        # Check if it's a citation marker (contains citation-ref or #ref- link)
        ref_link = el.find("a", attrs={"data-test": "citation-ref"})
        if ref_link:
            return ""
        ref_link = el.find("a", href=lambda h: h and "#ref-" in h)
        if ref_link:
            return ""
        # Skip <sup> with pure numeric content (citation number)
        text = el.get_text(strip=True)
        if re.match(r'^[\d,\s–-]+$', text):
            return ""
        # Keep other <sup> content
        return "".join(_convert_element(c) for c in el.children)

    # <span class="mathjax-tex"> → Keep LaTeX original
    if tag_name == "span" and "mathjax-tex" in el.get("class", []):
        return el.get_text()

    # Formula block div
    if tag_name == "div" and "c-article-equation" in el.get("class", []):
        eq_content = el.find("span", class_="mathjax-tex")
        if eq_content:
            latex = eq_content.get_text().strip()
            return f"\n\n{latex}\n\n"
        return ""

    # <figure> → Skip img, keep figcaption
    if tag_name == "figure":
        caption = el.find("figcaption")
        if caption:
            caption_text = caption.get_text(separator=" ", strip=True)
            return f"\n\n**{caption_text}**\n\n"
        return ""

    # Entire figure wrapper div → Process as figure
    if tag_name == "div" and "c-article-section__figure" in el.get("class", []):
        figure = el.find("figure")
        if figure:
            return _convert_element(figure)
        return ""

    # table wrapper → Process same as figure
    if tag_name == "div" and "c-article-table" in el.get("class", []):
        figure = el.find("figure")
        if figure:
            return _convert_element(figure)
        return ""

    # "Full size image" / "Full size table" link → Skip
    if tag_name == "div" and "u-hide-print" in el.get("class", []):
        return ""

    # <img> → Skip
    if tag_name == "img" or tag_name == "picture" or tag_name == "source":
        return ""

    # <h2> → ## heading
    if tag_name == "h2":
        text = el.get_text(separator=" ", strip=True)
        return f"\n\n## {text}\n\n"

    # <h3> → ### heading
    if tag_name == "h3":
        text = el.get_text(separator=" ", strip=True)
        return f"\n\n### {text}\n\n"

    # <h4> → #### heading
    if tag_name == "h4":
        text = el.get_text(separator=" ", strip=True)
        return f"\n\n#### {text}\n\n"

    # <p> → Paragraph
    if tag_name == "p":
        inner = "".join(_convert_element(c) for c in el.children)
        inner = ' '.join(inner.split())
        return f"\n\n{inner}\n\n"

    # <a> → markdown link or plain text
    if tag_name == "a":
        href = el.get("href", "")
        text = "".join(_convert_element(c) for c in el.children)
        text = text.strip()
        if href.startswith(("http://", "https://")):
            return f"[{text}]({href})"
        # Internal anchor/relative link → Keep text only
        return text

    # <b> / <strong> → **bold**
    if tag_name in ("b", "strong"):
        inner = "".join(_convert_element(c) for c in el.children)
        inner = inner.strip()
        if inner:
            return f"**{inner}**"
        return ""

    # <i> / <em> → *italic*
    if tag_name in ("i", "em"):
        inner = "".join(_convert_element(c) for c in el.children)
        inner = inner.strip()
        if inner:
            return f"*{inner}*"
        return ""

    # <ul> / <ol> → list
    if tag_name == "ul":
        items = []
        for li in el.find_all("li", recursive=False):
            item_text = "".join(_convert_element(c) for c in li.children)
            item_text = ' '.join(item_text.split())
            items.append(f"- {item_text}")
        return "\n\n" + "\n".join(items) + "\n\n"

    if tag_name == "ol":
        items = []
        for i, li in enumerate(el.find_all("li", recursive=False), 1):
            item_text = "".join(_convert_element(c) for c in li.children)
            item_text = ' '.join(item_text.split())
            items.append(f"{i}. {item_text}")
        return "\n\n" + "\n".join(items) + "\n\n"

    # <script> / <style> → Skip
    if tag_name in ("script", "style"):
        return ""

    # Default: Recursively process children
    return "".join(_convert_element(c) for c in el.children)


def extract_text_from_html(html_path: str, output_path: str) -> dict:
    """
    Extract text from HTML and save as Markdown format.

    Args:
        html_path: HTML file path
        output_path: Output Markdown file path

    Returns:
        dict: Extraction stats {char_count, word_count}
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    parts = []

    # Extract paper title from <h1 class="c-article-title">
    title_tag = soup.find("h1", class_="c-article-title")
    paper_title = title_tag.get_text(separator=" ", strip=True) if title_tag else ""
    if paper_title:
        parts.append(f"# {paper_title}\n")

    for section in soup.find_all("section", attrs={"data-title": True}):
        title = section["data-title"]

        if title in SKIP_SECTIONS:
            continue

        # Abstract special handling: aria-labelledby="Abs1"
        if title == "Abstract":
            parts.append("\n\n## Abstract\n\n")
            content_div = section.find("div", class_="c-article-section__content")
            if content_div:
                for child in content_div.children:
                    parts.append(_convert_element(child))
            continue

        # Acknowledgements special handling
        if title == "Acknowledgements":
            parts.append("\n\n## Acknowledgements\n\n")
            content_div = section.find("div", class_="c-article-section__content")
            if content_div:
                for child in content_div.children:
                    parts.append(_convert_element(child))
            continue

        # Regular section
        content_div = section.find("div", class_="c-article-section__content")
        if not content_div:
            continue

        # Use heading from <h2> tag
        h2 = section.find("h2")
        if h2:
            heading_text = h2.get_text(separator=" ", strip=True)
            parts.append(f"\n\n## {heading_text}\n\n")

        for child in content_div.children:
            parts.append(_convert_element(child))

    full_text = "".join(parts)
    full_text = clean_text(full_text)

    stats = {
        "title": paper_title,
        "char_count": len(full_text),
        "word_count": len(full_text.split()),
    }

    # Save as Markdown
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_text)

    return stats


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_text.py <html_path> <output_path>")
        print("")
        print("Arguments:")
        print("  html_path    Path to the HTML file")
        print("  output_path  Path for output Markdown file")
        print("")
        print("Example:")
        print("  python extract_text.py paper.html output/text.md")
        sys.exit(1)

    html_path = sys.argv[1]
    output_path = sys.argv[2]

    if not Path(html_path).exists():
        print(f"Error: HTML file not found: {html_path}")
        sys.exit(1)

    print(f"Extracting text from: {html_path}")

    try:
        stats = extract_text_from_html(html_path, output_path)

        print(f"\nExtraction complete:")
        print(f"  Characters: {stats['char_count']}")
        print(f"  Words: {stats['word_count']}")
        print(f"  Output: {output_path}")

        # Output JSON format stats to stdout
        print(f"\n__STATS__:{json.dumps(stats)}")

    except Exception as e:
        print(f"Error extracting text: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
