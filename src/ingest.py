from pathlib import Path
from typing import List
from tqdm import tqdm
from .utils_pdf import extract_pages
from .chunking import chunk_page
from .vectordb import get_client, get_collection, upsert_chunks
from .config import CHUNK_SIZE, CHUNK_OVERLAP

def ingest_reports(reports_dir: str, db_dir: str):
    client = get_client(db_dir)
    col = get_collection(client)
    pdfs = sorted(list(Path(reports_dir).glob("**/*.pdf")))
    all_chunks = []
    for pdf in tqdm(pdfs, desc="Parsing PDFs"):
        pages = extract_pages(pdf)
        for rec in pages:
            chunks = chunk_page(rec, CHUNK_SIZE, CHUNK_OVERLAP)
            all_chunks.extend(chunks)
    upsert_chunks(col, all_chunks)
