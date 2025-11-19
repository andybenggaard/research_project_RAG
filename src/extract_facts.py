# src/extract_facts.py

"""
Production-grade fact extraction pipeline using:
- improved vectordb retrieval
- hybrid retrieval: vector search + BM25 re-ranking
- per-chunk extraction with JSON guarantee
- deduplication + ESRS-aligned fact IDs
- stable merged output
"""

import json
import hashlib
from typing import List, Dict, Any

from .vectordb import get_client, get_collection, query
from .llm_ollama import generate_json

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    print("[WARN] rank-bm25 not installed. BM25 re-ranking disabled.")


# --------------------------------------------
# Helpers
# --------------------------------------------
def _fact_id(text: str, page: int) -> str:
    """Deterministic ID."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return f"fact_{page}_{h}"


def _merge_facts(all_facts: List[Dict]) -> List[Dict]:
    """
    Deduplicate facts by (page, text).
    Keeps highest confidence if duplicates appear.
    """
    merged: Dict[tuple, Dict] = {}
    priority = {"low": 1, "medium": 2, "high": 3}

    for f in all_facts:
        key = (f.get("page"), f.get("text", ""))
        if not key[1]:
            continue
        if key not in merged:
            merged[key] = f
        else:
            if priority.get(f.get("confidence", "medium"), 2) > priority.get(merged[key].get("confidence", "medium"), 2):
                merged[key] = f
    return list(merged.values())


def _bm25_rerank(docs: List[str], metas: List[Dict], query_text: str, top_n: int) -> tuple[list[str], list[Dict]]:
    """
    Re-rank a small set of documents using BM25.
    Returns new (docs, metas) lists sorted by lexical relevance to query_text.
    """
    if not HAS_BM25:
        print("[INFO] BM25 not available; skipping re-ranking.")
        return docs, metas

    # simple whitespace tokenization is good enough for ranking
    tokenized_corpus = [d.lower().split() for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query_text.lower().split()

    scores = bm25.get_scores(tokenized_query)
    idx = list(range(len(docs)))
    idx_sorted = sorted(idx, key=lambda i: scores[i], reverse=True)[:top_n]

    reranked_docs = [docs[i] for i in idx_sorted]
    reranked_metas = [metas[i] for i in idx_sorted]

    return reranked_docs, reranked_metas


# --------------------------------------------
# Main extraction
# --------------------------------------------
def extract_facts(
    db_dir: str,
    query_text: str,
    prompt_path: str,
    out_path: str,
    company: str,
    year: int,
    pool_size: int = 100,   # how many chunks to pull from Chroma
    top_k: int = 40,        # how many chunks to keep after BM25 re-rank
):
    """
    Multi-chunk robust extraction pipeline with hybrid retrieval.
    Steps:
      1) Vector search across ALL PDFs (pool_size candidates)
      2) BM25 re-ranking (top_k)
      3) Per-chunk JSON extraction via LLM
      4) Merge & dedupe
    """
    client = get_client(db_dir)
    col = get_collection(client)

    # ------------------------------------------------------------
    # LOAD PROMPT
    # ------------------------------------------------------------
    with open(prompt_path, "r") as f:
        system_prompt = f.read().strip()

    # ------------------------------------------------------------
    # RETRIEVE CANDIDATE CHUNKS (NO FILE FILTER)
    # ------------------------------------------------------------
    hits = query(col, query_text, n=pool_size, where=None)

    if (
        not hits or
        not hits.get("documents") or
        not hits["documents"] or
        not hits["documents"][0]
    ):
        print("[WARN] No retrieval hits — saving empty facts.")
        json.dump(
            {"company": company, "year": year, "facts": [], "raw": "no_hits"},
            open(out_path, "w"),
            indent=2
        )
        return

    docs = hits["documents"][0]
    metas = hits["metadatas"][0]

    print(f"[INFO] Retrieved {len(docs)} chunks from vector DB (pre-BM25).")

    # ------------------------------------------------------------
    # BM25 RE-RANKING (SECOND STAGE)
    # ------------------------------------------------------------
    if top_k and top_k < len(docs):
        docs, metas = _bm25_rerank(docs, metas, query_text, top_n=top_k)
        print(f"[INFO] After BM25 re-ranking: {len(docs)} chunks retained (top_k={top_k}).")
    else:
        print("[INFO] Skipping BM25 re-rank (top_k >= pool_size or BM25 unavailable).")

    # ------------------------------------------------------------
    # PROCESS PER CHUNK
    # ------------------------------------------------------------
    all_facts: List[Dict[str, Any]] = []

    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        page = meta.get("page")
        section_path = meta.get("section_path", "")
        file_name = meta.get("file_name", "unknown")

        # limit chunk length (LLM friendly)
        snippet = doc[:1800]

        user_prompt = f"""
Company: {company}
Year: {year}

The following is EVIDENCE from the report:
[page: {page}, file: {file_name}, section: {section_path}]

EVIDENCE:
\"\"\"
{snippet}
\"\"\"

Extract ONLY the facts according to the extraction rules.
Return ONLY valid JSON.
"""

        print(f"[DEBUG] Extracting from chunk {i}/{len(docs)} page={page} file={file_name}")

        try:
            chunk_result = generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_retries=3,
                temperature=0.1,
            )
        except Exception as e:
            print(f"[ERROR] JSON extraction failed for chunk {i}: {e}")
            continue

        # Validate structure
        chunk_facts = chunk_result.get("facts", [])
        if not isinstance(chunk_facts, list):
            chunk_facts = []

        # Normalize & attach metadata
        for f in chunk_facts:
            f.setdefault("page", page)
            f.setdefault("id", _fact_id(f.get("text", ""), page or 0))
            f.setdefault("file_name", file_name)
            f.setdefault("section_path", section_path)
            all_facts.append(f)
        # --- NEW: incremental preview writing (JSON Lines) ---
        with open(out_path + ".partial.jsonl", "a") as tmp:
            tmp.write(json.dumps(f) + "\n")

    # ------------------------------------------------------------
    # MERGE & DEDUPLICATE
    # ------------------------------------------------------------
    merged_facts = _merge_facts(all_facts)

    print(f"[INFO] Total extracted facts (raw): {len(all_facts)}")
    print(f"[INFO] After merge/dedupe: {len(merged_facts)}")

    # ------------------------------------------------------------
    # SAVE OUTPUT
    # ------------------------------------------------------------
    out = {
        "company": company,
        "year": year,
        "facts": merged_facts,
    }

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"[✓] Saved structured facts → {out_path}")
