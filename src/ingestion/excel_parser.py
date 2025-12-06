# src/ingestion/excel_parser.py

"""
Excel extraction optimized for structured data and tables.
- Reads all sheets from Excel files (.xlsx, .xls)
- Preserves table structure with column headers
- Detects and formats formulas and numerical data
- Returns structured blocks compatible with chunker
"""

from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


def format_sheet_as_text(df: pd.DataFrame, sheet_name: str) -> str:
    """
    Formats a DataFrame as readable text with table markers.
    Preserves column headers and handles empty cells.
    """
    if df.empty:
        return f"[Empty sheet: {sheet_name}]"

    lines = []
    lines.append(f"[TABLE: {sheet_name}]")

    # Add column headers
    headers = " | ".join(str(col) for col in df.columns)
    lines.append(headers)
    lines.append("-" * len(headers))

    # Add rows
    for idx, row in df.iterrows():
        row_text = " | ".join(str(val) if pd.notna(val) else "" for val in row)
        lines.append(row_text)

    lines.append("[/TABLE]")
    return "\n".join(lines)


def extract_block_info(df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
    """
    Creates a block structure compatible with the PDF parser output.
    """
    text = format_sheet_as_text(df, sheet_name)

    return {
        "text": text,
        "raw_text": text,
        "block_type": "table",
        "bbox": None,  # Excel doesn't have spatial coordinates
        "font_sizes": [],
        "spans": [],
        "table_text": text,
    }


def extract_sheets(excel_path: Path) -> List[Dict]:
    """
    Extracts structured information from each Excel sheet.
    Returns format compatible with PDF parser for downstream chunking.

    Returns:
        List of sheet records, each containing:
        - page: sheet index (1-indexed)
        - text: formatted table content
        - blocks: structured blocks (one per sheet)
        - file_name: Excel filename
        - source_uri: full file path
    """
    sheets_out = []

    try:
        # Read all sheets from the Excel file
        # engine='openpyxl' for .xlsx, 'xlrd' for .xls
        excel_file = pd.ExcelFile(excel_path)

        for sheet_index, sheet_name in enumerate(excel_file.sheet_names):
            try:
                # Read the sheet
                df = pd.read_excel(excel_file, sheet_name=sheet_name)

                # Skip completely empty sheets
                if df.empty or df.dropna(how='all').empty:
                    continue

                # Create block structure
                block = extract_block_info(df, sheet_name)

                # Create page-like record for this sheet
                sheets_out.append({
                    "page": sheet_index + 1,
                    "text": block["text"],
                    "blocks": [block],
                    "file_name": excel_path.name,
                    "source_uri": str(excel_path.resolve()),
                    "sheet_name": sheet_name,
                })

            except Exception as e:
                print(f"Warning: Could not process sheet '{sheet_name}' in {excel_path.name}: {e}")
                continue

        excel_file.close()

    except Exception as e:
        print(f"Error reading Excel file {excel_path}: {e}")
        return []

    return sheets_out
