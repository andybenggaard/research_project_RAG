#!/usr/bin/env python3
"""
CLI for running multi-step RAG extraction WITH automatic atomization.

This enhanced pipeline:
0. Atomizes broad requirements into atomic queries
1. Extracts regulation requirements
2. Extracts company data using atomic queries
3. Performs gap analysis
4. Saves comprehensive results

Example usage:
    python extract_multi_step_atomic.py --company "Maersk" --year 2023
"""

import argparse
from pathlib import Path
from src.extraction.multi_step import extract_facts_multi_step_atomic


def main():
    parser = argparse.ArgumentParser(
        description="Multi-step RAG extraction with automatic atomization for ESRS Scope 1 compliance"
    )

    # Required arguments
    parser.add_argument(
        "--company",
        type=str,
        required=True,
        help="Company name (e.g., 'Maersk', 'Shell')"
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Reporting year (e.g., 2023)"
    )

    # Optional arguments with defaults
    parser.add_argument(
        "--db-dir",
        type=str,
        default="data/vectors",
        help="Path to vector database directory (default: data/vectors)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: data/cache/{company}_atomic_{year}.json)"
    )

    parser.add_argument(
        "--regulation-prompt",
        type=str,
        default="prompts/extract_regulations.md",
        help="Path to regulation extraction prompt (default: prompts/extract_regulations.md)"
    )

    parser.add_argument(
        "--company-prompt",
        type=str,
        default="prompts/extract_factsV2.md",
        help="Path to company data extraction prompt (default: prompts/extract_factsV2.md)"
    )

    parser.add_argument(
        "--atomizer-prompt",
        type=str,
        default="prompts/atomize_queries.md",
        help="Path to atomizer prompt (default: prompts/atomize_queries.md)"
    )

    parser.add_argument(
        "--critic-prompt",
        type=str,
        default="prompts/critique_queries.md",
        help="Path to critic prompt (default: prompts/critique_queries.md)"
    )

    parser.add_argument(
        "--pool-size",
        type=int,
        default=60,
        help="Number of candidates from vector search per atomic query (default: 60)"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=30,
        help="Number of documents after BM25 reranking per atomic query (default: 30)"
    )

    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Maximum atomization refinement rounds (default: 3)"
    )

    parser.add_argument(
        "--no-answerability-probe",
        action="store_true",
        help="Disable answerability probes (faster but may generate unanswerable queries)"
    )

    args = parser.parse_args()

    # Set default output path if not provided
    if args.output is None:
        output_dir = Path("data/cache")
        output_dir.mkdir(parents=True, exist_ok=True)
        company_clean = args.company.lower().replace(" ", "_")
        args.output = str(output_dir / f"{company_clean}_atomic_{args.year}.json")

    # Validate paths
    db_path = Path(args.db_dir)
    if not db_path.exists():
        print(f"[ERROR] Vector database directory not found: {args.db_dir}")
        print("Have you run ingestion? Try: python -m src.ingest")
        return

    for prompt_name, prompt_path in [
        ("regulation", args.regulation_prompt),
        ("company", args.company_prompt),
        ("atomizer", args.atomizer_prompt),
        ("critic", args.critic_prompt),
    ]:
        if not Path(prompt_path).exists():
            print(f"[ERROR] {prompt_name.capitalize()} prompt not found: {prompt_path}")
            return

    # Run extraction with atomization
    print(f"\n{'='*70}")
    print(f"MULTI-STEP RAG EXTRACTION WITH ATOMIZATION")
    print(f"{'='*70}")
    print(f"Company:                  {args.company}")
    print(f"Year:                     {args.year}")
    print(f"Vector DB:                {args.db_dir}")
    print(f"Output:                   {args.output}")
    print(f"Pool size per query:      {args.pool_size}")
    print(f"Top-k per query:          {args.top_k}")
    print(f"Max atomization rounds:   {args.max_rounds}")
    print(f"Answerability probes:     {'Disabled' if args.no_answerability_probe else 'Enabled'}")
    print(f"{'='*70}\n")

    extract_facts_multi_step_atomic(
        db_dir=args.db_dir,
        company=args.company,
        year=args.year,
        regulation_prompt_path=args.regulation_prompt,
        company_prompt_path=args.company_prompt,
        atomizer_prompt_path=args.atomizer_prompt,
        critic_prompt_path=args.critic_prompt,
        out_path=args.output,
        pool_size=args.pool_size,
        top_k=args.top_k,
        max_atomization_rounds=args.max_rounds,
        enable_answerability_probe=not args.no_answerability_probe,
    )

    print(f"\n{'='*70}")
    print(f"✓ Extraction complete!")
    print(f"Results saved to: {args.output}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
