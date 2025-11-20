import Std

/-- Simple structure for a 2030 climate target (percentages as Nat). -/
structure ClimateTarget where
  company                 : String
  base_year               : Nat          -- e.g. 2016 or 2020
  target_year             : Nat          -- e.g. 2030
  scope1_reduction_pct    : Nat          -- 35 = 35%
  intensity_reduction_pct : Nat          -- 50 = 50%
  is_science_based        : Bool
  deriving Repr

/-- Our core ESRS E1 alignment predicate for this project. -/
def Meets_ESRS_E1_core (t : ClimateTarget) : Prop :=
  t.target_year = 2030 ∧
  t.is_science_based = true ∧
  t.scope1_reduction_pct ≥ 35 ∧
  t.intensity_reduction_pct ≥ 50

/-- Facts about Maersk, filled from `facts.json`. -/
def Maersk_2030_target : ClimateTarget :=
{ company                 := "Maersk",
  base_year               := 2016,  -- from “35% reduction by 2030, compared to 2016”
  target_year             := 2030,
  scope1_reduction_pct    := 35,    -- -35% overall/value-chain
  intensity_reduction_pct := 50,    -- ~50% intensity reduction (EEOI) vs 2020
  is_science_based        := true } -- SBTi-aligned 2030/2040 targets

/-- Main theorem: Maersk's 2030 target meets our ESRS E1 core criteria. -/
theorem Maersk_E1_aligned :
  Meets_ESRS_E1_core Maersk_2030_target := by
  unfold Meets_ESRS_E1_core
  unfold Maersk_2030_target
  -- goal: 2030 = 2030 ∧ true = true ∧ 35 ≥ 35 ∧ 50 ≥ 50
  apply And.intro
  · decide                         -- 2030 = 2030
  · apply And.intro
    · decide                       -- true = true
    · apply And.intro
      · exact Nat.le_refl _        -- 35 ≥ 35
      · exact Nat.le_refl _        -- 50 ≥ 50
