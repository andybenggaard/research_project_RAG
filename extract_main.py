#!/usr/bin/env python3
"""
Standalone script: Extract ESRS-aligned facts from vector DB

Usage:
    python extract_main.py \
        --db ./data/vectors \
        --out ./data/cache/facts.json \
        --company "Maersk" \
        --year 2023
"""

import argparse
from pathlib import Path
from dotenv import load_dotenv

from src.extract_facts import extract_facts

DEFAULT_DB_DIR = "./data/vectors"
DEFAULT_CACHE_PATH = "./data/cache/facts.json"
DEFAULT_PROMPT = "prompts/extract_facts.md"
DEFAULT_QUERY = (
    "Extract Scope 1–3 emissions, units, base year, method, assurance level, "
    "2030 targets, carbon intensity, and ESRS E1-4 target details."
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

    args = parser.parse_args()

    # Ensure output folder exists
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    extract_facts(
        db_dir=args.db,
        query_text=args.query,
        prompt_path=args.prompt,
        out_path=args.out,
        company=args.company,
        year=args.year,
    )


if __name__ == "__main__":
    main()