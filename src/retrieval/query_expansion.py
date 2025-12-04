# src/retrieval/query_expansion.py

"""
Query expansion with domain-specific synonyms and related terms.
"""

from typing import Dict, List


# Domain-specific term expansions
EXPANSIONS: Dict[str, str] = {
    "scope 1": "scope 1 direct emissions stationary mobile combustion fugitive process",
    "scope 2": "scope 2 indirect emissions purchased electricity heat steam cooling",
    "scope 3": "scope 3 value chain upstream downstream",
    "emissions": "emissions GHG greenhouse gas CO2e carbon dioxide methane CH4 N2O",
    "methodology": "methodology calculation approach measurement quantification method",
    "boundaries": "boundaries organizational consolidation perimeter reporting boundary",
    "targets": "targets goals objectives commitments pledges",
    "intensity": "intensity normalized per unit efficiency ratio",
    "baseline": "baseline base year reference year starting point",
    "verification": "verification assurance audit review attestation",
    "ghg protocol": "GHG Protocol Corporate Standard Scope 1 2 3 guidance",
    "esrs": "ESRS European Sustainability Reporting Standards CSRD E1",
    "materiality": "materiality material double materiality impact financial",
    "carbon": "carbon CO2 dioxide emissions GHG greenhouse",
}


def expand_query(query: str, max_expansions: int = 3) -> str:
    """
    Expand query with domain-specific synonyms and related terms.

    Args:
        query: Original search query
        max_expansions: Maximum number of expansions to add

    Returns:
        Expanded query string
    """
    query_lower = query.lower()
    added_terms: List[str] = []

    for term, expansion in EXPANSIONS.items():
        if term in query_lower and len(added_terms) < max_expansions:
            # Don't add if already in query
            expansion_terms = [t for t in expansion.split() if t not in query_lower]
            if expansion_terms:
                added_terms.extend(expansion_terms[:2])  # Add max 2 terms per match

    if added_terms:
        expanded = f"{query} {' '.join(added_terms[:max_expansions])}"
        print(f"[INFO] Query expanded: {query} → {expanded}")
        return expanded

    return query


def expand_regulation_query() -> str:
    """
    Pre-built query for extracting regulation requirements.
    """
    return (
        "ESRS E1 Scope 1 requirements methodology boundaries consolidation "
        "GHG Protocol Corporate Standard emission categories sources "
        "data quality measurement calculation reporting period "
        "ISO 14064 quantification principles completeness accuracy"
    )


def expand_company_query(year: int) -> str:
    """
    Pre-built query for extracting company data.

    Args:
        year: Reporting year
    """
    return (
        f"Scope 1 2 3 emissions {year} {year-1} total tCO2e tonnes "
        f"breakdown by gas CO2 CH4 N2O by source stationary mobile "
        f"methodology calculation factors base year targets 2030 "
        f"organizational boundary consolidation reporting period"
    )
