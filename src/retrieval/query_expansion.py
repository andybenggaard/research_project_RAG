# src/retrieval/query_expansion.py

"""
Query expansion with domain-specific synonyms and related terms.
"""

from typing import Dict, List


# Domain-specific term expansions (Scope 1 focused)
EXPANSIONS: Dict[str, str] = {
    "scope 1": "scope 1 direct emissions stationary mobile combustion fugitive process",
    "emissions": "emissions GHG greenhouse gas CO2e carbon dioxide methane CH4 N2O HFCs PFCs SF6 NF3",
    "emission factors": "emission factors EF conversion factors activity data IPCC EPA DEFRA GWP",
    "methodology": "methodology calculation approach measurement quantification method",
    "boundaries": "boundaries organizational consolidation perimeter reporting boundary",
    "targets": "targets goals objectives commitments pledges reduction",
    "intensity": "intensity normalized per unit efficiency ratio",
    "baseline": "baseline base year reference year starting point",
    "verification": "verification assurance audit review attestation",
    "ghg protocol": "GHG Protocol Corporate Standard Scope 1 direct emissions guidance",
    "esrs": "ESRS European Sustainability Reporting Standards CSRD E1 climate",
    "combustion": "combustion stationary mobile fuel diesel petrol natural gas heating",
    "fugitive": "fugitive refrigerants leakage HFCs SF6 equipment",
    "process": "process emissions industrial chemical reactions cement steel",
}

# ESRS Scope 1 Semantic Search Terms - Organized by emission category
SCOPE1_SEMANTIC_TERMS: Dict[str, List[str]] = {
    # Total emissions queries
    "total_emissions": [
        "total Scope 1 greenhouse gas emissions",
        "direct emissions from owned or controlled sources",
        "total Scope 1 GHG in CO2 equivalent",
        "Scope 1 emissions including all sources",
        "aggregate direct emissions from operations",
    ],

    # Emissions by greenhouse gas type
    "co2_emissions": [
        "carbon dioxide emissions from Scope 1 sources",
        "CO2 released from fuel combustion",
        "Scope 1 CO2 emissions from direct sources",
        "biogenic and fossil CO2 from operations",
    ],

    "ch4_emissions": [
        "methane emissions from Scope 1 fugitive sources",
        "CH4 released from natural gas infrastructure",
        "methane leakage from company operations",
        "Scope 1 CH4 emissions in CO2 equivalent",
        "fugitive methane from refrigeration or gas systems",
    ],

    "n2o_emissions": [
        "nitrous oxide emissions from combustion",
        "N2O released from industrial processes",
        "Scope 1 nitrous oxide from fuel burning",
    ],

    "fluorinated_gases": [
        "HFC emissions from refrigeration equipment",
        "SF6 leakage from electrical equipment",
        "PFC emissions from industrial processes",
        "fluorinated greenhouse gas emissions",
        "refrigerant leakage from air conditioning systems",
    ],

    # Emissions by source category
    "stationary_combustion": [
        "emissions from stationary combustion sources such as boilers and furnaces",
        "fuel consumption in on-site equipment and generators",
        "natural gas burned in company facilities",
        "diesel consumption in backup generators and stationary equipment",
        "emissions from heating systems and boilers",
        "fuel oil burned in stationary equipment",
    ],

    "mobile_combustion": [
        "emissions from company-owned vehicles and fleet",
        "fuel consumption by company-operated vessels and ships",
        "emissions from owned or leased vehicles",
        "aviation fuel used in company aircraft",
        "diesel and gasoline consumed by company fleet",
        "bunker fuel consumption for maritime transport",
    ],

    "fugitive_emissions": [
        "refrigerant leakage from air conditioning and cooling systems",
        "fugitive emissions from equipment and pipelines",
        "HFC emissions from refrigeration equipment",
        "methane leakage from natural gas infrastructure",
        "equipment leaks and fugitive releases",
        "unintentional emissions from refrigerants",
    ],

    "process_emissions": [
        "process emissions from industrial operations",
        "emissions from chemical reactions not involving combustion",
        "CO2 released during cement or lime production",
        "non-combustion emissions from manufacturing",
        "industrial process GHG releases",
    ],

    # Fuel consumption and energy
    "natural_gas": [
        "natural gas fuel consumption in energy units",
        "energy from natural gas combustion",
        "natural gas used in operations",
        "cubic meters or GWh of natural gas consumed",
    ],

    "diesel_fuel": [
        "diesel fuel consumption in liters or gallons",
        "diesel oil used in vehicles and equipment",
        "emissions from diesel combustion",
        "diesel energy consumption",
    ],

    "fuel_oil": [
        "fuel oil consumption for heating or power generation",
        "heavy fuel oil or bunker fuel use",
        "fuel oil burned in boilers",
        "residual fuel oil consumption",
    ],

    "gasoline": [
        "gasoline consumption in company vehicles",
        "petrol used in light-duty fleet",
        "motor gasoline fuel consumption",
    ],

    "coal": [
        "coal consumption for energy or heat",
        "coal burned in company operations",
        "anthracite or bituminous coal use",
    ],

    "biomass": [
        "biomass fuel consumption and emissions",
        "renewable fuel use in operations",
        "biofuels and biogenic emissions",
        "wood pellets or biogas consumption",
    ],

    # Emission factors
    "emission_factors": [
        "emission conversion factors used for Scope 1 calculations",
        "CO2 equivalent factors for fuel combustion",
        "emission factors from IPCC or national inventories",
        "kg CO2 per liter of diesel or natural gas",
        "GWP values for greenhouse gases",
        "fuel-specific emission coefficients",
    ],

    # Methodology and boundaries
    "methodology": [
        "calculation methodology for direct emissions",
        "consolidation approach for organizational boundaries",
        "financial control or operational control method",
        "how Scope 1 emissions are measured and calculated",
        "quantification approach for GHG inventory",
    ],

    "consolidation": [
        "organizational boundary based on financial control",
        "operational control consolidation approach",
        "equity share method for reporting",
        "how the company defines reporting boundaries",
    ],

    # Targets and performance
    "reduction_targets": [
        "Scope 1 emissions reduction targets",
        "absolute or intensity-based reduction goals",
        "percentage reduction from base year",
        "science-based targets for direct emissions",
        "decarbonization commitments for Scope 1",
    ],
}


def get_semantic_hints_for_category(category: str) -> List[str]:
    """
    Get semantic search hints for a specific emission category.

    Args:
        category: Emission category (e.g., 'stationary_combustion', 'ch4_emissions')

    Returns:
        List of semantic search phrases
    """
    return SCOPE1_SEMANTIC_TERMS.get(category, [])


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
    Pre-built query for extracting Scope 1 regulation requirements.
    """
    return (
        "ESRS E1 Scope 1 direct emissions requirements methodology boundaries consolidation "
        "GHG Protocol Corporate Standard emission factors IPCC EPA DEFRA "
        "stationary combustion mobile combustion fugitive process emissions "
        "data quality measurement calculation reporting period "
        "ISO 14064 quantification principles completeness accuracy "
        "CO2 CH4 N2O HFCs PFCs SF6 GWP conversion factors"
    )


def expand_company_query(year: int) -> str:
    """
    Pre-built query for extracting Scope 1 company data.

    Args:
        year: Reporting year
    """
    return (
        f"Scope 1 direct emissions {year} {year-1} total tCO2e tonnes "
        f"breakdown by gas CO2 CH4 N2O HFCs PFCs SF6 NF3 "
        f"by source stationary combustion mobile combustion fugitive process "
        f"methodology calculation emission factors activity data "
        f"base year targets reduction organizational boundary consolidation "
        f"reporting period IPCC EPA DEFRA GWP"
    )
