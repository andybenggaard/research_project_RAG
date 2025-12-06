import pandas as pd
from dataclasses import dataclass

# =========================
# 1. USER INPUTS — FILL THESE
# =========================

#TOTAL_SCOPE1_TCO2 = 33902.0

#ACTIVITY_MWH = {
 #   "coal_and_products": 0.00,
 #   "crude_oil_and_petroleum_products": 64516490.93,
 #   "natural_gas": 3395604.79,
#    "other_fossil_sources": 0.00,
#}

TOTAL_SCOPE1_TCO2 = 34138000.0  # tonnes CO2e

ACTIVITY_MWH = {
    "coal_and_products": 0.0,
    "crude_oil_and_petroleum_products": 112971000.0,
    "natural_gas": 113000.0,
    "other_fossil_sources": 14000.0,
}
SECTOR = "transport"


SECTOR = "transport"

EF_FILE_PATH = "Proofs/emissionfactors.xlsx"

SECTOR = "transport"

# =========================
# 2. MAPPINGS: aggregate category -> fuels in EF file
# =========================

AGGREGATE_CATEGORY_MAP = {
    "crude_oil_and_petroleum_products": [
        "Crude oil", "Orimulsion", "Natural Gas Liquids", "Motor gasoline2",
        "Aviation gasoline", "Jet gasoline", "Jet kerosene", "Other kerosene",
        "Shale oil", "Gas/Diesel oil2", "Residual fuel oil3",
        "Liquified Petroleum Gases", "Ethane", "Naphtha",
        "Bitumen", "Lubricants", "Petroleum coke", "Refinery feedstocks",
        "Refinery gas", "Paraffin waxes", "White Spirit/SBP",
        "Other petroleum products"
    ],
    "natural_gas": ["Natural gas4"],
    "coal_and_products": [
        "Anthracite", "Coking coal", "Other bituminous coal",
        "Sub bituminous coal", "Lignite", "Patent fuel"
    ],
    "other_fossil_sources": [
        # you decide what maps here based on your interpretation
        "Municipal waste (Non biomass fraction)",
        "Industrial wastes",
        "Waste oils"
    ],
}

# Sector-specific weights for expected fuel mix (optional, for sector-average EF)
SECTOR_WEIGHTS = {
    ("manufacturing", "crude_oil_and_petroleum_products"): {
        "Gas/Diesel oil2": 0.8,
        "Residual fuel oil3": 0.2,
    },
    ("manufacturing", "natural_gas"): {
        "Natural gas4": 1.0
    },
    # add other sectors/categories as needed
}

# =========================
# 3. CORE LOGIC
# =========================

@dataclass
class AuditResult:
    implied_ef_total: float
    min_ef_total: float
    max_ef_total: float
    sector_avg_ef_total: float | None
    status: str
    flags: list[str]


def mwh_to_TJ(mwh: float) -> float:
    return mwh * 0.0036  # 1 MWh = 3.6 GJ = 0.0036 TJ


def load_ef_data() -> pd.DataFrame:
    df = pd.read_excel(EF_FILE_PATH)

    # keep only rows where fuel name exists
    df = df[df["Unnamed: 1"].notna()].copy()

    df = df.rename(columns={
        "Unnamed: 1": "fuel",
        "Unnamed: 3": "ef_kg_per_TJ"
    })

    # convert kg/TJ -> t/TJ
    df["ef_tCO2_per_TJ"] = df["ef_kg_per_TJ"] / 1000.0

    df = df[pd.to_numeric(df["ef_tCO2_per_TJ"], errors="coerce").notna()]

    return df[["fuel", "ef_tCO2_per_TJ"]]


def get_fuel_subset(df: pd.DataFrame, aggregate_category: str) -> pd.DataFrame:
    fuels = AGGREGATE_CATEGORY_MAP.get(aggregate_category, [])
    subset = df[df["fuel"].isin(fuels)].copy()
    return subset


def compute_category_min_max(df: pd.DataFrame, category: str) -> tuple[float, float]:
    subset = get_fuel_subset(df, category)
    if subset.empty:
        return (float("inf"), 0.0)
    return subset["ef_tCO2_per_TJ"].min(), subset["ef_tCO2_per_TJ"].max()


def compute_category_sector_avg(df: pd.DataFrame, category: str, sector: str) -> float | None:
    weights = SECTOR_WEIGHTS.get((sector, category))
    if not weights:
        return None

    lookup = dict(zip(df["fuel"], df["ef_tCO2_per_TJ"]))
    num = 0.0
    den = 0.0
    for fuel, w in weights.items():
        if fuel in lookup:
            num += w * lookup[fuel]
            den += w
    if den == 0:
        return None
    return num / den


def audit_total_scope1() -> AuditResult:
    ef_df = load_ef_data()

    # 1) Total Scope 1 energy in TJ (sum of the 4 rows)
    total_scope1_TJ = sum(mwh_to_TJ(v) for v in ACTIVITY_MWH.values())

    # 2) Implied total emission factor (tCO2/TJ)
    implied_ef_total = TOTAL_SCOPE1_TCO2 / total_scope1_TJ

    # 3) Build min/max and sector-average EF across categories, weighted by energy share
    total_min = 0.0
    total_max = 0.0
    total_sector_avg = 0.0
    total_TJ = total_scope1_TJ
    total_sector_weight = 0.0

    for cat, mwh in ACTIVITY_MWH.items():
        cat_TJ = mwh_to_TJ(mwh)
        if cat_TJ == 0:
            continue
        share = cat_TJ / total_TJ

        cat_min, cat_max = compute_category_min_max(ef_df, cat)
        total_min += share * cat_min
        total_max += share * cat_max

        cat_sector_avg = compute_category_sector_avg(ef_df, cat, SECTOR)
        if cat_sector_avg is not None:
            total_sector_avg += share * cat_sector_avg
            total_sector_weight += share

    sector_avg_total = total_sector_avg if total_sector_weight > 0 else None

    # 4) Apply checks
    flags = []
    status = "Plausible"

    if implied_ef_total < total_min or implied_ef_total > total_max:
        status = "Error"
        flags.append("Implied total EF is outside physically possible min/max range for this fuel mix.")
    elif sector_avg_total is not None:
        deviation = abs(implied_ef_total - sector_avg_total) / sector_avg_total
        if deviation > SECTOR_AVG_TOLERANCE:
            status = "Warning"
            flags.append(
                f"Implied total EF deviates {deviation:.1%} from sector-average EF "
                f"(tolerance {SECTOR_AVG_TOLERANCE:.0%})."
            )

    return AuditResult(
        implied_ef_total=implied_ef_total,
        min_ef_total=total_min,
        max_ef_total=total_max,
        sector_avg_ef_total=sector_avg_total,
        status=status,
        flags=flags,
    )


# =========================
# 4. RUN AUDIT
# =========================

result = audit_total_scope1()

print(f"Implied total EF: {result.implied_ef_total:.2f} tCO2/TJ")
print(f"Min EF (mix): {result.min_ef_total:.2f} tCO2/TJ")
print(f"Max EF (mix): {result.max_ef_total:.2f} tCO2/TJ")
print(
    f"Sector-average EF (mix): {result.sector_avg_ef_total:.2f} tCO2/TJ"
    if result.sector_avg_ef_total
    else "Sector-average EF (mix): n/a"
)
print("Status:", result.status)
print("Flags:", result.flags)