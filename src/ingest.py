# src/ingest.py

"""
Improved ingestion pipeline:
- Uses advanced utils_pdf.py (headings, tables, cleaned text)
- Uses improved chunking (section-aware, semantic overlap)
- Generates high-quality metadata for vectordb
"""

from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

from .utils_pdf import extract_pages
from .chunking import chunk_page
from .vectordb import get_client, get_collection, upsert_chunks
from .config import CHUNK_SIZE, CHUNK_OVERLAP


def ingest_reports(reports_dir: str, db_dir: str):
    """
    Parse all PDFs, chunk them, and upsert into vector DB (Chroma).

    Now supports:
        - table-aware page extraction
        - heading-aware chunking
        - stable chunk IDs (from vectordb)
        - deterministic re-ingestion
    """

    reports_path = Path(reports_dir)
    pdfs = sorted(list(reports_path.glob("**/*.pdf")))

    if not pdfs:
        print(f"[WARN] No PDFs found under: {reports_path}")
        return

    print(f"[INFO] Found {len(pdfs)} PDF reports.")
    client = get_client(db_dir)
    collection = get_collection(client)

    total_chunks = 0

    for pdf in tqdm(pdfs, desc="Parsing & chunking PDFs"):
        print(f"\n[INFO] Processing {pdf.name}")

        pages = extract_pages(pdf)
        print(f"[DEBUG] Extracted {len(pages)} pages from {pdf.name}")

        pdf_chunks: List[Dict] = []

        for rec in pages:
            if not rec["text"].strip():
                print(f"[WARN] Skipping empty page {rec['page']} in {pdf.name}")
                continue

            page_chunks = chunk_page(
                record=rec,
                chunk_size=CHUNK_SIZE,
                overlap_tokens=CHUNK_OVERLAP
            )

            if not page_chunks:
                print(f"[WARN] No chunks produced for page {rec['page']} in {pdf.name}")

            pdf_chunks.extend(page_chunks)

        print(f"[INFO] → {len(pdf_chunks)} chunks produced for {pdf.name}")

        # Upsert into Chroma using OLLAMA embeddings (vectordb handles embed)
        upsert_chunks(collection, pdf_chunks)

        total_chunks += len(pdf_chunks)

    print(f"\n[INFO] Ingestion complete.")
    print(f"[INFO] Total chunks stored: {total_chunks}")
