# src/ingest.py

"""
Improved ingestion pipeline:
- Uses advanced utils_pdf.py (headings, tables, cleaned text)
- Uses improved chunking (section-aware, semantic overlap)
- Generates high-quality metadata for vectordb
- Uses Ollama embeddings via vectordb.upsert_chunks (batched)
"""

from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

from .ingestion.pdf_parser import extract_pages
from .ingestion.chunker import chunk_page
from .retrieval.vectordb import get_client, get_collection, upsert_chunks
from .utils.config import CHUNK_SIZE, CHUNK_OVERLAP


# How many chunks to embed/upsert in one go.
# Adjust if you hit timeouts or want more parallelism.
UPSERT_BATCH_SIZE = 64


def ingest_reports(reports_dir: str, db_dir: str) -> None:
    """
    Parse all PDFs, chunk them, and upsert into vector DB (Chroma).

    Features:
        - table-aware page extraction
        - heading-aware, paragraph-aware chunking
        - semantic overlap between chunks
        - stable chunk IDs (from vectordb)
        - deterministic re-ingestion
        - Ollama-based embeddings handled in vectordb.upsert_chunks
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
            text = rec.get("text", "")
            if not text.strip():
                print(f"[WARN] Skipping empty page {rec.get('page')} in {pdf.name}")
                continue

            page_chunks = chunk_page(
                record=rec,
                chunk_size=CHUNK_SIZE,
                overlap_tokens=CHUNK_OVERLAP,
            )

            if not page_chunks:
                print(f"[WARN] No chunks produced for page {rec.get('page')} in {pdf.name}")

            pdf_chunks.extend(page_chunks)

        if not pdf_chunks:
            print(f"[WARN] No chunks to ingest for {pdf.name}")
            continue

        print(f"[INFO] → {len(pdf_chunks)} chunks produced for {pdf.name}")

        # Upsert into Chroma using OLLAMA embeddings (vectordb handles embed)
        # Do it in batches to avoid very large embedding requests.
        num_batches = (len(pdf_chunks) + UPSERT_BATCH_SIZE - 1) // UPSERT_BATCH_SIZE
        for b_idx in range(num_batches):
            start = b_idx * UPSERT_BATCH_SIZE
            end = start + UPSERT_BATCH_SIZE
            batch = pdf_chunks[start:end]

            print(
                f"[INFO] Upserting batch {b_idx + 1}/{num_batches} "
                f"for {pdf.name} ({len(batch)} chunks)..."
            )
            try:
                upsert_chunks(collection, batch)
            except Exception as e:
                # Log and continue with next batch/file; user can re-run if needed
                print(
                    f"[ERROR] Failed to upsert batch {b_idx + 1}/{num_batches} "
                    f"for {pdf.name}: {e}"
                )

        total_chunks += len(pdf_chunks)

    print(f"\n[INFO] Ingestion complete.")
    print(f"[INFO] Total chunks (attempted) stored: {total_chunks}")