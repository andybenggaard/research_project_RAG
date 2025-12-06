#!/usr/bin/env python3
"""
Diagnostic script to check what the retrieval system is actually finding.

This helps debug why extract_multi_step isn't finding the right data.
"""

import sys
sys.path.append('.')

from src.retrieval import get_client, get_collection, hybrid_retrieve

def diagnose_company_retrieval(company="Maersk", year=2023):
    """
    Test what gets retrieved for company data extraction.
    """
    client = get_client("./data/vectors")
    col = get_collection(client)

    # Use the same query as multi_step.py Step 2
    query = f"{company} {company} {company} {year} sustainability report emissions data actual reported"

    print(f"Testing company data retrieval for {company} {year}")
    print(f"Query: {query}")
    print("=" * 80)

    # Test without filter
    print("\n1. WITHOUT document filter (old behavior):")
    docs_no_filter, metas_no_filter = hybrid_retrieve(col, query, pool_size=100, top_k=20, where=None)

    file_counts = {}
    for meta in metas_no_filter:
        fname = meta.get("file_name", "unknown")
        file_counts[fname] = file_counts.get(fname, 0) + 1

    print(f"\nRetrieved {len(docs_no_filter)} chunks from {len(file_counts)} files:")
    for fname, count in sorted(file_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {fname}: {count} chunks")

    # Test with post-retrieval filter (ChromaDB doesn't support $contains)
    print("\n2. WITH post-retrieval filtering (new behavior):")

    try:
        # Get unfiltered results
        docs_unfiltered, metas_unfiltered = hybrid_retrieve(
            col, query, pool_size=100, top_k=50, where=None  # Get more to filter from
        )

        # Filter in Python (same as multi_step.py does now)
        docs_with_filter = []
        metas_with_filter = []
        company_lower = company.lower()

        for doc, meta in zip(docs_unfiltered, metas_unfiltered):
            fname = meta.get("file_name", "").lower()
            if company_lower in fname:
                docs_with_filter.append(doc)
                metas_with_filter.append(meta)

        # Trim to top_k
        docs_with_filter = docs_with_filter[:20]
        metas_with_filter = metas_with_filter[:20]

        file_counts_filtered = {}
        for meta in metas_with_filter:
            fname = meta.get("file_name", "unknown")
            file_counts_filtered[fname] = file_counts_filtered.get(fname, 0) + 1

        print(f"\nRetrieved {len(docs_with_filter)} chunks from {len(file_counts_filtered)} files:")
        for fname, count in sorted(file_counts_filtered.items(), key=lambda x: -x[1]):
            print(f"  {fname}: {count} chunks")

        # Show sample chunks
        print("\n3. Sample chunks retrieved (first 3):")
        for i, (doc, meta) in enumerate(zip(docs_with_filter[:3], metas_with_filter[:3]), 1):
            print(f"\n--- Chunk {i} ---")
            print(f"File: {meta.get('file_name')}, Page: {meta.get('page')}")
            print(f"Content preview:\n{doc[:400]}...")
            print("-" * 80)

        # Check for numeric content
        print("\n4. Checking for numeric/table content in retrieved chunks:")
        numeric_chunks = 0
        table_chunks = 0
        for doc, meta in zip(docs_with_filter, metas_with_filter):
            has_numbers = sum(c.isdigit() for c in doc) > 20
            has_table_markers = '|' in doc or '[TABLE' in doc or 'in 1,000 tonnes' in doc

            if has_numbers:
                numeric_chunks += 1
            if has_table_markers:
                table_chunks += 1
                print(f"  Table found in page {meta.get('page')}: {doc[:200]}...")

        print(f"\nNumeric chunks: {numeric_chunks}/{len(docs_with_filter)}")
        print(f"Table-like chunks: {table_chunks}/{len(docs_with_filter)}")

    except Exception as e:
        print(f"Error with filter: {e}")

    # Test specific table query
    print("\n5. Testing direct table query:")
    table_query = f"{company} {year} scope 1 direct emissions table breakdown tonnes CO2 fuel energy"
    docs_table_all, metas_table_all = hybrid_retrieve(col, table_query, pool_size=100, top_k=50, where=None)

    # Filter for company
    docs_table = []
    metas_table = []
    for doc, meta in zip(docs_table_all, metas_table_all):
        if company_lower in meta.get("file_name", "").lower():
            docs_table.append(doc)
            metas_table.append(meta)

    docs_table = docs_table[:10]
    metas_table = metas_table[:10]

    print(f"\nRetrieved {len(docs_table)} chunks")
    for i, (doc, meta) in enumerate(zip(docs_table[:3], metas_table[:3]), 1):
        has_numbers = sum(c.isdigit() for c in doc) > 20
        has_table = '|' in doc or 'in 1,000 tonnes' in doc
        print(f"\n{i}. Page {meta.get('page')} - Numbers: {has_numbers}, Table: {has_table}")
        print(f"   {doc[:300]}...")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", default="Maersk")
    parser.add_argument("--year", type=int, default=2023)
    args = parser.parse_args()

    diagnose_company_retrieval(args.company, args.year)


if __name__ == "__main__":
    main()
