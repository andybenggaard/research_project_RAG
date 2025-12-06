"""
Ingestion module for PDF/Excel parsing, chunking, and embedding.
"""

from .pdf_parser import extract_pages
from .excel_parser import extract_sheets
from .chunker import chunk_page
from .embedder import embed_texts

__all__ = ["extract_pages", "extract_sheets", "chunk_page", "embed_texts"]
