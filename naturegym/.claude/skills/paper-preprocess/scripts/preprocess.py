#!/usr/bin/env python3
"""
Main paper preprocessing script.
Integrates text extraction (HTML), figure extraction (PDF), and link extraction (HTML).

Input is a directory containing *.pdf and *.html files.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

# Import submodules
from extract_text import extract_text_from_html
from extract_figures import extract_figures_from_pdf
from extract_links import extract_links


def preprocess_paper(input_dir: str, output_dir: str) -> dict:
    """
    Preprocess paper.

    Args:
        input_dir: Directory containing *.pdf and *.html files
        output_dir: Output directory

    Returns:
        dict: Preprocessing result metadata
    """
    input_dir = Path(input_dir)
    paper_id = input_dir.resolve().name
    output_base = Path(output_dir)

    # Auto-discover PDF and HTML files
    pdf_files = sorted(input_dir.glob("*.pdf"))
    html_files = sorted(input_dir.glob("*.html"))

    if not html_files:
        print(f"Error: No HTML file found in {input_dir}")
        sys.exit(1)
    if not pdf_files:
        print(f"Error: No PDF file found in {input_dir}")
        sys.exit(1)

    html_path = html_files[0]
    pdf_path = pdf_files[0]

    # Create output directory
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"=" * 50)
    print(f"Preprocessing: {paper_id}")
    print(f"  HTML: {html_path.name}")
    print(f"  PDF:  {pdf_path.name}")
    print(f"  Output: {output_base}")
    print(f"=" * 50)

    metadata = {
        "paper_id": paper_id,
        "source_html": str(html_path.absolute()),
        "source_pdf": str(pdf_path.absolute()),
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_tool": f"PyMuPDF {fitz.version[0]} + BeautifulSoup",
    }

    # Get PDF page count
    doc = fitz.open(str(pdf_path))
    metadata["page_count"] = len(doc)
    doc.close()

    # Step 1: Extract text (HTML)
    print(f"\n[1/3] Extracting text from HTML...")
    text_output = output_base / "text.md"
    try:
        text_stats = extract_text_from_html(str(html_path), str(text_output))
        metadata["text_stats"] = text_stats
        print(f"  Text extracted: {text_stats['word_count']} words")
    except Exception as e:
        print(f"  Text extraction failed: {e}")
        metadata["text_stats"] = {"error": str(e)}

    # Step 2: Extract figures (PDF)
    print(f"\n[2/3] Extracting figures from PDF...")
    try:
        figure_stats = extract_figures_from_pdf(str(pdf_path), str(output_base))
        metadata["figure_count"] = figure_stats["figure_count"]
        metadata["table_count"] = figure_stats["table_count"]
        metadata["figure_stats"] = figure_stats
        print(f"  Figures extracted: {figure_stats['figure_count']} figures, {figure_stats['table_count']} tables")
    except Exception as e:
        print(f"  Figure extraction failed: {e}")
        metadata["figure_count"] = 0
        metadata["table_count"] = 0
        metadata["figure_stats"] = {"error": str(e)}

    # Step 3: Extract links (HTML)
    print(f"\n[3/3] Extracting links from HTML...")
    links_output = output_base / "links.json"
    try:
        link_result = extract_links(str(html_path))

        # Add paper_id to link result
        link_result["paper_id"] = paper_id
        link_result["extraction_timestamp"] = metadata["extraction_timestamp"]

        with open(links_output, 'w', encoding='utf-8') as f:
            json.dump(link_result, f, indent=2, ensure_ascii=False)

        links_list = link_result.get("links", [])
        link_count = len(links_list)
        metadata["link_count"] = link_count
        metadata["link_stats"] = {
            "total": link_count,
            "data_availability": len(link_result.get("data_availability", [])),
            "code_availability": len(link_result.get("code_availability", [])),
        }
        print(f"  Links extracted: {link_count} links")
    except Exception as e:
        print(f"  Link extraction failed: {e}")
        metadata["link_count"] = 0
        metadata["link_stats"] = {"error": str(e)}

    print(f"\n" + "=" * 50)
    print(f"Preprocessing complete!")
    print(f"=" * 50)
    print(f"Output directory: {output_base}")
    print(f"  - text.md: {metadata.get('text_stats', {}).get('word_count', 'N/A')} words")
    print(f"  - figures/: {metadata.get('figure_count', 0)} files")
    print(f"  - tables/: {metadata.get('table_count', 0)} files")
    print(f"  - links.json: {metadata.get('link_count', 0)} links")

    return metadata


def main():
    if len(sys.argv) < 3:
        print("Usage: python preprocess.py <input_dir> <output_dir>")
        print("")
        print("Arguments:")
        print("  input_dir   Directory containing *.pdf and *.html files")
        print("              (folder name is used as paper_id)")
        print("  output_dir  Base directory for output")
        print("")
        print("Example:")
        print("  python preprocess.py ./s42256-019-0037-0/ ./s42256-019-0037-0/preprocessed")
        print("")
        print("Output structure:")
        print("  {output_dir}/")
        print("    text.md")
        print("    figures/")
        print("    tables/")
        print("    links.json")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not Path(input_dir).is_dir():
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)

    try:
        metadata = preprocess_paper(input_dir, output_dir)

        # Output metadata in JSON format
        print(f"\n__METADATA__:{json.dumps(metadata)}")

    except Exception as e:
        print(f"Error during preprocessing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
