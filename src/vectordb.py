# src/vectordb.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict


def get_client(persist_dir: str):
    """Create a persistent Chroma client."""
    try:
        return chromadb.PersistentClient(path=persist_dir)
    except AttributeError:
        return chromadb.Client(
            Settings(
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            )
        )


def get_collection(client, name: str = "reports"):
    """Create or get a collection using cosine similarity."""
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(collection, chunks: List[Dict]):
    """
    Upsert chunk documents into Chroma and let Chroma handle embeddings
    with its built-in MiniLM model.
    """
    ids, docs, metas = [], [], []
    for i, ch in enumerate(chunks):
        text = ch["text"]
        if not text.strip():
            # skip empty chunks
            print(f"[WARN] Skipping empty chunk for file {ch['file_name']} page {ch['page']}")
            continue

        ids.append(f"{ch['file_name']}::{ch['page']}::{i}")
        docs.append(text)
        metas.append({k: v for k, v in ch.items() if k != "text"})

    if not docs:
        print("[WARN] No non-empty chunks to upsert.")
        return

    collection.add(
        ids=ids,
        documents=docs,
        metadatas=metas,
    )


def query(collection, q: str, n: int = 8, where: dict | None = None):
    """Query the vector DB using a text query and optional filters."""
    return collection.query(
        query_texts=[q],
        n_results=n,
        where=where,
        include=["documents", "metadatas", "distances"],
    )