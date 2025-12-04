"""
Ingestion module for PDF parsing, chunking, and embedding.
"""

from .pdf_parser import extract_pages
from .chunker import chunk_page
from .embedder import embed_texts

__all__ = ["extract_pages", "chunk_page", "embed_texts"]
