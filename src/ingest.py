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
from .ingestion.excel_parser import extract_sheets
from .ingestion.chunker import chunk_page
from .retrieval.vectordb import get_client, get_collection, upsert_chunks
from .utils.config import CHUNK_SIZE, CHUNK_OVERLAP


# How many chunks to embed/upsert in one go.
# Adjust if you hit timeouts or want more parallelism.
UPSERT_BATCH_SIZE = 64


def extract_content(file_path: Path) -> List[Dict]:
    """
    Route to appropriate parser based on file type.
    Returns list of page/sheet records compatible with chunker.
    """
    suffix = file_path.suffix.lower()

    if suffix == '.pdf':
        return extract_pages(file_path)
    elif suffix in ['.xlsx', '.xls']:
        return extract_sheets(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def ingest_reports(reports_dir: str, db_dir: str) -> None:
    """
    Parse all PDFs and Excel files, chunk them, and upsert into vector DB (Chroma).

    Features:
        - table-aware page/sheet extraction
        - heading-aware, paragraph-aware chunking
        - semantic overlap between chunks
        - stable chunk IDs (from vectordb)
        - deterministic re-ingestion
        - Ollama-based embeddings handled in vectordb.upsert_chunks

    Supported formats: .pdf, .xlsx, .xls
    """

    reports_path = Path(reports_dir)

    # Discover all supported files
    pdfs = sorted(list(reports_path.glob("**/*.pdf")))
    excels = sorted(list(reports_path.glob("**/*.xlsx"))) + sorted(list(reports_path.glob("**/*.xls")))
    all_files = pdfs + excels

    if not all_files:
        print(f"[WARN] No supported files found under: {reports_path}")
        return

    print(f"[INFO] Found {len(pdfs)} PDF(s) and {len(excels)} Excel file(s).")
    client = get_client(db_dir)
    collection = get_collection(client)

    total_chunks = 0

    for file_path in tqdm(all_files, desc="Parsing & chunking documents"):
        print(f"\n[INFO] Processing {file_path.name}")

        pages = extract_content(file_path)
        print(f"[DEBUG] Extracted {len(pages)} pages/sheets from {file_path.name}")

        file_chunks: List[Dict] = []

        for rec in pages:
            text = rec.get("text", "")
            if not text.strip():
                print(f"[WARN] Skipping empty page {rec.get('page')} in {file_path.name}")
                continue

            page_chunks = chunk_page(
                record=rec,
                chunk_size=CHUNK_SIZE,
                overlap_tokens=CHUNK_OVERLAP,
            )

            if not page_chunks:
                print(f"[WARN] No chunks produced for page {rec.get('page')} in {file_path.name}")

            file_chunks.extend(page_chunks)

        if not file_chunks:
            print(f"[WARN] No chunks to ingest for {file_path.name}")
            continue

        print(f"[INFO] → {len(file_chunks)} chunks produced for {file_path.name}")

        # Upsert into Chroma using OLLAMA embeddings (vectordb handles embed)
        # Do it in batches to avoid very large embedding requests.
        num_batches = (len(file_chunks) + UPSERT_BATCH_SIZE - 1) // UPSERT_BATCH_SIZE
        for b_idx in range(num_batches):
            start = b_idx * UPSERT_BATCH_SIZE
            end = start + UPSERT_BATCH_SIZE
            batch = file_chunks[start:end]

            print(
                f"[INFO] Upserting batch {b_idx + 1}/{num_batches} "
                f"for {file_path.name} ({len(batch)} chunks)..."
            )
            try:
                upsert_chunks(collection, batch)
            except Exception as e:
                # Log and continue with next batch/file; user can re-run if needed
                print(
                    f"[ERROR] Failed to upsert batch {b_idx + 1}/{num_batches} "
                    f"for {file_path.name}: {e}"
                )

        total_chunks += len(file_chunks)

    print(f"\n[INFO] Ingestion complete.")
    print(f"[INFO] Total chunks (attempted) stored: {total_chunks}")