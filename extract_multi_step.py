#!/usr/bin/env python3
"""
Multi-step RAG extraction script.

This implements a 3-stage pipeline:
1. Extract regulation requirements from ISO/GHG Protocol/ESRS docs
2. Extract company data with regulation context
3. Perform gap analysis

Usage:
    python extract_multi_step.py \
        --db ./data/vectors \
        --out ./data/cache/compliance_analysis.json \
        --company "Maersk" \
        --year 2023
"""

import argparse
from pathlib import Path
from dotenv import load_dotenv

from src.extraction.multi_step import extract_facts_multi_step

DEFAULT_DB_DIR = "./data/vectors"
DEFAULT_OUT_PATH = "./data/cache/compliance_analysis.json"
DEFAULT_REGULATION_PROMPT = "prompts/extract_regulations.md"
DEFAULT_COMPANY_PROMPT = "prompts/extract_factsV2.md"


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Multi-step RAG extraction with compliance analysis"
    )
    parser.add_argument("--db", default=DEFAULT_DB_DIR, help="Vector database directory")
    parser.add_argument("--out", default=DEFAULT_OUT_PATH, help="Output JSON path")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--year", type=int, required=True, help="Reporting year")

    parser.add_argument(
        "--regulation-prompt",
        default=DEFAULT_REGULATION_PROMPT,
        help="Path to regulation extraction prompt"
    )
    parser.add_argument(
        "--company-prompt",
        default=DEFAULT_COMPANY_PROMPT,
        help="Path to company data extraction prompt"
    )

    parser.add_argument(
        "--pool-size",
        type=int,
        default=100,
        help="Candidates from vector search (default: 100)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=40,
        help="Keep after BM25 reranking (default: 40)"
    )

    args = parser.parse_args()

    # Ensure output folder exists
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    extract_facts_multi_step(
        db_dir=args.db,
        company=args.company,
        year=args.year,
        regulation_prompt_path=args.regulation_prompt,
        company_prompt_path=args.company_prompt,
        out_path=args.out,
        pool_size=args.pool_size,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
