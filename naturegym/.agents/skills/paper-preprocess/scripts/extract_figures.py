#!/usr/bin/env python3
"""
Extract figures (images and tables) from PDF. Based on structured text block detection for captions, performs intelligent cropping of figure areas.

Strategy:
1. Use page.get_text("dict") to get structured text blocks.
2. Detect captions starting with "Fig." / "Table" in independent text blocks.
3. Calculate figure area (image blocks or whitespace above the caption).
4. Render only the cropped figure area.
"""

import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)


# Simple label pattern (for standardizing labels)
FIGURE_LABEL_PATTERN = re.compile(r'Fig(?:ure)?\.?\s*(\d+)([a-zA-Z])?', re.IGNORECASE)
TABLE_LABEL_PATTERN = re.compile(r'Table\s*(\d+)([a-zA-Z])?', re.IGNORECASE)
EXTENDED_DATA_FIG_PATTERN = re.compile(r'Extended\s+Data\s+Fig(?:ure)?\.?\s*(\d+)([a-zA-Z])?', re.IGNORECASE)
EXTENDED_DATA_TABLE_PATTERN = re.compile(r'Extended\s+Data\s+Table\s*(\d+)([a-zA-Z])?', re.IGNORECASE)

# Caption start pattern: Text block first line starts with "Fig." / "Figure" / "Table" / "Extended Data Fig." / "Extended Data Table"
# Followed by number and separator (| : .)
CAPTION_START_RE = re.compile(
    r'^\s*(?:Extended\s+Data\s+(?:Fig(?:ure)?\.?\s*(\d+)|Table\s*(\d+))\s*[a-zA-Z]?\s*[\|:\.]|Fig(?:ure)?\.?\s*(\d+)\s*[a-zA-Z]?\s*[\|:\.]|Table\s*(\d+)\s*[a-zA-Z]?\s*[\|:\.])',
    re.IGNORECASE
)

def normalize_label(label: str) -> str:
    """Normalize label format."""
    label = label.strip()

    # Check Extended Data patterns first (more specific)
    ext_fig_match = EXTENDED_DATA_FIG_PATTERN.match(label)
    if ext_fig_match:
        num = ext_fig_match.group(1)
        suffix = ext_fig_match.group(2) or ""
        return f"Extended_Data_Fig_{num}{suffix}"

    ext_table_match = EXTENDED_DATA_TABLE_PATTERN.match(label)
    if ext_table_match:
        num = ext_table_match.group(1)
        suffix = ext_table_match.group(2) or ""
        return f"Extended_Data_Table_{num}{suffix}"

    fig_match = FIGURE_LABEL_PATTERN.match(label)
    if fig_match:
        num = fig_match.group(1)
        suffix = fig_match.group(2) or ""
        return f"Fig. {num}{suffix}"

    table_match = TABLE_LABEL_PATTERN.match(label)
    if table_match:
        num = table_match.group(1)
        suffix = table_match.group(2) or ""
        return f"Table {num}{suffix}"

    return label


def get_block_first_line(block: dict) -> str:
    """Get the first line of text from a block."""
    lines = block.get("lines", [])
    if not lines:
        return ""
    spans = lines[0].get("spans", [])
    if not spans:
        return ""
    return "".join(span.get("text", "") for span in spans)


def is_caption_start(text: str) -> bool:
    """
    Determine if text is the start of a figure/table caption.
    Exclude figures/tables with number > 10 (likely supplementary).
    """
    if not text or not text.strip():
        return False

    match = CAPTION_START_RE.match(text)
    if not match:
        return False

    # Check number: figure number > 10 might be supplementary figure
    # Groups: (1) Extended Data Fig num, (2) Extended Data Table num, (3) Fig num, (4) Table num
    ext_fig_num = match.group(1)
    ext_table_num = match.group(2)
    fig_num = match.group(3)
    table_num = match.group(4)

    # Extended Data figures/tables are always included (no number limit)
    if ext_fig_num or ext_table_num:
        return True

    if fig_num and int(fig_num) > 10:
        return False
    if table_num and int(table_num) > 10:
        return False

    return True


def extract_label_from_block(block: dict) -> str:
    """Extract normalized label from caption block."""
    first_line = get_block_first_line(block)
    if not first_line:
        return ""

    # Try matching Extended Data Figure
    ext_fig_match = re.match(r'\s*(Extended\s+Data\s+Fig(?:ure)?\.?\s*\d+[a-zA-Z]?)', first_line, re.IGNORECASE)
    if ext_fig_match:
        return normalize_label(ext_fig_match.group(1))

    # Try matching Extended Data Table
    ext_table_match = re.match(r'\s*(Extended\s+Data\s+Table\s*\d+[a-zA-Z]?)', first_line, re.IGNORECASE)
    if ext_table_match:
        return normalize_label(ext_table_match.group(1))

    # Try matching Figure
    fig_match = re.match(r'\s*(Fig(?:ure)?\.?\s*\d+[a-zA-Z]?)', first_line, re.IGNORECASE)
    if fig_match:
        return normalize_label(fig_match.group(1))

    # Try matching Table
    table_match = re.match(r'\s*(Table\s*\d+[a-zA-Z]?)', first_line, re.IGNORECASE)
    if table_match:
        return normalize_label(table_match.group(1))

    return ""


def is_figure_label(label: str) -> bool:
    """Determine if label is Figure type."""
    return label.startswith("Fig.") or label.startswith("Extended_Data_Fig_")


def is_table_label(label: str) -> bool:
    """Determine if label is Table type."""
    return label.startswith("Table") or label.startswith("Extended_Data_Table_")


def find_figures_on_page(page) -> list:
    """
    Detect figure/table captions on page using structured text blocks.

    Returns:
        list of dict: [{"label": "Fig. 1", "type": "figure"|"table", "caption_block": block, "caption_bbox": (x0,y0,x1,y1)}]
    """
    text_dict = page.get_text("dict")
    blocks = text_dict["blocks"]
    results = []

    for block in blocks:
        if block["type"] != 0:  # Skip image blocks
            continue

        first_line = get_block_first_line(block)
        if not is_caption_start(first_line):
            continue

        label = extract_label_from_block(block)
        if not label:
            continue

        bbox = block["bbox"]  # (x0, y0, x1, y1)
        item_type = "figure" if is_figure_label(label) else "table"

        results.append({
            "label": label,
            "type": item_type,
            "caption_block": block,
            "caption_bbox": bbox,
        })

    return results


def sanitize_label(label: str) -> str:
    """Convert label to safe filename part, identifying with single underscore."""
    # "Fig. 1" → "Fig_1", "Table 2a" → "Table_2a"
    return re.sub(r'[^\w]+', '_', label).strip('_')


def extract_embedded_images(doc, output_dir: str, min_size: int = 100) -> dict:
    """Extract embedded bitmap images from PDF (fallback method)."""
    figures_dir = Path(output_dir) / "figures"
    tables_dir = Path(output_dir) / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "figure_count": 0,
        "table_count": 0,
        "skipped_small": 0,
        "figures": [],
        "tables": []
    }

    for page_num, page in enumerate(doc, 1):
        image_list = page.get_images(full=True)

        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                width = base_image["width"]
                height = base_image["height"]

                if width < min_size and height < min_size:
                    stats["skipped_small"] += 1
                    continue

                filename = f"page{page_num}_img{img_index + 1}.{image_ext}"
                filepath = figures_dir / filename

                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                stats["figure_count"] += 1
                stats["figures"].append({
                    "filename": filename,
                    "page": page_num,
                    "label": "",
                })

            except Exception as e:
                print(f"Warning: Failed to extract image on page {page_num}: {e}")
                continue

    return stats


def render_figures(doc, output_dir: str, dpi: int = 200) -> dict:
    """
    Detect and render pages containing figures/tables. Each figure/table renders the full page.

    Returns:
        dict: stats with figures and tables lists
    """
    figures_dir = Path(output_dir) / "figures"
    tables_dir = Path(output_dir) / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "figure_count": 0,
        "table_count": 0,
        "skipped_small": 0,
        "figures": [],
        "tables": [],
        "method": "page_rendering"
    }

    seen_labels = set()
    rendered_pages = {}  # page_num -> pixmap, avoid duplicate rendering of same page

    for page_num_0, page in enumerate(doc):
        page_num = page_num_0 + 1
        items = find_figures_on_page(page)
        if not items:
            continue

        for item in items:
            label = item["label"]
            if label in seen_labels:
                continue
            seen_labels.add(label)

            # Render full page (render only once per page)
            if page_num not in rendered_pages:
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                rendered_pages[page_num] = page.get_pixmap(matrix=mat)

            pix = rendered_pages[page_num]
            safe_label = sanitize_label(label)
            filename = f"{safe_label}_page{page_num}.png"

            if item["type"] == "figure":
                filepath = figures_dir / filename
                pix.save(str(filepath))
                stats["figure_count"] += 1
                stats["figures"].append({
                    "filename": filename,
                    "page": page_num,
                    "label": label,
                })
            else:
                filepath = tables_dir / filename
                pix.save(str(filepath))
                stats["table_count"] += 1
                stats["tables"].append({
                    "filename": filename,
                    "page": page_num,
                    "label": label,
                })

    return stats


def extract_figures_from_pdf(pdf_path: str, output_dir: str, min_size: int = 100) -> dict:
    """
    Main function to extract figures from PDF.

    Strategy:
    1. Detect captions using structured text blocks and intelligently crop.
    2. If no captions detected, try extracting embedded bitmap images.
    3. If still no results, render all pages.
    """
    doc = fitz.open(pdf_path)

    # Try intelligent cropping based on caption
    stats = render_figures(doc, output_dir)

    total_found = stats["figure_count"] + stats["table_count"]
    print(f"Found {stats['figure_count']} figures and {stats['table_count']} tables via caption detection")

    if total_found == 0:
        # Try extracting embedded images
        print("No figure/table captions found, trying to extract embedded images...")
        stats = extract_embedded_images(doc, output_dir, min_size)

        if stats["figure_count"] == 0 and stats["table_count"] == 0:
            print("No embedded images found either, rendering all pages...")
            figures_dir = Path(output_dir) / "figures"
            figures_dir.mkdir(parents=True, exist_ok=True)

            for page_num, page in enumerate(doc, 1):
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                filename = f"page{page_num}.png"
                filepath = figures_dir / filename
                pix.save(str(filepath))

                stats["figure_count"] += 1
                stats["figures"].append({
                    "filename": filename,
                    "page": page_num,
                    "label": f"Page {page_num}",
                })

            stats["method"] = "full_page_rendering"

    doc.close()
    return stats


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_figures.py <pdf_path> <output_dir>")
        print("")
        print("Arguments:")
        print("  pdf_path    Path to the PDF file")
        print("  output_dir  Directory for output figures")
        print("")
        print("Output:")
        print("  figures/         Directory containing extracted figures")
        print("  tables/          Directory containing extracted tables")
        print("")
        print("Example:")
        print("  python extract_figures.py paper.pdf output/")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]

    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    print(f"Extracting figures from: {pdf_path}")

    try:
        stats = extract_figures_from_pdf(pdf_path, output_dir)

        print(f"\nExtraction complete:")
        print(f"  Figures: {stats['figure_count']}")
        print(f"  Tables: {stats['table_count']}")
        if "method" in stats:
            print(f"  Method: {stats['method']}")
        print(f"  Output: {output_dir}")

    except Exception as e:
        print(f"Error extracting figures: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
