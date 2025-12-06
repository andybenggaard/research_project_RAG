"""
Extract requirements and numeric data from compliance_analysis.json
for Lean 4 formalization of ESRS Scope 1 compliance.

This script processes the massive JSON file and outputs:
1. Structured requirements (ESRS regulations)
2. Extracted numeric values (emissions, targets, reductions)
3. Lean 4-ready data structures
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class NumericValue:
    """Represents an extracted numeric value with context"""
    value: float
    unit: Optional[str]
    context: str
    fact_id: str
    page: int
    file_name: str
    confidence: str
    value_type: str  # "emission", "target", "reduction_percent", "year", "other"


@dataclass
class Requirement:
    """Structured ESRS requirement"""
    requirement_id: str
    requirement_text: str
    category: str
    scope: List[str]
    mandatory: bool
    source_standard: str
    source_file: str
    source_page: int


@dataclass
class ComplianceFact:
    """Company compliance fact with numeric extraction"""
    id: str
    text: str
    page: int
    file_name: str
    confidence: str
    fact_type: str
    esrs_target: Dict[str, Any]
    numeric_values: List[NumericValue]


class LeanDataExtractor:
    """Extracts and structures data for Lean 4 formalization"""

    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self.data = self._load_json()

    def _load_json(self) -> Dict[str, Any]:
        """Load the compliance analysis JSON"""
        print(f"Loading {self.json_path}...")
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_numbers(self, text: str) -> List[Tuple[float, str]]:
        """
        Extract all numeric values from text with surrounding context.
        Returns list of (value, context) tuples.
        """
        results = []

        # Pattern 1: Numbers with units (e.g., "123.45 tonnes CO2e", "35%", "2030")
        pattern_with_unit = r'([-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*([a-zA-Z%]+(?:\s+[a-zA-Z0-9]+)*)?'

        for match in re.finditer(pattern_with_unit, text):
            num_str = match.group(1).replace(',', '')
            unit = match.group(2) if match.group(2) else ""

            try:
                value = float(num_str)
                # Get surrounding context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()

                results.append((value, unit.strip(), context))
            except ValueError:
                continue

        return results

    def classify_numeric_value(self, value: float, unit: str, context: str) -> str:
        """Classify the type of numeric value based on context"""
        context_lower = context.lower()
        unit_lower = unit.lower()

        # Year detection
        if 1990 <= value <= 2100 and value == int(value):
            return "year"

        # Percentage detection
        if '%' in unit or 'percent' in context_lower:
            return "reduction_percent"

        # Emission detection
        if any(term in unit_lower for term in ['tco2', 'co2', 'tonne', 'ton', 'mtco2', 'ktco2']):
            return "emission"
        if any(term in context_lower for term in ['emission', 'ghg', 'carbon', 'co2', 'scope 1', 'scope 2', 'scope 3']):
            return "emission"

        # Target detection
        if any(term in context_lower for term in ['target', 'goal', 'reduction', 'decrease']):
            return "target"

        return "other"

    def extract_requirements(self) -> List[Requirement]:
        """Extract all regulation requirements"""
        requirements = []

        for req_data in self.data.get("regulation_requirements", []):
            req = Requirement(
                requirement_id=req_data.get("requirement_id", ""),
                requirement_text=req_data.get("requirement_text", ""),
                category=req_data.get("category", ""),
                scope=req_data.get("scope", []),
                mandatory=req_data.get("mandatory", False),
                source_standard=req_data.get("source_standard", ""),
                source_file=req_data.get("source_file", ""),
                source_page=req_data.get("source_page", 0)
            )
            requirements.append(req)

        return requirements

    def extract_company_facts(self) -> List[ComplianceFact]:
        """Extract company facts with numeric values"""
        facts = []

        for fact_data in self.data.get("company_facts", []):
            text = fact_data.get("text", "")
            numeric_extractions = self.extract_numbers(text)

            numeric_values = []
            for value, unit, context in numeric_extractions:
                value_type = self.classify_numeric_value(value, unit, context)

                numeric_values.append(NumericValue(
                    value=value,
                    unit=unit if unit else None,
                    context=context,
                    fact_id=fact_data.get("id", ""),
                    page=fact_data.get("page", 0),
                    file_name=fact_data.get("file_name", ""),
                    confidence=fact_data.get("confidence", ""),
                    value_type=value_type
                ))

            fact = ComplianceFact(
                id=fact_data.get("id", ""),
                text=text,
                page=fact_data.get("page", 0),
                file_name=fact_data.get("file_name", ""),
                confidence=fact_data.get("confidence", ""),
                fact_type=fact_data.get("fact_type", ""),
                esrs_target=fact_data.get("esrs_target", {}),
                numeric_values=numeric_values
            )
            facts.append(fact)

        return facts

    def filter_scope1_requirements(self, requirements: List[Requirement]) -> List[Requirement]:
        """Filter requirements relevant to Scope 1"""
        return [req for req in requirements if "Scope 1" in req.scope]

    def filter_scope1_facts(self, facts: List[ComplianceFact]) -> List[ComplianceFact]:
        """Filter facts relevant to Scope 1"""
        return [
            fact for fact in facts
            if "Scope 1" in fact.esrs_target.get("scope", [])
        ]

    def extract_emissions_data(self, facts: List[ComplianceFact]) -> List[Dict[str, Any]]:
        """Extract structured emissions data for Lean 4 EmissionInventory"""
        emissions_data = []

        for fact in facts:
            for num_val in fact.numeric_values:
                if num_val.value_type == "emission":
                    emissions_data.append({
                        "value_tCO2e": num_val.value,
                        "unit": num_val.unit,
                        "context": num_val.context,
                        "source_fact_id": fact.id,
                        "page": fact.page,
                        "file_name": fact.file_name,
                        "confidence": fact.confidence,
                        "scope": fact.esrs_target.get("scope", [])
                    })

        return emissions_data

    def generate_lean_structure(self, facts: List[ComplianceFact],
                               requirements: List[Requirement]) -> Dict[str, Any]:
        """Generate a Lean 4-compatible data structure"""

        # Extract years (base_year, target_year)
        years = {}
        for fact in facts:
            target = fact.esrs_target
            if target.get("base_year"):
                years["base_year"] = target["base_year"]
            if target.get("target_year"):
                years["target_year"] = target["target_year"]

        # Extract reduction targets
        reduction_targets = []
        for fact in facts:
            target = fact.esrs_target
            if target.get("reduction_percent"):
                reduction_targets.append({
                    "target_type": target.get("target_type"),
                    "reduction_percent": target.get("reduction_percent"),
                    "base_year": target.get("base_year"),
                    "target_year": target.get("target_year"),
                    "absolute_or_intensity": target.get("absolute_or_intensity"),
                    "scope": target.get("scope", []),
                    "fact_id": fact.id,
                    "confidence": fact.confidence
                })

        # Extract emissions inventory
        emissions = self.extract_emissions_data(facts)

        # Map requirements to R1-R6 categories
        requirement_categories = {
            "boundary_definition": [],
            "calculation_method": [],
            "data_reporting": [],
            "quality_requirement": [],
            "verification": []
        }

        for req in requirements:
            for category in requirement_categories.keys():
                if category in req.category:
                    requirement_categories[category].append({
                        "requirement_id": req.requirement_id,
                        "text": req.requirement_text,
                        "mandatory": req.mandatory,
                        "source_page": req.source_page
                    })

        return {
            "company": self.data.get("company"),
            "year": self.data.get("year"),
            "lean_structure": {
                "years": years,
                "reduction_targets": reduction_targets,
                "emissions_inventory": emissions,
                "requirement_categories": requirement_categories
            }
        }

    def export_to_files(self, output_dir: str):
        """Export extracted data to multiple output files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print("\n=== Extracting Requirements ===")
        requirements = self.extract_requirements()
        scope1_requirements = self.filter_scope1_requirements(requirements)
        print(f"Total requirements: {len(requirements)}")
        print(f"Scope 1 requirements: {len(scope1_requirements)}")

        print("\n=== Extracting Company Facts ===")
        facts = self.extract_company_facts()
        scope1_facts = self.filter_scope1_facts(facts)
        print(f"Total facts: {len(facts)}")
        print(f"Scope 1 facts: {len(scope1_facts)}")

        # Count numeric values
        total_numeric_values = sum(len(f.numeric_values) for f in facts)
        scope1_numeric_values = sum(len(f.numeric_values) for f in scope1_facts)
        print(f"Total numeric values extracted: {total_numeric_values}")
        print(f"Scope 1 numeric values: {scope1_numeric_values}")

        # Export 1: All Scope 1 requirements
        req_file = output_path / "scope1_requirements.json"
        with open(req_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(req) for req in scope1_requirements], f, indent=2)
        print(f"\n✓ Exported: {req_file}")

        # Export 2: All Scope 1 facts with numeric values
        facts_file = output_path / "scope1_facts_with_numbers.json"
        with open(facts_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(fact) for fact in scope1_facts], f, indent=2)
        print(f"✓ Exported: {facts_file}")

        # Export 3: Emissions data only
        emissions_data = self.extract_emissions_data(scope1_facts)
        emissions_file = output_path / "scope1_emissions_data.json"
        with open(emissions_file, 'w', encoding='utf-8') as f:
            json.dump(emissions_data, f, indent=2)
        print(f"✓ Exported: {emissions_file}")
        print(f"  Total emission values: {len(emissions_data)}")

        # Export 4: Lean 4 structure
        lean_structure = self.generate_lean_structure(scope1_facts, scope1_requirements)
        lean_file = output_path / "lean4_data_structure.json"
        with open(lean_file, 'w', encoding='utf-8') as f:
            json.dump(lean_structure, f, indent=2)
        print(f"✓ Exported: {lean_file}")

        # Export 5: Summary statistics
        stats = {
            "company": self.data.get("company"),
            "year": self.data.get("year"),
            "extraction_stats": {
                "total_requirements": len(requirements),
                "scope1_requirements": len(scope1_requirements),
                "total_facts": len(facts),
                "scope1_facts": len(scope1_facts),
                "total_numeric_values": total_numeric_values,
                "scope1_numeric_values": scope1_numeric_values,
                "emission_values": len(emissions_data),
                "reduction_targets": len(lean_structure["lean_structure"]["reduction_targets"])
            },
            "numeric_value_types": self._count_value_types(scope1_facts),
            "requirement_categories": self._count_requirement_categories(scope1_requirements),
            "confidence_distribution": self._count_confidence_levels(scope1_facts)
        }

        stats_file = output_path / "extraction_summary.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"✓ Exported: {stats_file}")

        print(f"\n=== All exports complete ===")
        print(f"Output directory: {output_path.absolute()}")

        return stats

    def _count_value_types(self, facts: List[ComplianceFact]) -> Dict[str, int]:
        """Count numeric values by type"""
        counts = {}
        for fact in facts:
            for num_val in fact.numeric_values:
                counts[num_val.value_type] = counts.get(num_val.value_type, 0) + 1
        return counts

    def _count_requirement_categories(self, requirements: List[Requirement]) -> Dict[str, int]:
        """Count requirements by category"""
        counts = {}
        for req in requirements:
            # Categories can be pipe-separated
            categories = [cat.strip() for cat in req.category.split('|')]
            for cat in categories:
                counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _count_confidence_levels(self, facts: List[ComplianceFact]) -> Dict[str, int]:
        """Count facts by confidence level"""
        counts = {}
        for fact in facts:
            counts[fact.confidence] = counts.get(fact.confidence, 0) + 1
        return counts


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract requirements and numeric data for Lean 4 formalization"
    )
    parser.add_argument(
        "--input",
        default="data/cache/compliance_analysis.json",
        help="Path to compliance_analysis.json"
    )
    parser.add_argument(
        "--output",
        default="data/lean_extracts",
        help="Output directory for extracted files"
    )

    args = parser.parse_args()

    # Run extraction
    extractor = LeanDataExtractor(args.input)
    stats = extractor.export_to_files(args.output)

    # Print summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"Company: {stats['company']}")
    print(f"Year: {stats['year']}")
    print(f"\nScope 1 Requirements: {stats['extraction_stats']['scope1_requirements']}")
    print(f"Scope 1 Facts: {stats['extraction_stats']['scope1_facts']}")
    print(f"Numeric Values Extracted: {stats['extraction_stats']['scope1_numeric_values']}")
    print(f"Emission Values: {stats['extraction_stats']['emission_values']}")
    print(f"\nNumeric Value Types:")
    for vtype, count in stats['numeric_value_types'].items():
        print(f"  {vtype}: {count}")
    print(f"\nRequirement Categories:")
    for cat, count in stats['requirement_categories'].items():
        print(f"  {cat}: {count}")
    print(f"\nConfidence Distribution:")
    for conf, count in stats['confidence_distribution'].items():
        print(f"  {conf}: {count}")
    print("="*60)


if __name__ == "__main__":
    main()
