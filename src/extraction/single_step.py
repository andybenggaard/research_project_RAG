# src/extraction/single_step.py

"""
Single-step fact extraction pipeline (original approach).
Extracts facts directly from all documents in one pass.
"""

import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..retrieval import get_client, get_collection, hybrid_retrieve
from .llm_client import generate_json


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


# --------------------------------------------
# Main extraction
# --------------------------------------------
def extract_facts_single_step(
    db_dir: str,
    query_text: str,
    prompt_path: str,
    out_path: str,
    company: str,
    year: int,
    pool_size: int = 100,
    top_k: int = 40,
    where: Optional[dict] = None,
):
    """
    Single-step fact extraction pipeline with hybrid retrieval.

    Steps:
      1) Vector search across documents (pool_size candidates)
      2) BM25 re-ranking (top_k)
      3) Per-chunk JSON extraction via LLM
      4) Merge & dedupe

    Args:
        db_dir: Path to vector database
        query_text: Search query
        prompt_path: Path to extraction prompt
        out_path: Output JSON path
        company: Company name
        year: Reporting year
        pool_size: Number of candidates from vector search
        top_k: Number to keep after BM25 reranking
        where: Optional metadata filter
    """
    client = get_client(db_dir)
    col = get_collection(client)

    # Load prompt
    with open(prompt_path, "r") as f:
        system_prompt = f.read().strip()

    # Hybrid retrieval
    docs, metas = hybrid_retrieve(col, query_text, pool_size, top_k, where)

    if not docs:
        print("[WARN] No retrieval hits — saving empty facts.")
        json.dump(
            {"company": company, "year": year, "facts": [], "raw": "no_hits"},
            open(out_path, "w"),
            indent=2
        )
        return

    # Process per chunk
    all_facts: List[Dict[str, Any]] = []
    partial_path = out_path + ".partial.jsonl"

    # Clear partial file
    Path(partial_path).unlink(missing_ok=True)

    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        page = meta.get("page")
        section_path = meta.get("section_path", "")
        file_name = meta.get("file_name", "unknown")

        # Limit chunk length (LLM friendly)
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

            # Incremental preview writing (JSON Lines)
            with open(partial_path, "a") as tmp:
                tmp.write(json.dumps(f) + "\n")

    # Merge & deduplicate
    merged_facts = _merge_facts(all_facts)

    print(f"[INFO] Total extracted facts (raw): {len(all_facts)}")
    print(f"[INFO] After merge/dedupe: {len(merged_facts)}")

    # Save output
    out = {
        "company": company,
        "year": year,
        "facts": merged_facts,
    }

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"[✓] Saved structured facts → {out_path}")
