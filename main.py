#!/usr/bin/env python3
"""
End-to-end pipeline:

1. Read config (.env, CLI args)
2. Ingest all PDFs under ./reports into ./data/vectors
3. Run fact extraction into ./data/cache/facts.json

This can be called as a script:
    python main.py --company "IPCC AR6 WGIII" --year 2022 --query "..."

Or imported:
    from main import run_pipeline
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.ingest import ingest_reports
from src.extract_facts import extract_facts


DEFAULT_REPORTS_DIR = "./reports"
DEFAULT_DB_DIR = "./data/vectors"
DEFAULT_CACHE_DIR = "./data/cache"
DEFAULT_PROMPT_PATH = "prompts/extract_facts.md"
DEFAULT_OUT_PATH = "data/cache/facts.json"


def run_pipeline(
    reports_dir: str = DEFAULT_REPORTS_DIR,
    db_dir: str = DEFAULT_DB_DIR,
    company: str = "IPCC AR6 WGIII",
    year: int = 2022,
    query_text: str = "",
    prompt_path: str = DEFAULT_PROMPT_PATH,
    out_path: str = DEFAULT_OUT_PATH,
    reingest: bool = True,
) -> None:
    """
    Run the full pipeline:
      - (optionally) ingest all PDFs under reports_dir into db_dir
      - extract structured facts into out_path

    This is what you can call from your recursive verification framework.
    """
    # Ensure env vars (OLLAMA_HOST, LLM_MODEL, etc.) are loaded
    load_dotenv()

    reports_dir = str(Path(reports_dir).resolve())
    db_dir = str(Path(db_dir).resolve())
    out_path = str(Path(out_path).resolve())
    prompt_path = str(Path(prompt_path).resolve())

    Path(DEFAULT_CACHE_DIR).mkdir(parents=True, exist_ok=True)

    # 1) Ingest PDFs → vector DB
    if reingest:
        print(f"[pipeline] Ingesting PDFs from {reports_dir} into {db_dir} ...")
        ingest_reports(reports_dir, db_dir)
    else:
        print(f"[pipeline] Skipping ingest (reingest=False), using existing DB at {db_dir}")

    # 2) Extract facts from vector DB → JSON
    if not query_text:
        # safe default – override on CLI if you want something else
        query_text = (
            "Extract quantitative facts with page refs about greenhouse gas emissions, "
            "sector shares, targets, and mitigation potentials in the report."
        )

    print(f"[pipeline] Extracting facts → {out_path}")
    extract_facts(
        db_dir=db_dir,
        query_text=query_text,
        prompt_path=prompt_path,
        out_path=out_path,
        company=company,
        year=year,
    )
    print("[pipeline] Done.")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="End-to-end PDF → vectors → facts pipeline")
    parser.add_argument("--reports", default=DEFAULT_REPORTS_DIR, help="Directory with PDF reports")
    parser.add_argument("--db", default=DEFAULT_DB_DIR, help="Directory for Chroma DB")
    parser.add_argument("--company", required=True, help="Company or report name for metadata")
    parser.add_argument("--year", type=int, required=True, help="Reporting year")
    parser.add_argument(
        "--query",
        default="Extract quantitative facts with page refs about greenhouse gas emissions, "
                "sector shares, targets, and mitigation potentials in the report.",
        help="Semantic query to drive retrieval + extraction",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT_PATH,
        help="Path to extract_facts system prompt (Markdown)",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT_PATH,
        help="Output JSON path for extracted facts",
    )
    parser.add_argument(
        "--no-reingest",
        action="store_true",
        help="Skip ingest step and reuse existing vector DB",
    )

    args = parser.parse_args()

    run_pipeline(
        reports_dir=args.reports,
        db_dir=args.db,
        company=args.company,
        year=args.year,
        query_text=args.query,
        prompt_path=args.prompt,
        out_path=args.out,
        reingest=not args.no_reingest,
    )


if __name__ == "__main__":
    main()
