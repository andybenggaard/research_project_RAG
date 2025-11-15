#!/usr/bin/env python3
"""
Standalone script: PDF ingestion → Chroma DB

Usage:
    python ingest_main.py --reports ./reports --db ./data/vectors
"""

import argparse
from pathlib import Path
from dotenv import load_dotenv

from src.ingest import ingest_reports

DEFAULT_REPORTS_DIR = "./reports"
DEFAULT_DB_DIR = "./data/vectors"


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Ingest PDFs into vector DB")
    parser.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--db", default=DEFAULT_DB_DIR)

    args = parser.parse_args()

    # Ensure output folder exists
    Path(args.db).mkdir(parents=True, exist_ok=True)

    ingest_reports(args.reports, args.db)


if __name__ == "__main__":
    main()
