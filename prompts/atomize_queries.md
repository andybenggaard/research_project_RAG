# ATOMIC QUERY GENERATOR

Split broad requirements into atomic queries. One metric per query.

## OUTPUT FORMAT

Return valid JSON only:

```json
{
  "atomic_queries": [
    {
      "query_id": "Q001",
      "question": "Total Scope 1 emissions in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "total_emissions",
      "keywords": ["Scope 1", "total", "emissions", "GHG", "tCO2e", "{{reporting_year}}"],
      "semantic_hints": ["direct emissions", "Scope 1 GHG", "total Scope 1"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    }
  ]
}
```

## CATEGORIES

- total_emissions: Total Scope 1
- emissions_by_gas: CO2, CH4, N2O, HFCs, etc.
- emissions_by_source: stationary, mobile, fugitive, process
- emission_factor: Emission factors with units
- energy_consumption: Fuel consumption
- methodology: Calculation methods
- targets: Reduction goals

## EXAMPLES

**Input:** "Report total Scope 1 emissions"

**Output:**
```json
{
  "atomic_queries": [
    {
      "query_id": "Q001",
      "question": "Total Scope 1 GHG emissions in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "total_emissions",
      "keywords": ["Scope 1", "total", "emissions", "GHG", "tCO2e", "{{reporting_year}}"],
      "semantic_hints": ["direct emissions from owned sources", "total Scope 1 GHG", "Scope 1 CO2 equivalent"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    }
  ]
}
```

**Input:** "Breakdown by gas type CO2, CH4, N2O"

**Output:**
```json
{
  "atomic_queries": [
    {
      "query_id": "Q001",
      "question": "Scope 1 CO2 emissions in tonnes for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2", "tCO2", "kt CO2"],
      "scope": "Scope 1",
      "category": "emissions_by_gas",
      "keywords": ["Scope 1", "CO2", "carbon dioxide", "emissions", "{{reporting_year}}"],
      "semantic_hints": ["CO2 from Scope 1", "carbon dioxide direct emissions", "Scope 1 CO2"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    },
    {
      "query_id": "Q002",
      "question": "Scope 1 CH4 emissions in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "emissions_by_gas",
      "keywords": ["Scope 1", "CH4", "methane", "emissions", "{{reporting_year}}"],
      "semantic_hints": ["methane Scope 1", "CH4 direct emissions", "fugitive methane"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    },
    {
      "query_id": "Q003",
      "question": "Scope 1 N2O emissions in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "emissions_by_gas",
      "keywords": ["Scope 1", "N2O", "nitrous oxide", "emissions", "{{reporting_year}}"],
      "semantic_hints": ["nitrous oxide Scope 1", "N2O direct emissions", "N2O from combustion"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    }
  ]
}
```

**Input:** "Emissions by source: stationary, mobile, fugitive, process"

**Output:**
```json
{
  "atomic_queries": [
    {
      "query_id": "Q001",
      "question": "Scope 1 emissions from stationary combustion in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "emissions_by_source",
      "keywords": ["Scope 1", "stationary", "combustion", "boilers", "emissions", "{{reporting_year}}"],
      "semantic_hints": ["stationary combustion emissions", "boilers and furnaces", "on-site fuel burning"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    },
    {
      "query_id": "Q002",
      "question": "Scope 1 emissions from mobile combustion in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "emissions_by_source",
      "keywords": ["Scope 1", "mobile", "combustion", "vehicles", "fleet", "{{reporting_year}}"],
      "semantic_hints": ["mobile combustion emissions", "company vehicles", "fleet emissions"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    },
    {
      "query_id": "Q003",
      "question": "Scope 1 fugitive emissions in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "emissions_by_source",
      "keywords": ["Scope 1", "fugitive", "leakage", "refrigerants", "{{reporting_year}}"],
      "semantic_hints": ["fugitive emissions", "refrigerant leakage", "equipment leaks"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    },
    {
      "query_id": "Q004",
      "question": "Scope 1 process emissions in tonnes CO2e for {{reporting_year}}",
      "expected_answer_type": "number",
      "unit_candidates": ["tonnes CO2e", "tCO2e", "kt CO2e"],
      "scope": "Scope 1",
      "category": "emissions_by_source",
      "keywords": ["Scope 1", "process", "emissions", "industrial", "{{reporting_year}}"],
      "semantic_hints": ["process emissions", "industrial processes", "non-combustion emissions"],
      "validation_rules": {"must_contain_number": true, "must_contain_year": true, "must_mention_scope_1": true}
    }
  ]
}
```

## RULES

1. Split compound requirements (use "and", "or", commas as split points)
2. One metric per query
3. Include {{reporting_year}} in question and keywords
4. For numbers: add unit_candidates
5. Add 5+ keywords
6. Add 3+ semantic_hints (short phrases)
7. Use scope "Scope 1" always
8. Set validation_rules based on answer type

Return only JSON. No extra text.
