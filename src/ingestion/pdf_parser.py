# src/utils_pdf.py

"""
Advanced PDF extraction optimized for ESG / Climate reports.
- Detects headings using font size / bold weight
- Extracts tables separately
- Cleans footers / page numbers
- Normalizes multi-column layout into natural reading order
- Returns structured blocks for chunker
"""

from pathlib import Path
import fitz  # pymupdf
from typing import List, Dict, Any


# ---------------------------------------------------------
# Utility: classify text block type
# ---------------------------------------------------------
def classify_block(block: Dict[str, Any]) -> str:
    """
    Classifies a block based on structure and font properties.
    """
    if block.get("table", False):
        return "table"

    # Heading heuristic: larger font OR bold
    max_size = 0
    bold_found = False
    for span in block.get("spans", []):
        size = span.get("size", 0)
        flags = span.get("flags", 0)
        max_size = max(max_size, size)
        if flags & 2:  # 2 = bold
            bold_found = True

    if max_size >= 12 or bold_found:
        return "heading"

    return "text"


# ---------------------------------------------------------
# Utility: extract table as MarkDown-ish text
# ---------------------------------------------------------
def extract_table(page, b):
    """
    Extracts simple tables via PyMuPDF.  
    Returns a text version (pipe tables).
    """
    try:
        table = page.find_tables()
        out = []
        for t in table:
            if t.bbox == b["bbox"]:
                for row in t.extract():
                    out.append(" | ".join(cell.strip() for cell in row))
                return "\n".join(out)
    except Exception:
        pass
    return ""


# ---------------------------------------------------------
# Remove footer / page numbers
# ---------------------------------------------------------
def remove_footer_and_pagenum(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    for ln in lines:
        # Remove isolated page numbers or "Page 12"
        if ln.strip().isdigit():
            continue
        if ln.lower().startswith("page ") and ln[5:].strip().isdigit():
            continue
        cleaned.append(ln)
    return "\n".join(cleaned).strip()


# ---------------------------------------------------------
# Main page extractor
# ---------------------------------------------------------
def extract_pages(pdf_path: Path) -> List[Dict]:
    """
    Extracts structured information from each page:
        - clean text (footer removed)
        - table text
        - block reading order
        - font-size aware headings
    """
    doc = fitz.open(pdf_path)
    pages_out = []

    for page_index, page in enumerate(doc):
        blocks_raw = page.get_text("dict")["blocks"]
        blocks_processed = []

        for b in blocks_raw:
            if "lines" not in b:
                continue

            # Extract spans with font info
            spans = []
            txt = []
            for l in b["lines"]:
                for s in l["spans"]:
                    spans.append(s)
                    txt.append(s.get("text", ""))

            text = "\n".join(txt).strip()
            if not text:
                continue

            # Clean text (remove page numbers)
            clean_text = remove_footer_and_pagenum(text)

            # Table extraction attempt
            is_table = False
            table_text = ""
            try:
                if b.get("type", 0) == 5:  # PyMuPDF table type
                    is_table = True
                    table_text = extract_table(page, b)
            except Exception:
                pass

            block_type = classify_block({
                "spans": spans,
                "bbox": b.get("bbox")
            })

            blocks_processed.append({
                "text": clean_text,
                "raw_text": text,
                "block_type": "table" if is_table else block_type,
                "bbox": b.get("bbox"),
                "font_sizes": [s.get("size", 0) for s in spans],
                "spans": spans,
                "table_text": table_text,
            })

        # Combine block texts in reading order
        full_text = []
        for b in blocks_processed:
            if b["block_type"] == "table" and b["table_text"]:
                full_text.append(b["table_text"])
            else:
                full_text.append(b["text"])

        pages_out.append({
            "page": page_index + 1,
            "text": "\n\n".join(t for t in full_text if t.strip()),
            "blocks": blocks_processed,
            "file_name": pdf_path.name,
            "source_uri": str(pdf_path.resolve())
        })

    doc.close()
    return pages_out