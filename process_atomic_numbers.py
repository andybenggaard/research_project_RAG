#!/usr/bin/env python3
"""
Process extracted atomic query results from numbers.json for audit variables.

This script filters the 170+ extracted facts to extract clean numerical values
for audit verification, similar to extract_audit_variables.py but for atomic extraction output.
"""

import json
import re
from typing import Dict, Optional, List


def extract_numeric_value(text: str) -> Optional[float]:
    """Extract numeric values from text, handling various formats."""
    text = text.replace(',', '')

    patterns = [
        r'(\d+\.?\d*)\s*(?:tonnes?|tco2e?|mwh|tj|gwh)',
        r'(\d+\.?\d*)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def filter_high_confidence_facts(facts: List[dict]) -> List[dict]:
    """Filter to high-confidence facts with actual numbers."""
    filtered = []
    for fact in facts:
        # Skip low confidence
        if fact.get('confidence') == 'low':
            continue

        # Skip definitions/methodology
        if fact.get('fact_type') == 'definition':
            continue

        # Skip if text says "could not be found"
        text = fact.get('text', '')
        if 'could not be found' in text.lower() or 'does not contain' in text.lower():
            continue

        # Must have a number
        if extract_numeric_value(text) is None:
            continue

        filtered.append(fact)

    return filtered


def extract_scope1_total(facts: List[dict]) -> Optional[float]:
    """Extract total Scope 1 emissions from atomic extraction results."""
    candidates = []

    for fact in facts:
        category = fact.get('atomic_query_category', '')
        text = fact.get('text', '').lower()

        # CRITICAL: Must have tCO2e/tonnes CO2 units, NOT GWh/MWh
        if 'gwh' in text or 'mwh' in text or 'gj' in text or 'tj' in text:
            # Skip energy facts - not emissions
            if 'tco2' not in text and 'tonnes co2' not in text:
                continue

        # Look for total emissions category
        if category == 'total_emissions':
            value = extract_numeric_value(text)
            if value and value > 100:  # Must be reasonable total (lowered threshold)
                # Must contain emissions keywords
                if any(kw in text for kw in ['tco2', 'co2e', 'emissions', 'scope 1']):
                    candidates.append({
                        'value': value,
                        'page': fact.get('page'),
                        'text': text[:100],
                        'category': category
                    })

        # Also check for "scope 1" in text with emissions units
        if 'scope 1' in text and any(kw in text for kw in ['tco2', 'co2e', 'emissions']):
            value = extract_numeric_value(text)
            if value and value > 100:
                # Exclude if it looks like energy
                if 'gwh' not in text and 'mwh' not in text:
                    candidates.append({
                        'value': value,
                        'page': fact.get('page'),
                        'text': text[:100],
                        'category': category
                    })

    if candidates:
        # Log all candidates for debugging
        # Return the largest value (most likely to be the total)
        return max(c['value'] for c in candidates)

    return None


def extract_emissions_by_gas(facts: List[dict]) -> Dict[str, float]:
    """Extract emissions breakdown by gas type."""
    gases = {
        'co2': 0.0,
        'ch4': 0.0,
        'n2o': 0.0,
        'hfcs': 0.0,
        'pfcs': 0.0,
        'sf6': 0.0,
    }

    for fact in facts:
        category = fact.get('atomic_query_category', '')
        if category != 'emissions_by_gas':
            continue

        text = fact.get('text', '').lower()
        query = fact.get('atomic_question', '').lower()
        value = extract_numeric_value(text)

        if not value or value < 10:  # Skip trivial values
            continue

        # Match gas types
        if 'co2' in query and 'ch4' not in query and 'n2o' not in query:
            gases['co2'] = max(gases['co2'], value)
        elif 'ch4' in query or 'methane' in query:
            gases['ch4'] = max(gases['ch4'], value)
        elif 'n2o' in query or 'nitrous oxide' in query:
            gases['n2o'] = max(gases['n2o'], value)
        elif 'hfc' in query:
            gases['hfcs'] = max(gases['hfcs'], value)
        elif 'pfc' in query:
            gases['pfcs'] = max(gases['pfcs'], value)
        elif 'sf6' in query:
            gases['sf6'] = max(gases['sf6'], value)

    return gases


def extract_emissions_by_source(facts: List[dict]) -> Dict[str, float]:
    """Extract emissions breakdown by source."""
    sources = {
        'stationary_combustion': 0.0,
        'mobile_combustion': 0.0,
        'fugitive_emissions': 0.0,
        'process_emissions': 0.0,
    }

    for fact in facts:
        category = fact.get('atomic_query_category', '')
        if category != 'emissions_by_source':
            continue

        text = fact.get('text', '').lower()
        query = fact.get('atomic_question', '').lower()
        value = extract_numeric_value(text)

        if not value or value < 10:
            continue

        if 'stationary' in query:
            sources['stationary_combustion'] = max(sources['stationary_combustion'], value)
        elif 'mobile' in query:
            sources['mobile_combustion'] = max(sources['mobile_combustion'], value)
        elif 'fugitive' in query:
            sources['fugitive_emissions'] = max(sources['fugitive_emissions'], value)
        elif 'process' in query:
            sources['process_emissions'] = max(sources['process_emissions'], value)

    return sources


def extract_fuel_activities(facts: List[dict], sector: str, debug: bool = False) -> tuple:
    """
    Extract activity data by fuel category from facts.
    Returns a tuple of (activities dict, matched_facts dict for debugging).
    """
    activities = {
        "coal_and_products": 0.0,
        "crude_oil_and_petroleum_products": 0.0,
        "natural_gas": 0.0,
        "other_fossil_sources": 0.0,
    }

    matched_facts = {
        "coal_and_products": [],
        "crude_oil_and_petroleum_products": [],
        "natural_gas": [],
        "other_fossil_sources": [],
    }

    for fact in facts:
        category = fact.get('atomic_query_category', '')
        text = fact.get('text', '').lower()

        # Skip if not energy-related
        if category != 'energy_consumption':
            continue

        # Skip facts that say data is NOT reported
        if any(phrase in text for phrase in ['not reported', 'not available', 'n/a', 'not disclosed']):
            continue

        # Extract numeric value
        value = extract_numeric_value(text)
        if not value or value < 10:
            continue

        # Convert to MWh based on units
        mwh_value = value
        if 'gwh' in text:
            mwh_value = value * 1000  # GWh to MWh
        elif 'tj' in text:
            mwh_value = value * 277.778  # TJ to MWh
        elif 'gj' in text:
            mwh_value = value * 0.277778  # GJ to MWh

        # Map to fuel categories based on keywords
        fuel_cat = None
        if any(kw in text for kw in ['fuel oil', 'hfo', 'mdo', 'mgo', 'marine diesel', 'petroleum', 'diesel', 'gasoline']):
            fuel_cat = "crude_oil_and_petroleum_products"
        elif any(kw in text for kw in ['natural gas', 'lng', 'gas fuel']) and 'liquified petroleum' not in text:
            fuel_cat = "natural_gas"
        elif 'coal' in text:
            fuel_cat = "coal_and_products"
        elif any(kw in text for kw in ['lpg', 'biomass', 'waste']):
            fuel_cat = "other_fossil_sources"

        if fuel_cat:
            activities[fuel_cat] = max(activities[fuel_cat], mwh_value)
            if debug:
                matched_facts[fuel_cat].append({
                    'text': fact.get('text', '')[:80],
                    'value': mwh_value,
                    'page': fact.get('page')
                })

    # If no specific fuel breakdown, try to get total and allocate by sector
    total_activity = sum(activities.values())
    if total_activity < 1000:
        # Look for total energy consumption
        for fact in facts:
            text = fact.get('text', '').lower()
            if 'total energy' in text or 'fossil energy' in text:
                value = extract_numeric_value(text)
                if value and value > 1000:
                    # Convert to MWh
                    if 'gwh' in text:
                        total_energy = value * 1000
                    elif 'tj' in text:
                        total_energy = value * 277.778
                    elif 'gj' in text:
                        total_energy = value * 0.277778
                    else:
                        total_energy = value

                    # Allocate by sector
                    if sector == 'transport':
                        activities["crude_oil_and_petroleum_products"] = total_energy * 0.95
                        activities["natural_gas"] = total_energy * 0.05
                    elif sector == 'manufacturing':
                        activities["natural_gas"] = total_energy * 0.60
                        activities["crude_oil_and_petroleum_products"] = total_energy * 0.40
                    else:
                        activities["crude_oil_and_petroleum_products"] = total_energy
                    break

    return (activities, matched_facts) if debug else (activities, {})


def extract_total_energy(facts: List[dict]) -> Optional[float]:
    """Extract total energy consumption in MWh."""
    candidates = []

    for fact in facts:
        category = fact.get('atomic_query_category', '')
        text = fact.get('text', '').lower()

        if category == 'energy_consumption' or 'energy' in text:
            # Handle different units
            if 'gwh' in text:
                value = extract_numeric_value(text)
                if value:
                    # Convert GWh to MWh
                    candidates.append(value * 1000)
            elif 'mwh' in text:
                value = extract_numeric_value(text)
                if value:
                    candidates.append(value)
            elif 'tj' in text:
                value = extract_numeric_value(text)
                if value:
                    # Convert TJ to MWh: 1 TJ = 277.778 MWh
                    candidates.append(value * 277.778)
            elif 'gj' in text:
                value = extract_numeric_value(text)
                if value:
                    # Convert GJ to MWh: 1 GJ = 0.277778 MWh
                    candidates.append(value * 0.277778)

    if candidates:
        return max(candidates)

    return None


def extract_sector(facts: List[dict], company_name: str) -> str:
    """Determine company sector."""
    company_lower = company_name.lower()

    # Check company name
    if 'maersk' in company_lower:
        return 'transport'

    # Check facts for sector keywords
    all_text = ' '.join([f.get('text', '').lower() for f in facts[:30]])

    if any(kw in all_text for kw in ['shipping', 'maritime', 'vessel', 'freight']):
        return 'transport'
    elif any(kw in all_text for kw in ['manufacturing', 'production', 'factory']):
        return 'manufacturing'
    elif any(kw in all_text for kw in ['energy', 'power', 'utility']):
        return 'energy'

    return 'manufacturing'  # default


def validate_emission_factor(scope1_tco2: float, total_activity_mwh: float) -> dict:
    """
    Validate that the implied emission factor is physically reasonable.
    Returns validation status and messages.
    """
    if not scope1_tco2 or not total_activity_mwh or total_activity_mwh < 1:
        return {
            'status': 'ERROR',
            'ef': None,
            'message': 'Missing emissions or activity data'
        }

    total_tj = total_activity_mwh * 0.0036
    implied_ef = scope1_tco2 / total_tj

    # Typical emission factors (tCO2/TJ):
    # Natural gas: ~56
    # Oil products (diesel, fuel oil): ~73-77
    # Coal: ~90-100
    # Reasonable range: 40-120 tCO2/TJ

    if implied_ef < 10:
        return {
            'status': 'ERROR',
            'ef': implied_ef,
            'message': f'Implied EF ({implied_ef:.2f} tCO2/TJ) is impossibly low. Typical EFs: Natural gas ~56, Oil ~74, Coal ~95. Likely scope mismatch between emissions and energy data.'
        }
    elif implied_ef > 150:
        return {
            'status': 'WARNING',
            'ef': implied_ef,
            'message': f'Implied EF ({implied_ef:.2f} tCO2/TJ) is unusually high. Check if emissions include non-energy sources.'
        }
    elif implied_ef < 40:
        return {
            'status': 'WARNING',
            'ef': implied_ef,
            'message': f'Implied EF ({implied_ef:.2f} tCO2/TJ) is low. Expected: Natural gas ~56, Oil ~74. Verify scope consistency.'
        }
    else:
        return {
            'status': 'OK',
            'ef': implied_ef,
            'message': f'Implied EF ({implied_ef:.2f} tCO2/TJ) is reasonable.'
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Process atomic extraction results for audit variables"
    )
    parser.add_argument(
        '--input',
        type=str,
        default='results/numbers.json',
        help='Input JSON file with atomic extraction results'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show which facts were used for each fuel category'
    )

    args = parser.parse_args()

    # Load data
    with open(args.input, 'r') as f:
        data = json.load(f)

    all_facts = data.get('facts', [])
    company = data.get('company', 'Unknown')
    year = data.get('year', 'Unknown')

    print(f"Loaded {len(all_facts)} facts from {args.input}")

    # Filter to high-confidence facts with numbers
    filtered_facts = filter_high_confidence_facts(all_facts)
    print(f"Filtered to {len(filtered_facts)} high-confidence numerical facts")

    # Extract variables
    sector = extract_sector(filtered_facts, company)
    scope1_total = extract_scope1_total(filtered_facts)
    by_gas = extract_emissions_by_gas(filtered_facts)
    by_source = extract_emissions_by_source(filtered_facts)
    fuel_activities, fuel_debug = extract_fuel_activities(filtered_facts, sector, debug=args.debug)
    total_energy = extract_total_energy(filtered_facts)

    # Print results for audit.py
    print("\n" + "=" * 70)
    print("EXTRACTED AUDIT VARIABLES FOR audit.py")
    print("=" * 70)
    print(f"\n# Company: {company}")
    print(f"# Year: {year}")
    print(f"\nTOTAL_SCOPE1_TCO2 = {scope1_total if scope1_total else 0.0}")

    # Activity data (REQUIRED for audit.py)
    print("\nACTIVITY_MWH = {")
    for fuel, value in fuel_activities.items():
        print(f'    "{fuel}": {value:.2f},')
    print("}")

    print(f'\nSECTOR = "{sector}"')

    # Optional: Emissions by gas
    if any(v > 0 for v in by_gas.values()):
        print("\n# Optional: Emissions by gas type (tCO2e)")
        print("EMISSIONS_BY_GAS = {")
        for gas, value in by_gas.items():
            if value > 0:
                print(f'    "{gas}": {value},')
        print("}")

    # Optional: Emissions by source
    if any(v > 0 for v in by_source.values()):
        print("\n# Optional: Emissions by source (tCO2e)")
        print("EMISSIONS_BY_SOURCE = {")
        for source, value in by_source.items():
            if value > 0:
                print(f'    "{source}": {value},')
        print("}")

    print("\n" + "=" * 70)

    # Summary statistics
    print("\nSUMMARY:")
    print(f"  Total facts extracted: {len(all_facts)}")
    print(f"  High-confidence numerical facts: {len(filtered_facts)}")

    if scope1_total:
        print(f"\n  ✓ Total Scope 1: {scope1_total:,.0f} tCO2e")
    else:
        print(f"\n  ⚠ Could not extract total Scope 1")

    # Activity data breakdown
    total_activity = sum(fuel_activities.values())
    if total_activity > 0:
        print(f"\n  ✓ Activity data breakdown (MWh):")
        for fuel, value in fuel_activities.items():
            if value > 0:
                percentage = (value / total_activity) * 100
                print(f"    - {fuel}: {value:,.0f} MWh ({percentage:.1f}%)")
        print(f"\n    Total: {total_activity:,.0f} MWh ({total_activity * 0.0036:,.0f} TJ)")

        # Validate emission factor
        validation = validate_emission_factor(scope1_total, total_activity)
        status_icon = {
            'OK': '✓',
            'WARNING': '⚠',
            'ERROR': '✗'
        }.get(validation['status'], '?')

        if validation['ef']:
            print(f"\n  {status_icon} {validation['message']}")
        else:
            print(f"\n  {status_icon} {validation['message']}")

        if validation['status'] == 'ERROR':
            print("\n  LIKELY ISSUES:")
            print("    - Emissions and energy data may have different scope boundaries")
            print("    - Energy might be global while emissions are regional (e.g., UK SECR)")
            print("    - Check if extraction mixed up units (GWh vs tCO2e)")
    else:
        print("\n  ⚠ Could not extract activity data")

    if total_energy:
        print(f"  ✓ Total energy: {total_energy:,.0f} MWh ({total_energy * 0.0036:,.0f} TJ)")

    # Show breakdown percentages
    total_by_gas = sum(by_gas.values())
    if total_by_gas > 0:
        print(f"\n  Emissions by gas breakdown:")
        for gas, value in by_gas.items():
            if value > 0:
                pct = (value / total_by_gas) * 100
                print(f"    - {gas.upper()}: {value:,.0f} tCO2e ({pct:.1f}%)")

    total_by_source = sum(by_source.values())
    if total_by_source > 0:
        print(f"\n  Emissions by source breakdown:")
        for source, value in by_source.items():
            if value > 0:
                pct = (value / total_by_source) * 100
                print(f"    - {source}: {value:,.0f} tCO2e ({pct:.1f}%)")

    print(f"\n  Sector: {sector}")

    # Debug: Show which facts were matched for each fuel category
    if args.debug and fuel_debug:
        print("\n" + "=" * 70)
        print("DEBUG: FUEL CATEGORY MATCHES")
        print("=" * 70)
        for fuel_cat, facts in fuel_debug.items():
            if facts:
                print(f"\n{fuel_cat.upper()}:")
                for f in facts:
                    print(f"  - {f['value']:,.0f} MWh | Page {f['page']} | {f['text']}")

    # Show some sample facts
    print("\n" + "=" * 70)
    print("SAMPLE HIGH-CONFIDENCE FACTS:")
    print("=" * 70)

    for i, fact in enumerate(filtered_facts[:10], 1):
        category = fact.get('atomic_query_category', 'unknown')
        text = fact.get('text', '')[:150]
        page = fact.get('page', '?')
        print(f"\n{i}. [{category}] (page {page})")
        print(f"   {text}")


if __name__ == "__main__":
    main()
