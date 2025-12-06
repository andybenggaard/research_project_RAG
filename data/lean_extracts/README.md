# Lean 4 Formalization Extraction Results

This directory contains extracted requirements and numeric data from `compliance_analysis.json`, structured for Lean 4 formalization of ESRS Scope 1 compliance.

## Generated Files

### 1. `extraction_summary.json`
High-level statistics about the extraction:
- **77 Scope 1 requirements** extracted
- **101 Scope 1 facts** with company data
- **171 numeric values** extracted (99 emissions, 22 reduction percentages, 5 targets)
- **13 reduction targets** identified
- Confidence distribution: 88 high, 9 medium, 4 low

### 2. `scope1_requirements.json`
All ESRS E1 regulatory requirements filtered for Scope 1 emissions.

**Structure:**
```json
{
  "requirement_id": "ESRS_E1_R1",
  "requirement_text": "The undertaking shall disclose...",
  "category": "boundary_definition | data_reporting",
  "scope": ["Scope 1"],
  "mandatory": true,
  "source_standard": "ESRS E1",
  "source_file": "Overview-Integration-Disclosure-Rules-Jan-2025.pdf",
  "source_page": 11
}
```

**Categories:**
- `boundary_definition`: 19 requirements
- `data_reporting`: 44 requirements
- `calculation_method`: 14 requirements
- `verification`: 2 requirements
- `quality_requirement`: 1 requirement

**Use Case:** Map these to R1-R6 requirements in your Lean 4 formalization (see `Proofs/mainv2.lean`).

---

### 3. `scope1_facts_with_numbers.json`
Company facts extracted from Maersk reports with all numeric values extracted and classified.

**Structure:**
```json
{
  "id": "maersk-scope1-emissions-2021",
  "text": "Maersk's Scope 1 emissions were 35.2 million tonnes CO2e in 2021",
  "page": 56,
  "file_name": "maersk-sustainability-report_2021.pdf",
  "confidence": "high",
  "fact_type": "claim",
  "esrs_target": {
    "target_type": "GHG reduction",
    "scope": ["Scope 1"],
    "base_year": 2020,
    "target_year": 2030,
    "reduction_percent": 70,
    "absolute_or_intensity": "absolute"
  },
  "numeric_values": [
    {
      "value": 35.2,
      "unit": "million tonnes CO2e",
      "context": "...surrounding text...",
      "fact_id": "maersk-scope1-emissions-2021",
      "page": 56,
      "file_name": "maersk-sustainability-report_2021.pdf",
      "confidence": "high",
      "value_type": "emission"
    }
  ]
}
```

**Numeric Value Types:**
- `emission`: 99 values (tCO2e, tonnes, emissions data)
- `reduction_percent`: 22 values (target percentages)
- `target`: 5 values (target values)
- `year`: Automatically classified (1990-2100 integer values)
- `other`: 45 values (miscellaneous numbers)

---

### 4. `scope1_emissions_data.json`
Filtered list of **only emission values** with metadata.

**Structure:**
```json
{
  "value_tCO2e": 35.2,
  "unit": "million tonnes CO2e",
  "context": "Maersk's Scope 1 emissions were 35.2 million tonnes CO2e in 2021",
  "source_fact_id": "maersk-scope1-emissions-2021",
  "page": 56,
  "file_name": "maersk-sustainability-report_2021.pdf",
  "confidence": "high",
  "scope": ["Scope 1"]
}
```

**Total:** 99 emission values

**Use Case:** Map directly to `Scope1Emission` structure in Lean 4:
```lean
structure Scope1Emission where
  ghgType      : GHGType
  source       : SourceType
  amount_tCO2e : Float
  method       : MethodType
  dataQuality  : DataQuality
  site         : String
  period       : ReportingPeriod
```

---

### 5. `lean4_data_structure.json`
Complete structured data ready for Lean 4 `EmissionInventory`.

**Structure:**
```json
{
  "company": "Maersk",
  "year": 2023,
  "lean_structure": {
    "years": {
      "base_year": 2022,
      "target_year": 2030
    },
    "reduction_targets": [
      {
        "target_type": "GHG reduction",
        "reduction_percent": 70,
        "base_year": 2020,
        "target_year": 2030,
        "absolute_or_intensity": "absolute",
        "scope": ["Scope 1"],
        "fact_id": "5",
        "confidence": "high"
      }
    ],
    "emissions_inventory": [...],
    "requirement_categories": {
      "boundary_definition": [...],
      "calculation_method": [...],
      "data_reporting": [...],
      "quality_requirement": [...],
      "verification": [...]
    }
  }
}
```

**Use Case:** Direct mapping to Lean 4 structures in `Proofs/mainv2.lean`:
- `years` → `ReportingPeriod`
- `reduction_targets` → `ClimateTarget` (for verification)
- `emissions_inventory` → `List Scope1Emission`
- `requirement_categories` → Validation rules (R1-R6, V1-V6)

---

## How to Use These Files for Lean 4 Formalization

### Step 1: Map Requirements to Lean 4 Rules
Use `scope1_requirements.json` to define or validate your requirement rules:

**Example mapping:**
- `boundary_definition` requirements → **R1: Boundary Completeness**
- `calculation_method` requirements → **R3: Methodological Transparency**
- `data_reporting` requirements → **R4: Disaggregation & Sum Consistency**
- `quality_requirement` requirements → **R6: Documentation & Data Quality**

### Step 2: Structure Emission Inventory
Use `scope1_emissions_data.json` to populate `EmissionInventory`:

```lean
def Maersk_2023_inventory : EmissionInventory := {
  emissions := [
    { ghgType := co2,
      source := mobileCombustion,
      amount_tCO2e := 35.2,  -- from extracted data
      method := directMeasurement,
      dataQuality := primary,
      site := "Global Fleet",
      period := { start := ⟨2023, 1, 1⟩, end := ⟨2023, 12, 31⟩ },
      factor? := none
    },
    -- ... more emissions from scope1_emissions_data.json
  ],
  boundary := ...,
  reportingPeriod := ...,
  consolidationApproach := operationalControl,
  declaredTotals := ...
}
```

### Step 3: Verify Reduction Targets
Use `reduction_targets` from `lean4_data_structure.json`:

```lean
def Maersk_2030_target : ClimateTarget := {
  company := "Maersk",
  base_year := 2020,
  target_year := 2030,
  scope1_reduction_pct := 70,  -- from extracted data
  intensity_reduction_pct := 50,
  is_science_based := true
}

theorem Maersk_E1_aligned :
  Meets_ESRS_E1_core Maersk_2030_target := by
  unfold Meets_ESRS_E1_core
  simp [Maersk_2030_target]
```

### Step 4: Run Compliance Validation
Use the boolean checker from `mainv2.lean`:

```lean
#eval scope1CompliantB 0.01 Maersk_2023_inventory
-- Expected: true (if all V1-V6 validations pass)
```

---

## Extraction Statistics

**Company:** Maersk
**Year:** 2023
**Extraction Method:** Multi-step RAG

| Metric | Count |
|--------|-------|
| Total Requirements | 99 |
| Scope 1 Requirements | 77 |
| Total Facts | 125 |
| Scope 1 Facts | 101 |
| Numeric Values Extracted | 171 |
| Emission Values | 99 |
| Reduction Targets | 13 |

**Confidence Distribution:**
- High: 88 (87%)
- Medium: 9 (9%)
- Low: 4 (4%)

---

## Re-running the Extraction

To regenerate these files or process a different company:

```bash
python3 src/extraction/extract_for_lean.py \
  --input data/cache/compliance_analysis.json \
  --output data/lean_extracts
```

**Options:**
- `--input`: Path to compliance analysis JSON (default: `data/cache/compliance_analysis.json`)
- `--output`: Output directory (default: `data/lean_extracts`)

---

## Next Steps for Formalization

1. **Review extracted emissions data** in `scope1_emissions_data.json`
   - Identify missing fields (ghgType, source, method, dataQuality)
   - These may need manual classification or additional extraction

2. **Map requirement categories to R1-R6**
   - Review `scope1_requirements.json`
   - Ensure all mandatory requirements are covered in Lean 4 formalization

3. **Validate numeric values**
   - Check for unrealistic values (e.g., > 1 billion tonnes)
   - Verify unit conversions (million tonnes → tonnes)
   - Cross-reference with original PDFs (page numbers provided)

4. **Define emission factors**
   - Extract emission factors from regulatory documents
   - Create `EmissionFactor` structures in Lean 4

5. **Implement compliance checker**
   - Use `scope1CompliantB` from `mainv2.lean`
   - Test with Maersk data
   - Generate proof certificates

---

## File Locations

- **Source script:** `src/extraction/extract_for_lean.py`
- **Lean 4 proofs:** `Proofs/mainv2.lean` (570 lines, ESRS E1 formalization)
- **Original JSON:** `data/cache/compliance_analysis.json` (392 KB, 11,018 lines)

---

Generated: 2025-12-04
