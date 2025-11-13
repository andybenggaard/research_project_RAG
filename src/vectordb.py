# src/vectordb.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict
from .embedder_ollama import embed_texts  # ← add this import

def get_client(persist_dir: str):
    # Either PersistentClient (new) or Client(Settings(...)) both work
    try:
        return chromadb.PersistentClient(path=persist_dir)
    except AttributeError:
        return chromadb.Client(Settings(persist_directory=persist_dir, anonymized_telemetry=False))

def get_collection(client, name="reports"):
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

def upsert_chunks(collection, chunks):
    ids, docs, metas = [], [], []
    for i, ch in enumerate(chunks):
        ids.append(f"{ch['file_name']}::{ch['page']}::{i}")
        docs.append(ch["text"])
        metas.append({k: ch[k] for k in ch if k != "text"})

    # Let Chroma embed internally (MiniLM ONNX)
    collection.add(ids=ids, documents=docs, metadatas=metas)


def query(collection, q: str, n=8, where: dict | None = None):
    return collection.query(
        query_texts=[q],
        n_results=n,
        where=where,  # supports $eq, $in, $gt, $gte, $lt, $lte, $ne, $nin
        include=["documents","metadatas","distances"]
    )


