# src/__main__.py

"""
Entry point for running `python -m src.ingest`
"""

from .ingest import ingest_reports

if __name__ == "__main__":
    # Default paths
    REPORTS_DIR = "./reports"
    DB_DIR = "./data/vectors"

    print("[INFO] Starting ingestion pipeline...")
    print(f"[INFO] Reports directory: {REPORTS_DIR}")
    print(f"[INFO] Vector DB directory: {DB_DIR}")

    ingest_reports(REPORTS_DIR, DB_DIR)
