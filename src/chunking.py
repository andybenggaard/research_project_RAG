# src/chunking.py

"""
Improved ESG-grade chunking for PDF ingestion.
- Heading detection (regex)
- Section path generation
- Paragraph-aware chunking
- Semantic overlap
- Stable token estimation
"""

from typing import List, Dict
import re


# ----------------------------------------
# Token estimation (improved heuristic)
# ----------------------------------------
def count_tokens(text: str) -> int:
    """
    Approximate token count using 1 token ≈ 4 chars for ESG text.
    """
    return max(1, int(len(text) / 4))


# ----------------------------------------
# Heading detection
# ----------------------------------------
HEADING_RE = re.compile(
    r"^(\d+(\.\d+)*)([\.\s]+)([A-Z][^\n]{2,100})$"
)

def detect_heading(text: str) -> str | None:
    """
    Detect section headings like:
        '2 Climate Strategy'
        '2.1 2030 targets'
        '3.4.2 Scope 3 methodology'
    """
    lines = text.strip().split("\n")
    if not lines:
        return None

    first = lines[0].strip()
    m = HEADING_RE.match(first)
    if m:
        num = m.group(1)
        title = m.group(4).strip()
        return f"{num} {title}"

    return None


# ----------------------------------------
# Build hierarchical section path
# ----------------------------------------
def update_section_path(section_path: List[str], new_heading: str) -> List[str]:
    """
    Given a heading like "2.1 Energy efficiency", maintain a section tree:
        ["2 Climate Strategy", "2.1 Energy efficiency"]
    """
    num = new_heading.split(" ")[0]        # "2.1"
    depth = num.count(".") + 1             # e.g. "2.1.3" → depth = 3

    # truncate existing path at this depth - 1
    new_path = section_path[:depth - 1]
    new_path.append(new_heading)
    return new_path


# ----------------------------------------
# Split page into structural paragraphs
# ----------------------------------------
def split_paragraphs(text: str) -> List[str]:
    # Split on blank lines but keep tight paragraphs
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paras


# ----------------------------------------
# Main chunker
# ----------------------------------------
def chunk_page(record: Dict, chunk_size: int, overlap_tokens: int) -> List[Dict]:
    """
    ESG-optimized chunking:
    - paragraph-aware
    - heading detection and section_path tracking
    - semantic overlap by paragraph, not raw characters
    """
    text = record["text"]
    file_name = record["file_name"]
    page = record["page"]
    source_uri = record["source_uri"]

    paras = split_paragraphs(text)
    chunks = []

    buf: List[str] = []
    buf_tokens = 0
    section_path: List[str] = []

    for para in paras:
        # 1. If the paragraph is a heading, update section path
        heading = detect_heading(para)
        if heading:
            section_path = update_section_path(section_path, heading)

        ptoks = count_tokens(para)

        # 2. If adding this paragraph exceeds chunk size, flush the chunk
        if buf and (buf_tokens + ptoks > chunk_size):
            chunk_text = "\n\n".join(buf)
            chunks.append({
                "text": chunk_text,
                "page": page,
                "file_name": file_name,
                "source_uri": source_uri,
                "section_path": " > ".join(section_path),
            })

            # ----------------------------------------
            # 3. Semantic overlap: reuse the LAST paragraphs up to overlap_tokens
            # ----------------------------------------
            overlap_buf = []
            overlap_sum = 0

            # start from end, accumulate until overlap_tokens reached
            for prev_para in reversed(buf):
                t = count_tokens(prev_para)
                if overlap_sum + t > overlap_tokens:
                    break
                overlap_buf.insert(0, prev_para)
                overlap_sum += t

            # new buffer contains overlap + new paragraph
            buf = overlap_buf + [para]
            buf_tokens = overlap_sum + ptoks

        else:
            # Just add paragraph to buffer
            buf.append(para)
            buf_tokens += ptoks

    # Flush remaining
    if buf:
        chunk_text = "\n\n".join(buf)
        chunks.append({
            "text": chunk_text,
            "page": page,
            "file_name": file_name,
            "source_uri": source_uri,
            "section_path": " > ".join(section_path),
        })

    return chunks