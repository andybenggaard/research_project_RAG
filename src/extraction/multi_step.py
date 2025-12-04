# src/extraction/multi_step.py

"""
Multi-step RAG pipeline for compliance verification.

This approach separates:
1. Regulation understanding (what's required?)
2. Company data extraction (what does the company report?)
3. Gap analysis (what's missing?)

This is more effective than single-pass extraction because:
- The LLM learns requirements first before looking at company data
- Reduces hallucination by providing clear context
- Makes compliance gaps explicit
- Better maps to formal verification in Lean
"""

import json
from typing import List, Dict, Any
from pathlib import Path

from ..retrieval import get_client, get_collection, hybrid_retrieve, expand_regulation_query, expand_company_query
from .llm_client import generate_json
from .single_step import _fact_id, _merge_facts


# ----------------------------------------------------------------------
# STEP 1: Extract Regulation Requirements
# ----------------------------------------------------------------------
def extract_regulations(
    db_dir: str,
    regulation_prompt_path: str,
    pool_size: int = 80,
    top_k: int = 30,
) -> List[Dict]:
    """
    Extract ESRS/GHG Protocol requirements from regulatory documents.

    Filters to only regulatory documents (ISO, GHG Protocol, ESRS guidance).
    Returns structured requirements list.
    """
    client = get_client(db_dir)
    col = get_collection(client)

    # Load regulation extraction prompt
    with open(regulation_prompt_path, "r") as f:
        system_prompt = f.read().strip()

    # Query for regulations - adding document type keywords to prioritize regulatory docs
    query = f"ISO GHG Protocol ESRS regulation standard guidance {expand_regulation_query()}"

    # Filter to only regulatory documents (ChromaDB uses $contains not $regex)
    # Note: We can't use $or with $contains, so we'll skip filtering for now
    # and let the retrieval handle it via query relevance
    where_filter = None  # Will retrieve all docs, BM25 will rank regulatory ones higher

    print(f"[STEP 1] Extracting regulation requirements...")
    docs, metas = hybrid_retrieve(col, query, pool_size, top_k, where=where_filter)

    if not docs:
        print("[WARN] No regulation documents found.")
        return []

    all_requirements: List[Dict] = []

    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        page = meta.get("page")
        file_name = meta.get("file_name", "unknown")
        snippet = doc[:1800]

        user_prompt = f"""
Document: {file_name}
Page: {page}

The following is regulatory text:
\"\"\"
{snippet}
\"\"\"

Extract ONLY compliance requirements for ESRS E1 Scope 1 emissions reporting.
Focus on:
- What data MUST be reported
- How it should be calculated
- Required boundaries and scopes
- Data quality requirements

Return ONLY valid JSON.
"""

        print(f"[DEBUG] Processing regulation chunk {i}/{len(docs)} from {file_name}")

        try:
            result = generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_retries=3,
                temperature=0.05,  # Very low for regulations
            )

            requirements = result.get("requirements", [])
            if isinstance(requirements, list):
                for req in requirements:
                    req["source_file"] = file_name
                    req["source_page"] = page
                    all_requirements.append(req)

        except Exception as e:
            print(f"[ERROR] Failed to extract from regulation chunk {i}: {e}")
            continue

    print(f"[STEP 1] ✓ Extracted {len(all_requirements)} requirements")
    return all_requirements


# ----------------------------------------------------------------------
# STEP 2: Extract Company Data with Regulation Context
# ----------------------------------------------------------------------
def extract_company_data(
    db_dir: str,
    company: str,
    year: int,
    company_prompt_path: str,
    regulation_context: List[Dict],
    pool_size: int = 120,
    top_k: int = 60,
) -> List[Dict]:
    """
    Extract company data with regulation requirements as context.

    Uses the regulation requirements to build targeted queries and
    provides context to the LLM about what to look for.
    """
    client = get_client(db_dir)
    col = get_collection(client)

    # Load company extraction prompt
    with open(company_prompt_path, "r") as f:
        system_prompt = f.read().strip()

    # Build context string from regulations
    reg_context = "\n".join([
        f"- {req.get('requirement_text', req.get('text', ''))}"
        for req in regulation_context[:10]  # Top 10 most important
    ])

    # Query for company data with company name and year to prioritize relevant docs
    query = f"{company} {expand_company_query(year)}"

    # Filter to only company reports (using $contains which ChromaDB supports)
    # Note: ChromaDB doesn't support nested $and with $contains well, so we'll rely on query
    where_filter = None  # Query-based filtering via BM25 will prioritize company docs

    print(f"[STEP 2] Extracting company data for {company} ({year})...")
    docs, metas = hybrid_retrieve(col, query, pool_size, top_k, where=where_filter)

    if not docs:
        print(f"[WARN] No company documents found for {company} {year}.")
        return []

    all_facts: List[Dict] = []

    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        page = meta.get("page")
        section_path = meta.get("section_path", "")
        file_name = meta.get("file_name", "unknown")
        snippet = doc[:1800]

        user_prompt = f"""
Company: {company}
Year: {year}

REGULATORY CONTEXT (what you should look for):
{reg_context}

The following is EVIDENCE from {company}'s report:
[page: {page}, file: {file_name}, section: {section_path}]

EVIDENCE:
\"\"\"
{snippet}
\"\"\"

Extract ONLY facts that relate to the regulatory requirements above.
Focus on Scope 1 emissions data, methodology, and boundaries.

Return ONLY valid JSON.
"""

        print(f"[DEBUG] Extracting company data {i}/{len(docs)} page={page}")

        try:
            chunk_result = generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_retries=3,
                temperature=0.1,
            )

            chunk_facts = chunk_result.get("facts", [])
            if isinstance(chunk_facts, list):
                for f in chunk_facts:
                    f.setdefault("page", page)
                    f.setdefault("id", _fact_id(f.get("text", ""), page or 0))
                    f.setdefault("file_name", file_name)
                    f.setdefault("section_path", section_path)
                    all_facts.append(f)

        except Exception as e:
            print(f"[ERROR] Failed to extract company data chunk {i}: {e}")
            continue

    print(f"[STEP 2] ✓ Extracted {len(all_facts)} company facts")
    return all_facts


# ----------------------------------------------------------------------
# STEP 3: Gap Analysis
# ----------------------------------------------------------------------
def perform_gap_analysis(
    regulation_requirements: List[Dict],
    company_facts: List[Dict],
) -> Dict[str, Any]:
    """
    Compare regulation requirements against company disclosures.

    Returns:
        Dictionary with:
        - covered_requirements: List of requirements with supporting facts
        - missing_requirements: List of requirements without support
        - compliance_score: Percentage of requirements covered
    """
    print(f"[STEP 3] Performing gap analysis...")

    covered = []
    missing = []

    # Simple keyword matching (can be improved with embeddings)
    for req in regulation_requirements:
        req_text = req.get("requirement_text", req.get("text", "")).lower()
        req_keywords = set(req_text.split())

        # Check if any company fact addresses this requirement
        supporting_facts = []
        for fact in company_facts:
            fact_text = fact.get("text", "").lower()
            fact_keywords = set(fact_text.split())

            # Simple overlap check (can be improved)
            overlap = len(req_keywords & fact_keywords)
            if overlap > 3:  # At least 3 common words
                supporting_facts.append(fact)

        if supporting_facts:
            covered.append({
                "requirement": req,
                "supporting_facts": supporting_facts[:3]  # Top 3
            })
        else:
            missing.append(req)

    compliance_score = (len(covered) / len(regulation_requirements) * 100) if regulation_requirements else 0

    print(f"[STEP 3] ✓ Compliance score: {compliance_score:.1f}%")
    print(f"[STEP 3]   Covered: {len(covered)} requirements")
    print(f"[STEP 3]   Missing: {len(missing)} requirements")

    return {
        "covered_requirements": covered,
        "missing_requirements": missing,
        "compliance_score": compliance_score,
        "total_requirements": len(regulation_requirements),
        "covered_count": len(covered),
        "missing_count": len(missing),
    }


# ----------------------------------------------------------------------
# Main Multi-Step Pipeline
# ----------------------------------------------------------------------
def extract_facts_multi_step(
    db_dir: str,
    company: str,
    year: int,
    regulation_prompt_path: str,
    company_prompt_path: str,
    out_path: str,
    pool_size: int = 100,
    top_k: int = 40,
):
    """
    Multi-step RAG pipeline:
    1. Extract regulation requirements
    2. Extract company data with regulation context
    3. Perform gap analysis
    4. Save comprehensive results

    Args:
        db_dir: Path to vector database
        company: Company name
        year: Reporting year
        regulation_prompt_path: Path to regulation extraction prompt
        company_prompt_path: Path to company data extraction prompt
        out_path: Output JSON path
        pool_size: Candidates from vector search
        top_k: Keep after BM25 reranking
    """
    print(f"\n{'='*60}")
    print(f"MULTI-STEP RAG EXTRACTION")
    print(f"Company: {company} | Year: {year}")
    print(f"{'='*60}\n")

    # Step 1: Extract regulations
    regulation_requirements = extract_regulations(
        db_dir=db_dir,
        regulation_prompt_path=regulation_prompt_path,
        pool_size=80,
        top_k=30,
    )

    if not regulation_requirements:
        print("[ERROR] No regulation requirements extracted. Aborting.")
        return

    # Step 2: Extract company data with regulation context
    company_facts = extract_company_data(
        db_dir=db_dir,
        company=company,
        year=year,
        company_prompt_path=company_prompt_path,
        regulation_context=regulation_requirements,
        pool_size=pool_size,
        top_k=top_k,
    )

    # Deduplicate company facts
    company_facts = _merge_facts(company_facts)

    # Step 3: Gap analysis
    gap_analysis = perform_gap_analysis(regulation_requirements, company_facts)

    # Save comprehensive output
    output = {
        "company": company,
        "year": year,
        "extraction_method": "multi_step_rag",
        "regulation_requirements": regulation_requirements,
        "company_facts": company_facts,
        "gap_analysis": gap_analysis,
        "summary": {
            "total_regulation_requirements": len(regulation_requirements),
            "total_company_facts": len(company_facts),
            "compliance_score": gap_analysis["compliance_score"],
            "covered_requirements": gap_analysis["covered_count"],
            "missing_requirements": gap_analysis["missing_count"],
        }
    }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"[✓] Multi-step extraction complete → {out_path}")
    print(f"{'='*60}\n")
