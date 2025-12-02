/-
  ESRS E1 – Scope 1 Emissions Formalisation in Lean 4
  ---------------------------------------------------

  This file defines:
    * Core entities (GHGType, SourceType, MethodType, DataQuality, etc.)
    * Scope1Emission and EmissionInventory structures
    * Declared totals for consistency checks
    * Requirements & sub-requirements as predicates:
        - R1: Boundary completeness
        - R2: GHG completeness
        - R3: Methodological transparency
        - R4: Disaggregation
        - R5: Temporal accuracy
        - R6: Documentation
      plus validation rules V1–V6 (non-negative, sum checks, etc.)

  Below that, we add a Boolean checker layer:
    * ...B versions of requirements returning Bool
    * scope1CompliantB : Float → EmissionInventory → Bool
      (eps for numeric tolerance)
-/

import Std.Data.List.Basic
import Std.Data.List.Lemmas

namespace ESRS
namespace Scope1

open Std
open List

--------------------------------------------------------------------------------
-- 1. Basic Enumerations & Supporting Types
--------------------------------------------------------------------------------

inductive GHGType
  | co2
  | ch4
  | n2o
  | hfcs
  | pfcs
  | sf6
  | nf3
  deriving Repr, DecidableEq

inductive SourceType
  | stationaryCombustion
  | mobileCombustion
  | process
  | fugitive
  deriving Repr, DecidableEq

inductive MethodType
  | directMeasurement
  | calculation
  | estimation
  deriving Repr, DecidableEq

inductive DataQuality
  | primary
  | secondary
  | estimated
  deriving Repr, DecidableEq

inductive ConsolidationApproach
  | operationalControl
  | financialControl
  | equityShare
  deriving Repr, DecidableEq

/-- A simple representation of a reporting period. Extend as needed. -/
structure ReportingPeriod where
  startYear : Nat
  endYear   : Nat
  deriving Repr, DecidableEq

/--
BoundaryDefinition is modelled abstractly: we assume it can tell us
whether it is valid for a given consolidation approach and whether it
covers a given site or source type.

NOTE: For the Boolean checker we keep these as `Bool`, and interpret
      `= true` in the Prop-level spec.
-/
structure BoundaryDefinition where
  description           : String
  validForConsolidation : ConsolidationApproach → Bool
  coversSource          : SourceType → Bool
  coversSite            : String → Bool
  deriving Repr

/-- Emission factor metadata (simplified). -/
structure EmissionFactor where
  name        : String
  source      : String        -- e.g. "IPCC 2006", "DEFRA 2024"
  value       : Float         -- e.g. kg CO2e per unit of activity
  unit        : String        -- e.g. "kgCO2e/kWh"
  deriving Repr, DecidableEq

--------------------------------------------------------------------------------
-- 2. Core Entities: Scope1Emission & Inventory
--------------------------------------------------------------------------------

/--
Scope1Emission: one record of Scope 1 emissions for a specific gas,
source type, site, and method.
-/
structure Scope1Emission where
  ghgType      : GHGType
  source       : SourceType
  amount_tCO2e : Float
  method       : MethodType
  dataQuality  : DataQuality
  site         : String
  period       : ReportingPeriod
  factor?      : Option EmissionFactor
  deriving Repr, DecidableEq

/--
DeclaredTotals: what the reporter claims as the official totals
(by source, by gas, and overall Scope 1 total). Used for consistency
checks against the detailed list of Scope1Emission entries.
-/
structure DeclaredTotals where
  bySource   : SourceType → Float
  byGHG      : GHGType    → Float
  scope1Total : Float
  deriving Repr

/--
EmissionInventory: the full Scope 1 inventory for a given reporting period.
-/
structure EmissionInventory where
  emissions             : List Scope1Emission
  boundary              : BoundaryDefinition
  reportingPeriod       : ReportingPeriod
  consolidationApproach : ConsolidationApproach
  declaredTotals        : DeclaredTotals
  deriving Repr

--------------------------------------------------------------------------------
-- 3. Helper Constants & Aggregation Functions
--------------------------------------------------------------------------------

/-- All recognised GHG types. -/
def allGHGTypes : List GHGType :=
  [ GHGType.co2, GHGType.ch4, GHGType.n2o,
    GHGType.hfcs, GHGType.pfcs, GHGType.sf6, GHGType.nf3 ]

/-- All recognised Scope 1 source types. -/
def allSourceTypes : List SourceType :=
  [ SourceType.stationaryCombustion,
    SourceType.mobileCombustion,
    SourceType.process,
    SourceType.fugitive ]

/-- Total Scope 1 emissions across all entries. -/
def totalScope1 (inv : EmissionInventory) : Float :=
  inv.emissions.foldl (fun acc e => acc + e.amount_tCO2e) 0.0

/-- Total emissions by a given SourceType. -/
def totalBySource (inv : EmissionInventory) (st : SourceType) : Float :=
  inv.emissions.foldl
    (fun acc e =>
      if e.source = st then acc + e.amount_tCO2e else acc)
    0.0

/-- Total emissions by a given GHGType. -/
def totalByGHG (inv : EmissionInventory) (gas : GHGType) : Float :=
  inv.emissions.foldl
    (fun acc e =>
      if e.ghgType = gas then acc + e.amount_tCO2e else acc)
    0.0

/--
Check that all emissions in the inventory belong to the same reporting period.
(You can later relax this to allow sub-periods if needed.)
-/
def allEmissionsInPeriod (inv : EmissionInventory) : Prop :=
  ∀ e ∈ inv.emissions, e.period = inv.reportingPeriod

--------------------------------------------------------------------------------
-- 4. Requirement Type & Helpers
--------------------------------------------------------------------------------

/-- A requirement on some α is simply a predicate on α. -/
abbrev Requirement (α : Type) := α → Prop

--------------------------------------------------------------------------------
-- 5. Requirements: R1 – Boundary Completeness
--------------------------------------------------------------------------------

/--
R1.1 – Consolidation alignment:
The boundary must be valid for the chosen consolidation approach.
-/
def R1_1_consolidationAlignment : Requirement EmissionInventory :=
  fun inv => inv.boundary.validForConsolidation inv.consolidationApproach = true

/--
R1.3 – Emission source coverage:
For every required Scope 1 source type, there must exist at least
one emission record with that source type, OR the boundary explicitly
declares that it does not cover that source type.
-/
def R1_3_sourceCoverage (inv : EmissionInventory) : Prop :=
  ∀ st, st ∈ allSourceTypes →
    (inv.boundary.coversSource st = true →
      ∃ e, e ∈ inv.emissions ∧ e.source = st)

/--
R1 – Combined boundary completeness requirement.
Extend with more sub-requirements (e.g., site coverage) as needed.
-/
def R1_boundaryCompleteness : Requirement EmissionInventory :=
  fun inv =>
    R1_1_consolidationAlignment inv ∧
    R1_3_sourceCoverage inv

--------------------------------------------------------------------------------
-- 6. Requirements: R2 – GHG Completeness
--------------------------------------------------------------------------------

/--
Helper: "inventory declares zero" can be understood as the declared total
for that gas being exactly 0.0. This is a simplification that you can
refine later (e.g. adding explicit flags).
-/
def inventoryDeclaresZeroForGas (inv : EmissionInventory) (gas : GHGType) : Prop :=
  inv.declaredTotals.byGHG gas = 0.0

/--
R2 – GHG completeness:
For every recognised GHG type, either:
  * there is at least one emission record with that gas, OR
  * the inventory explicitly declares zero emissions for that gas.
-/
def R2_ghgCompleteness (inv : EmissionInventory) : Prop :=
  ∀ gas, gas ∈ allGHGTypes →
    (∃ e, e ∈ inv.emissions ∧ e.ghgType = gas) ∨
    inventoryDeclaresZeroForGas inv gas

--------------------------------------------------------------------------------
-- 7. Requirements: R3 – Methodological Transparency
--------------------------------------------------------------------------------

/--
R3.1 – Method declaration:
Every emission must specify method and data quality, and if the method
is calculation, it should reference an emission factor.
-/
def R3_1_methodDeclaration (inv : EmissionInventory) : Prop :=
  ∀ e ∈ inv.emissions,
    match e.method with
    | MethodType.directMeasurement =>
        True
    | MethodType.estimation =>
        True
    | MethodType.calculation =>
        e.factor?.isSome

/--
R3.2 – Emission factor source:
If a factor is provided, it must have non-empty name and source.
(You can refine this with a whitelist of accepted standards.)
-/
def R3_2_factorSourceValid (inv : EmissionInventory) : Prop :=
  ∀ e ∈ inv.emissions,
    match e.factor? with
    | none   => True
    | some f => f.name ≠ "" ∧ f.source ≠ ""

/--
R3 – Combined methodological transparency requirement.
-/
def R3_methodologicalTransparency : Requirement EmissionInventory :=
  fun inv =>
    R3_1_methodDeclaration inv ∧
    R3_2_factorSourceValid inv

--------------------------------------------------------------------------------
-- 8. Requirements: R4 – Disaggregation & Sum Consistency
--------------------------------------------------------------------------------

/--
R4.2 – By source type:
Declared totals by source must match the aggregated emissions.
-/
def R4_2_disaggregationBySource (inv : EmissionInventory) : Prop :=
  ∀ st, st ∈ allSourceTypes →
    inv.declaredTotals.bySource st = totalBySource inv st

/--
R4.3 – By GHG type:
Declared totals by GHG must match the aggregated emissions.
-/
def R4_3_disaggregationByGHG (inv : EmissionInventory) : Prop :=
  ∀ gas, gas ∈ allGHGTypes →
    inv.declaredTotals.byGHG gas = totalByGHG inv gas

/--
R4 – Overall disaggregation & total consistency:
  * by-source totals align
  * by-GHG totals align
  * overall declared Scope 1 total equals the sum of all records.
-/
def R4_disaggregationAndTotals (inv : EmissionInventory) : Prop :=
  R4_2_disaggregationBySource inv ∧
  R4_3_disaggregationByGHG inv ∧
  inv.declaredTotals.scope1Total = totalScope1 inv

--------------------------------------------------------------------------------
-- 9. Requirements: R5 – Temporal Accuracy
--------------------------------------------------------------------------------

/--
R5.1 – All emissions fall within the reporting period.
-/
def R5_1_reportingPeriodAlignment : Requirement EmissionInventory :=
  fun inv => allEmissionsInPeriod inv

--------------------------------------------------------------------------------
-- 10. Requirements: R6 – Documentation & Data Quality
--------------------------------------------------------------------------------

/--
R6.1 – Data lineage & assumptions are present.
This is abstract; here we simply require that data quality is not "estimated"
for every single record (i.e. there must be some primary or secondary data).
You can refine this with explicit "metadata" structures later.
-/
def R6_1_presenceOfNonEstimatedData (inv : EmissionInventory) : Prop :=
  ∃ e, e ∈ inv.emissions ∧ e.dataQuality ≠ DataQuality.estimated

/--
R6 – Documentation requirement placeholder.
Right now it only enforces presence of some non-estimated data. Extend
with explicit metadata as needed.
-/
def R6_documentation (inv : EmissionInventory) : Prop :=
  R6_1_presenceOfNonEstimatedData inv

--------------------------------------------------------------------------------
-- 11. Validation Rules V1–V6 (Reusable Checks)
--------------------------------------------------------------------------------

/--
V1 – Boundary completeness check: we reuse R1.
-/
def V1_boundaryCompleteness : Requirement EmissionInventory :=
  R1_boundaryCompleteness

/--
V2 – GHG completeness check: we reuse R2.
-/
def V2_ghgCompleteness : Requirement EmissionInventory :=
  R2_ghgCompleteness

/--
V3 – Method consistency: we reuse R3.
-/
def V3_methodConsistency : Requirement EmissionInventory :=
  R3_methodologicalTransparency

/--
V4 – Sum validation: we reuse R4.
-/
def V4_sumValidation : Requirement EmissionInventory :=
  R4_disaggregationAndTotals

/--
V5 – No negative values.
-/
def V5_nonNegativeEmissions (inv : EmissionInventory) : Prop :=
  ∀ e ∈ inv.emissions, e.amount_tCO2e ≥ 0.0

/--
V6 – Temporal validity: we reuse R5.1.
-/
def V6_temporalValidity : Requirement EmissionInventory :=
  R5_1_reportingPeriodAlignment

--------------------------------------------------------------------------------
-- 12. Combined "Overall Compliance" Predicate (Prop-level spec)
--------------------------------------------------------------------------------

/--
Combined predicate that says an inventory satisfies all Scope 1
requirements defined above. This is where you can plug in your
proof obligations later.
-/
def scope1Compliant (inv : EmissionInventory) : Prop :=
  V1_boundaryCompleteness inv ∧
  V2_ghgCompleteness inv ∧
  V3_methodConsistency inv ∧
  V4_sumValidation inv ∧
  V5_nonNegativeEmissions inv ∧
  V6_temporalValidity inv ∧
  R6_documentation inv

--------------------------------------------------------------------------------
-- 13. Boolean Checker Layer
--------------------------------------------------------------------------------

/-- Approximate equality for Floats with tolerance `eps`. -/
def approxEq (eps : Float) (x y : Float) : Bool :=
  decide (Float.abs (x - y) ≤ eps)

/-- Does the inventory have at least one emission for this source type? -/
def hasEmissionForSourceB (inv : EmissionInventory) (st : SourceType) : Bool :=
  inv.emissions.any (fun e => decide (e.source = st))

/-- Does the inventory have at least one emission for this GHG type? -/
def hasEmissionForGasB (inv : EmissionInventory) (gas : GHGType) : Bool :=
  inv.emissions.any (fun e => decide (e.ghgType = gas))

/-- Bool version of "inventory declares zero for this gas". -/
def inventoryDeclaresZeroForGasB (inv : EmissionInventory) (gas : GHGType) : Bool :=
  decide (inv.declaredTotals.byGHG gas = 0.0)

/-- All emissions in period (Bool). -/
def allEmissionsInPeriodB (inv : EmissionInventory) : Bool :=
  inv.emissions.all (fun e => decide (e.period = inv.reportingPeriod))

/------------------------------------------------------------------------------
-- R1 – Boundary completeness (Bool)
------------------------------------------------------------------------------/

/-- R1.1 (Bool) – boundary consolidation alignment. -/
def R1_1_consolidationAlignmentB (inv : EmissionInventory) : Bool :=
  inv.boundary.validForConsolidation inv.consolidationApproach

/-- R1.3 (Bool) – for covered sources, there is at least one emission. -/
def R1_3_sourceCoverageB (inv : EmissionInventory) : Bool :=
  allSourceTypes.all (fun st =>
    if inv.boundary.coversSource st then
      hasEmissionForSourceB inv st
    else
      true)

/-- R1 (Bool) – combined. -/
def R1_boundaryCompletenessB (inv : EmissionInventory) : Bool :=
  R1_1_consolidationAlignmentB inv &&
  R1_3_sourceCoverageB inv

/------------------------------------------------------------------------------
-- R2 – GHG completeness (Bool)
------------------------------------------------------------------------------/

/-- R2 (Bool) – for each gas, either we have data or we declare zero. -/
def R2_ghgCompletenessB (inv : EmissionInventory) : Bool :=
  allGHGTypes.all (fun gas =>
    hasEmissionForGasB inv gas || inventoryDeclaresZeroForGasB inv gas)

/------------------------------------------------------------------------------
-- R3 – Methodological transparency (Bool)
------------------------------------------------------------------------------/

/-- R3.1 (Bool) – method declaration & factor presence for calculations. -/
def R3_1_methodDeclarationB (inv : EmissionInventory) : Bool :=
  inv.emissions.all (fun e =>
    match e.method with
    | MethodType.directMeasurement => true
    | MethodType.estimation        => true
    | MethodType.calculation       => e.factor?.isSome)

/-- R3.2 (Bool) – factor must have non-empty name & source if present. -/
def R3_2_factorSourceValidB (inv : EmissionInventory) : Bool :=
  inv.emissions.all (fun e =>
    match e.factor? with
    | none   => true
    | some f =>
        (!f.name.isEmpty) && (!f.source.isEmpty))

/-- R3 (Bool) – combined. -/
def R3_methodologicalTransparencyB (inv : EmissionInventory) : Bool :=
  R3_1_methodDeclarationB inv &&
  R3_2_factorSourceValidB inv

/------------------------------------------------------------------------------
-- R4 – Disaggregation & sums (Bool, using eps for tolerance)
------------------------------------------------------------------------------/

/-- R4.2 (Bool) – by-source totals match aggregated values up to eps. -/
def R4_2_disaggregationBySourceB (eps : Float) (inv : EmissionInventory) : Bool :=
  allSourceTypes.all (fun st =>
    approxEq eps (inv.declaredTotals.bySource st) (totalBySource inv st))

/-- R4.3 (Bool) – by-GHG totals match aggregated values up to eps. -/
def R4_3_disaggregationByGHGB (eps : Float) (inv : EmissionInventory) : Bool :=
  allGHGTypes.all (fun gas =>
    approxEq eps (inv.declaredTotals.byGHG gas) (totalByGHG inv gas))

/-- R4 (Bool) – disaggregation & overall total (with eps tolerance). -/
def R4_disaggregationAndTotalsB (eps : Float) (inv : EmissionInventory) : Bool :=
  R4_2_disaggregationBySourceB eps inv &&
  R4_3_disaggregationByGHGB eps inv &&
  approxEq eps inv.declaredTotals.scope1Total (totalScope1 inv)

/------------------------------------------------------------------------------
-- R5 – Temporal accuracy (Bool)
------------------------------------------------------------------------------/

/-- R5.1 (Bool) – all emissions fall into the reporting period. -/
def R5_1_reportingPeriodAlignmentB (inv : EmissionInventory) : Bool :=
  allEmissionsInPeriodB inv

/------------------------------------------------------------------------------
-- R6 – Documentation & data quality (Bool)
------------------------------------------------------------------------------/

/-- R6.1 (Bool) – there exists some non-estimated data. -/
def R6_1_presenceOfNonEstimatedDataB (inv : EmissionInventory) : Bool :=
  inv.emissions.any (fun e =>
    !(decide (e.dataQuality = DataQuality.estimated)))

/-- R6 (Bool) – documentation placeholder. -/
def R6_documentationB (inv : EmissionInventory) : Bool :=
  R6_1_presenceOfNonEstimatedDataB inv

/------------------------------------------------------------------------------
-- Validation rules V1–V6 (Bool versions)
------------------------------------------------------------------------------/

/-- V1 (Bool) – boundary completeness. -/
def V1_boundaryCompletenessB (inv : EmissionInventory) : Bool :=
  R1_boundaryCompletenessB inv

/-- V2 (Bool) – GHG completeness. -/
def V2_ghgCompletenessB (inv : EmissionInventory) : Bool :=
  R2_ghgCompletenessB inv

/-- V3 (Bool) – method consistency. -/
def V3_methodConsistencyB (inv : EmissionInventory) : Bool :=
  R3_methodologicalTransparencyB inv

/-- V4 (Bool) – sum validation with tolerance. -/
def V4_sumValidationB (eps : Float) (inv : EmissionInventory) : Bool :=
  R4_disaggregationAndTotalsB eps inv

/-- V5 (Bool) – no negative emissions. -/
def V5_nonNegativeEmissionsB (inv : EmissionInventory) : Bool :=
  inv.emissions.all (fun e => decide (e.amount_tCO2e ≥ 0.0))

/-- V6 (Bool) – temporal validity. -/
def V6_temporalValidityB (inv : EmissionInventory) : Bool :=
  R5_1_reportingPeriodAlignmentB inv

/------------------------------------------------------------------------------
-- Combined Boolean checker
------------------------------------------------------------------------------/

/--
Boolean checker for overall Scope 1 compliance.

`eps` is a numeric tolerance for float-based equality comparisons
in R4 (totals alignment).
-/
def scope1CompliantB (eps : Float) (inv : EmissionInventory) : Bool :=
  V1_boundaryCompletenessB inv &&
  V2_ghgCompletenessB inv &&
  V3_methodConsistencyB inv &&
  V4_sumValidationB eps inv &&
  V5_nonNegativeEmissionsB inv &&
  V6_temporalValidityB inv &&
  R6_documentationB inv

end Scope1
end ESRS
