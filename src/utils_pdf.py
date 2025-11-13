from pathlib import Path
import fitz  # pymupdf
from typing import List, Dict

def extract_pages(pdf_path: Path) -> List[Dict]:
    doc = fitz.open(pdf_path)
    results = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        blocks = page.get_text("blocks")
        results.append({
            "page": i + 1,
            "text": text,
            "blocks": blocks,
            "file_name": pdf_path.name,
            "source_uri": str(pdf_path.resolve())
        })
    doc.close()
    return results
