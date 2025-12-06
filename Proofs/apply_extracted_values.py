"""
Apply extracted values from compliance_analysis.json to audit.py

This script updates the USER INPUTS section of audit.py with extracted values.
"""

import json
import os
import sys

# Import the extraction functions
from extract_audit_variables import (
    extract_scope1_total,
    extract_fuel_activities,
    extract_sector,
    extract_total_energy
)


def update_audit_file(scope1_total, activity_mwh, sector):
    """Update audit.py with extracted values."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audit_file = os.path.join(script_dir, 'audit.py')

    with open(audit_file, 'r') as f:
        lines = f.readlines()

    # Find and update the values
    new_lines = []
    in_user_inputs = False
    in_activity_dict = False
    dict_indent = 0

    for line in lines:
        # Track if we're in the USER INPUTS section
        if '# 1. USER INPUTS' in line or 'USER INPUTS — FILL THESE' in line:
            in_user_inputs = True

        # Stop tracking after the mappings section starts
        if '# 2. MAPPINGS' in line or 'MAPPINGS:' in line:
            in_user_inputs = False

        # Update TOTAL_SCOPE1_TCO2
        if in_user_inputs and line.strip().startswith('TOTAL_SCOPE1_TCO2'):
            new_lines.append(f'TOTAL_SCOPE1_TCO2 = {scope1_total}\n')
            continue

        # Update ACTIVITY_MWH dictionary
        if in_user_inputs and line.strip().startswith('ACTIVITY_MWH'):
            in_activity_dict = True
            new_lines.append(line)  # Keep the opening line
            new_lines.append('    "coal_and_products": {:.2f},\n'.format(activity_mwh["coal_and_products"]))
            new_lines.append('    "crude_oil_and_petroleum_products": {:.2f},\n'.format(activity_mwh["crude_oil_and_petroleum_products"]))
            new_lines.append('    "natural_gas": {:.2f},\n'.format(activity_mwh["natural_gas"]))
            new_lines.append('    "other_fossil_sources": {:.2f},\n'.format(activity_mwh["other_fossil_sources"]))
            new_lines.append('}\n')
            continue

        # Skip old ACTIVITY_MWH contents
        if in_activity_dict:
            if '}' in line:
                in_activity_dict = False
            continue

        # Update SECTOR
        if in_user_inputs and line.strip().startswith('SECTOR'):
            new_lines.append(f'SECTOR = "{sector}"\n')
            continue

        # Keep all other lines
        new_lines.append(line)

    # Write back to file
    with open(audit_file, 'w') as f:
        f.writelines(new_lines)

    print(f"✓ Updated {audit_file}")


def main():
    # Load compliance analysis data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_file = os.path.join(project_root, 'data', 'cache', 'compliance_analysis.json')

    if not os.path.exists(data_file):
        print(f"Error: Could not find {data_file}")
        sys.exit(1)

    with open(data_file, 'r') as f:
        data = json.load(f)

    company_facts = data.get('company_facts', [])
    company_name = data.get('company', 'Unknown')

    # Extract variables
    sector = extract_sector(company_facts, company_name)
    scope1_total = extract_scope1_total(company_facts)
    activity_mwh = extract_fuel_activities(company_facts, sector)

    if not scope1_total:
        print("Warning: Could not extract Scope 1 total. Using default value of 0.0")
        scope1_total = 0.0

    print("=" * 60)
    print("APPLYING EXTRACTED VALUES TO audit.py")
    print("=" * 60)
    print(f"\nCompany: {company_name}")
    print(f"Year: {data.get('year', 'Unknown')}")
    print(f"\nValues to apply:")
    print(f"  TOTAL_SCOPE1_TCO2 = {scope1_total}")
    print(f"  SECTOR = \"{sector}\"")
    print(f"\n  ACTIVITY_MWH:")
    for fuel, value in activity_mwh.items():
        print(f"    {fuel}: {value:.2f} MWh")

    # Ask for confirmation
    response = input("\nApply these values to audit.py? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        update_audit_file(scope1_total, activity_mwh, sector)
        print("\n✓ Successfully updated audit.py")
        print("\nNext steps:")
        print("  1. Review the updated values in audit.py")
        print("  2. Verify the EF_FILE_PATH points to your emission factors file")
        print("  3. Run: python audit.py")
    else:
        print("\nCancelled. No changes made to audit.py")


if __name__ == "__main__":
    main()
