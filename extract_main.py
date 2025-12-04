#!/usr/bin/env python3
"""
Standalone script: Extract ESRS-aligned facts from vector DB

Usage (default settings):
    python extract_main.py \
        --db ./data/vectors \
        --out ./data/cache/facts.json \
        --company "Maersk" \
        --year 2023

With custom retrieval settings:
    python extract_main.py \
        --db ./data/vectors \
        --out ./data/cache/facts.json \
        --company "Maersk" \
        --year 2023 \
        --pool-size 120 \
        --top-k 60
"""

import argparse
from pathlib import Path
from dotenv import load_dotenv

from src.extraction.single_step import extract_facts_single_step

DEFAULT_DB_DIR = "./data/vectors"
DEFAULT_CACHE_PATH = "./data/cache/factsV2.json"
DEFAULT_PROMPT = "prompts/extract_factsV2.md"
DEFAULT_QUERY = (
    "Scope 1 2 3 emissions, breakdowns, CO2e values, base year, methodology, data quality, emission factors, boundaries, consolidation approach, ESRS E1 targets, 2030 goals, carbon intensity."
)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Extract structured facts from vector DB")
    parser.add_argument("--db", default=DEFAULT_DB_DIR)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--out", default=DEFAULT_CACHE_PATH)
    parser.add_argument("--company", required=True)
    parser.add_argument("--year", type=int, required=True)

    # NEW: hybrid retrieval tuning
    parser.add_argument(
        "--pool-size",
        type=int,
        default=100,
        help="How many chunks to pull from Chroma before BM25 re-ranking (default: 100)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=40,
        help="How many chunks to keep after BM25 re-ranking (default: 40)",
    )

    args = parser.parse_args()

    # Ensure output folder exists
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    extract_facts_single_step(
        db_dir=args.db,
        query_text=args.query,
        prompt_path=args.prompt,
        out_path=args.out,
        company=args.company,
        year=args.year,
        pool_size=args.pool_size,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
