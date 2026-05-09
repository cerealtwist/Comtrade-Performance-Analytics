"""
Cleans raw Comtrade and World Bank LPI data.
Outputs analysis-ready CSVs to data/processed/.
"""

import logging
import os

import pandas as pd

# Setup

os.makedirs("data/processed", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/processed/cleaning.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
TIMESTAMP = "20260508"

# Comtrade Cleaning

KEEP_COLS = {
    "refYear": "year",
    "refMonth": "month",
    "period": "period",
    "flowCode": "flow_code",
    "flow_label": "flow_label",
    "partnerISO": "partner_iso",
    "partnerDesc": "partner_name",
    "cmdCode": "hs_code",
    "cmdDesc": "hs_description",
    "cifvalue": "cif_value_usd",
    "fobvalue": "fob_value_usd",
    "primaryValue": "primary_value_usd",
    "qty": "quantity",
    "isReported": "is_reported",
}

FOCUS_PARTNERS = {
    "CHN": "China",
    "JPN": "Japan",
    "SGP": "Singapore",
    "USA": "United States",
    "DEU": "Germany",
    "MYS": "Malaysia",
    "KOR": "South Korea",
    "W00": "World",
}


def clean_comtrade() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = os.path.join(RAW_DIR, f"comtrade_hs85_all_{TIMESTAMP}.csv")
    log.info(f"Loading: {path}")

    raw = pd.read_csv(path, dtype={"period": str, "cmdCode": str})
    log.info(f"Raw shape: {raw.shape}")

    # Select and rename columns
    existing_cols = {k: v for k, v in KEEP_COLS.items() if k in raw.columns}
    df = raw[list(existing_cols.keys())].rename(columns=existing_cols)

    # Parse date - period is YYYYMM string
    df = df.assign(
        date=pd.to_datetime(df["period"].str.zfill(6), format="%Y%m"),
        year=lambda x: x["date"].dt.year,
        month=lambda x: x["date"].dt.month,
        quarter=lambda x: x["date"].dt.quarter,
    )

    # Drop rows with null primary trade value or null net weight
    before = len(df)
    df = df.dropna(subset=["primary_value_usd"])
    log.info(f"Dropped {before - len(df)} rows with null primary value.")

    # Split into partner-level and world aggregate
    df_partners = df.loc[df["partner_iso"].isin(FOCUS_PARTNERS.keys())].copy()
    df_world = df.loc[df["partner_iso"] == "W00"].copy()

    # Overwrite partner_name from mapping for consistency
    df_partners = df_partners.assign(
        partner_name=df_partners["partner_iso"].map(FOCUS_PARTNERS)
    )

    # Clean flow label
    df_partners = df_partners.assign(
        flow_label=df_partners["flow_label"].str.lower().str.strip()
    )

    # Final column order
    final_cols = [
        "date",
        "year",
        "month",
        "quarter",
        "period",
        "flow_code",
        "flow_label",
        "partner_iso",
        "partner_name",
        "hs_code",
        "hs_description",
        "primary_value_usd",
        "fob_value_usd",
        "cif_value_usd",
        "is_reported",
    ]

    final_cols = [c for c in final_cols if c in df_partners.columns]
    df_partners = df_partners[final_cols].sort_values(
        ["date", "flow_label", "partner_iso"]
    )

    # Save
    out_partners = os.path.join(PROCESSED_DIR, "comtrade_hs85_clean.csv")
    out_world = os.path.join(PROCESSED_DIR, "comtrade_hs85_world.csv")

    df_partners.to_csv(out_partners, index=False)
    df_world.to_csv(out_world, index=False)

    log.info(f"Partner-level saved: {out_partners} | {len(df_partners)} rows")
    log.info(f"World aggregate saved: {out_world} | {len(df_world)} rows")

    return df_partners, df_world


# LPI Cleaning

LPI_SCORE_COLS = [
    "lpi_overall",
    "lpi_customs",
    "lpi_infrastructure",
    "lpi_international_shipments",
    "lpi_logistics_competence",
    "lpi_tracking_tracing",
    "lpi_timeliness",
]


def expand_lpi_to_annual(
    group: pd.DataFrame, country_code: str, country_name: str
) -> pd.DataFrame:
    all_years = pd.DataFrame({"year": range(2015, 2025)})
    merged = all_years.merge(group, on="year", how="left")

    merged = merged.assign(country_code=country_code, country_name=country_name)

    merged[LPI_SCORE_COLS] = merged[LPI_SCORE_COLS].ffill().bfill()
    return merged


def clean_lpi() -> pd.DataFrame:
    path = os.path.join(RAW_DIR, f"worldbank_lpi_{TIMESTAMP}.csv")
    log.info(f"Loading: {path}")

    lpi = pd.read_csv(path)
    lpi = lpi.assign(
        country_name=lpi["country_name"].replace({"Korea, Rep.": "South Korea"}),
        year=lpi["year"].astype(int),
    )

    log.info(f"Raw LPI shape: {lpi.shape}")

    # Expand each country to annual frequency using a list comprehension
    expanded = pd.concat(
        [
            expand_lpi_to_annual(
                group.drop(columns=["country_code", "country_name"]),
                country_code=country_code,
                country_name=group["country_name"].iloc[0],
            )
            for country_code, group in lpi.groupby("country_code")
        ],
        ignore_index=True,
    )

    col_order = ["country_code", "country_name", "year"] + LPI_SCORE_COLS
    expanded = (
        expanded[col_order].sort_values(["country_code", "year"]).reset_index(drop=True)
    )

    log.info(f"LPI expanded shape: {expanded.shape}")

    out_path = os.path.join(PROCESSED_DIR, "lpi_annual_clean.csv")
    expanded.to_csv(out_path, index=False)
    log.info(f"Clean LPI saved: {out_path} | {len(expanded)} rows")

    return expanded


# Entry

if __name__ == "__main__":
    log.info("=== Starting cleaning pipeline ===")

    df_partners, df_world = clean_comtrade()
    df_lpi = clean_lpi()

    log.info("=== Cleaning complete ===")

    print("\n--- Comtrade sample ---")
    print(df_partners.head(3).to_string())

    print("\n--- LPI Indonesia ---")
    print(df_lpi.loc[df_lpi["country_code"] == "IDN"].to_string())
