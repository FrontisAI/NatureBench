---
name: paper-preprocess
description: Preprocessing CNS papers (PDF + HTML) to extract text, figures, and links. Outputs structured data for use by the paper-filter skill.
context: fork
agent: general-purpose
allowed-tools: Read, Bash(python *)
---

# Paper Preprocess Skill

Preprocess CNS papers using HTML (text/links) and PDF (figures) to extract structured data.

## Input Requirements

Before invoking this skill, provide:
1. **Input Directory**: A directory containing both `*.pdf` and `*.html` files for the same paper (Nature/Springer structured HTML). The folder name is used as `paper_id`.
2. **Output Directory**: The base directory to store preprocessing results

## Workflow

### Step 1: Extract Text (from HTML)

Use `scripts/extract_text.py` to extract full text from the HTML:
- Preserve document structure (headings, paragraphs, bold/italic)
- Preserve LaTeX formulas
- Remove citation reference numbers
- Skip non-content sections (References, Recommendations, Author information, etc.)
- Output in Markdown format

### Step 2: Extract Figures (from PDF)

Use `scripts/extract_figures.py` to extract figures from the PDF:
- Detect figure/table captions via structured text blocks
- Render full pages containing detected figures/tables
- Fall back to embedded image extraction if no captions found, then to full-page rendering if still empty

### Step 3: Extract Links (from HTML)

Use `scripts/extract_links.py` to extract links from the HTML:
- Extract hyperlinks from article body sections
- Classify into data_availability / code_availability / supplementary_information / other by section
- Identify common link types (GitHub, Zenodo, CodeOcean, etc.)
- Filter out internal anchors, citation references, and non-content sections

## Usage

```bash
cd skills/paper-preprocess/scripts

python3 preprocess.py <input_dir> <output_dir>

# Example:
python3 preprocess.py ./s42256-019-0037-0/ ./s42256-019-0037-0/preprocessed
```

## Output Structure

```
{output_dir}/
  text.md                 # Full paper text (Markdown format)
  figures/                # Figures directory
    Fig_1_page2.png
    Fig_2_page3.png
    ...
  tables/                 # Tables directory
    Table_1_page3.png
    ...
  links.json              # Extracted links with section classification
```

### links.json Format

```json
{
  "links": [
    {
      "url": "https://github.com/example/repo",
      "type": "github | zenodo | codeocean | huggingface | google_drive | dropbox | other",
      "context": "Surrounding paragraph text (up to 400 chars)",
      "section": "data_availability | code_availability | supplementary_information | other"
    }
  ],
  "data_availability": ["https://..."],
  "code_availability": ["https://github.com/..."],
  "paper_id": "s42256-019-0037-0",
  "extraction_timestamp": "2026-01-01T00:00:00"
}
```

## Dependencies

Install Python dependencies before running:
```bash
pip install pymupdf beautifulsoup4
```
