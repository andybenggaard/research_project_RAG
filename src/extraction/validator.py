# src/extraction/validator.py

"""
Validation layer for extracted facts.
Checks for logical consistency, numeric plausibility, and completeness.
"""

import re
from typing import List, Dict, Any


def extract_numbers(text: str) -> List[float]:
    """Extract all numeric values from text."""
    # Matches numbers with optional commas and decimals
    pattern = r'[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?'
    matches = re.findall(pattern, text)
    return [float(m.replace(',', '')) for m in matches]


def validate_numeric_plausibility(fact: Dict) -> List[str]:
    """Check if numeric values are plausible for ESG data."""
    issues = []
    text = fact.get("text", "").lower()
    numbers = extract_numbers(text)

    if not numbers:
        return issues

    # Check for unrealistic Scope 1 emissions
    if "scope 1" in text or "scope_1" in text:
        for num in numbers:
            if num > 1e9:  # > 1 billion tonnes (unrealistic for single company)
                issues.append(f"Unrealistic Scope 1 value: {num:,.0f} tCO2e")
            if num < 0:
                issues.append(f"Negative emission value: {num}")

    # Check for unrealistic percentages
    if "%" in text or "percent" in text:
        for num in numbers:
            if num > 100 and num < 1000:  # Likely a percentage
                issues.append(f"Percentage > 100%: {num}")
            if num < 0:
                issues.append(f"Negative percentage: {num}")

    return issues


def validate_year_consistency(fact: Dict) -> List[str]:
    """Check year consistency in targets and base years."""
    issues = []

    esrs_target = fact.get("esrs_target", {})
    if not isinstance(esrs_target, dict):
        return issues

    base_year = esrs_target.get("base_year")
    target_year = esrs_target.get("target_year")

    if base_year and target_year:
        try:
            base = int(base_year)
            target = int(target_year)

            if base > target:
                issues.append(f"Base year ({base}) after target year ({target})")

            if target < 2020:
                issues.append(f"Target year ({target}) in the past")

            if base < 1990:
                issues.append(f"Base year ({base}) unrealistically old")

        except (ValueError, TypeError):
            issues.append(f"Invalid year format: base={base_year}, target={target_year}")

    return issues


def validate_fact_completeness(fact: Dict) -> List[str]:
    """Check if fact has required fields."""
    issues = []

    required_fields = ["text", "page", "confidence"]
    for field in required_fields:
        if not fact.get(field):
            issues.append(f"Missing required field: {field}")

    # Check confidence value
    confidence = fact.get("confidence")
    if confidence and confidence not in ["low", "medium", "high"]:
        issues.append(f"Invalid confidence value: {confidence}")

    return issues


def validate_citation_presence(fact: Dict) -> List[str]:
    """Check if high-confidence claims have citations."""
    issues = []

    if fact.get("confidence") == "high":
        citations = fact.get("citations", [])
        if not citations or len(citations) == 0:
            # Check if text contains implicit citations
            text = fact.get("text", "")
            if not any(marker in text.lower() for marker in ["according to", "per", "based on", "follows"]):
                issues.append("High-confidence fact without citation")

    return issues


def validate_facts(facts: List[Dict]) -> Dict[str, Any]:
    """
    Validate a list of extracted facts.

    Returns:
        Dictionary with validation results:
        - valid_facts: List of facts passing validation
        - facts_with_issues: List of (fact, issues) tuples
        - validation_summary: Statistics
    """
    valid_facts = []
    facts_with_issues = []

    for fact in facts:
        all_issues = []

        # Run all validations
        all_issues.extend(validate_numeric_plausibility(fact))
        all_issues.extend(validate_year_consistency(fact))
        all_issues.extend(validate_fact_completeness(fact))
        all_issues.extend(validate_citation_presence(fact))

        if all_issues:
            facts_with_issues.append({
                "fact": fact,
                "issues": all_issues
            })
        else:
            valid_facts.append(fact)

    # Create summary
    summary = {
        "total_facts": len(facts),
        "valid_facts": len(valid_facts),
        "facts_with_issues": len(facts_with_issues),
        "validation_rate": (len(valid_facts) / len(facts) * 100) if facts else 0,
    }

    # Categorize issues
    issue_categories = {}
    for item in facts_with_issues:
        for issue in item["issues"]:
            # Categorize by first word
            category = issue.split(":")[0] if ":" in issue else issue.split()[0]
            issue_categories[category] = issue_categories.get(category, 0) + 1

    summary["issue_breakdown"] = issue_categories

    print(f"\n[VALIDATION] Results:")
    print(f"  Total facts: {summary['total_facts']}")
    print(f"  Valid: {summary['valid_facts']} ({summary['validation_rate']:.1f}%)")
    print(f"  With issues: {summary['facts_with_issues']}")

    if issue_categories:
        print(f"\n  Issue breakdown:")
        for category, count in sorted(issue_categories.items(), key=lambda x: -x[1]):
            print(f"    - {category}: {count}")

    return {
        "valid_facts": valid_facts,
        "facts_with_issues": facts_with_issues,
        "summary": summary,
    }
