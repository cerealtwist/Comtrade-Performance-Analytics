"""
FEATURE ENGINEERING from Comtrade and LPI data.
Outputs feature-enriched datasets to data/processed/.

Outputs:
- comtrade_features.csv   : monthly trade data with derived indicators
- trade_balance.csv       : annual trade balance per partner
- lpi_trade_merged.csv    : annual trade value merged with LPI scores
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
        logging.FileHandler("data/processed/features.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

PROCESSED_DIR = "data/processed"


# Load Clean Data


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    trade = pd.read_csv(
        os.path.join(PROCESSED_DIR, "comtrade_hs85_clean.csv"), parse_dates=["date"]
    )
    lpi = pd.read_csv(os.path.join(PROCESSED_DIR, "lpi_annual_clean.csv"))
    log.info(f"Loaded trade data: {trade.shape}")
    log.info(f"Loaded LPI data: {lpi.shape}")
    return trade, lpi


# Time Series Features


def build_time_series_features(trade: pd.DataFrame) -> pd.DataFrame:
    """
    For each partner-flow combination, compute:
    - MoM growth rate
    - YoY growth rate
    - Rolling 3-month average
    - Rolling 12-month average
    - Rolling 12-month standard deviation (volatility)
    - Anomaly flag (value > 2 std from rolling mean)
    """
    log.info("Building time series features...")

    # Sort before any rolling or shift operations
    trade = trade.sort_values(["partner_iso", "flow_label", "date"]).reset_index(
        drop=True
    )

    # Group key for all rolling operations
    group_keys = ["partner_iso", "flow_label"]

    # Month-over-month growth rate
    trade = trade.assign(
        mom_growth=trade.groupby(group_keys)["primary_value_usd"].pct_change(periods=1)
    )

    # Year-over-year growth rate (lag 12 months)
    trade = trade.assign(
        yoy_growth=trade.groupby(group_keys)["primary_value_usd"].pct_change(periods=12)
    )

    # Rolling 3-month average
    trade = trade.assign(
        rolling_3m_avg=trade.groupby(group_keys)["primary_value_usd"].transform(
            lambda s: s.rolling(3, min_periods=1).mean()
        )
    )

    # Rolling 12-month average
    trade = trade.assign(
        rolling_12m_avg=trade.groupby(group_keys)["primary_value_usd"].transform(
            lambda s: s.rolling(12, min_periods=6).mean()
        )
    )

    # Rolling 12-month standard deviation (volatility proxy)
    trade = trade.assign(
        rolling_12m_std=trade.groupby(group_keys)["primary_value_usd"].transform(
            lambda s: s.rolling(12, min_periods=6).std()
        )
    )

    # Anomaly flag: value deviates more than 2 std from rolling mean
    trade = trade.assign(
        is_anomaly=(
            (trade["primary_value_usd"] - trade["rolling_12m_avg"]).abs()
            > 2 * trade["rolling_12m_std"]
        )
    )

    anomaly_count = trade["is_anomaly"].sum()
    log.info(f"Anomalies flagged: {anomaly_count}")

    return trade


# Trade Balance


def build_trade_balance(trade: pd.DataFrame) -> pd.DataFrame:
    """
    Annual trade balance per partner:
    balance = total exports - total imports (USD)
    Positive = net exporter to that partner
    Negative = net importer from that partner
    """
    log.info("Building trade balance...")

    annual = (
        trade.groupby(["year", "partner_iso", "partner_name", "flow_label"])[
            "primary_value_usd"
        ]
        .sum()
        .reset_index()
    )

    # Pivot so exports and imports are columns
    balance = annual.pivot_table(
        index=["year", "partner_iso", "partner_name"],
        columns="flow_label",
        values="primary_value_usd",
    ).reset_index()

    balance.columns.name = None

    # Rename for clarity
    balance = balance.rename(
        columns={"exports": "total_exports_usd", "imports": "total_imports_usd"}
    )

    # Fill missing with 0 before computing balance
    balance = balance.assign(
        total_exports_usd=balance["total_exports_usd"].fillna(0),
        total_imports_usd=balance["total_imports_usd"].fillna(0),
    )

    balance = balance.assign(
        trade_balance_usd=balance["total_exports_usd"] - balance["total_imports_usd"],
        total_trade_usd=balance["total_exports_usd"] + balance["total_imports_usd"],
    )

    balance = balance.sort_values(["partner_iso", "year"]).reset_index(drop=True)
    log.info(f"Trade balance table shape: {balance.shape}")

    return balance


# LPI + Trade Merge

LPI_PARTNER_MAP = {
    "CHN": "CHN",
    "JPN": "JPN",
    "SGP": "SGP",
    "USA": "USA",
    "DEU": "DEU",
    "MYS": "MYS",
    "KOR": "KOR",
}

# World Bank ISO3 codes for partners
WB_TO_COMTRADE = {
    "CHN": "CHN",
    "JPN": "JPN",
    "SGP": "SGP",
    "USA": "USA",
    "DEU": "DEU",
    "MYS": "MYS",
    "KOR": "KOR",
}


def build_lpi_trade_merged(trade: pd.DataFrame, lpi: pd.DataFrame) -> pd.DataFrame:
    """
    Merge annual trade totals w/ LPI scores per partner per year.
    Excludes World aggregate since LPI is country-level.
    Used for bottleneck correlation analysis.
    """
    log.info("Building LPI-trade merged dataset...")

    # Annual trade totals per partner and flow
    annual_trade = (
        trade.loc[trade["partner_iso"] != "W00"]
        .groupby(["year", "partner_iso", "partner_name", "flow_label"])[
            "primary_value_usd"
        ]
        .sum()
        .reset_index()
        .rename(columns={"primary_value_usd": "annual_trade_value_usd"})
    )

    # LPI uses same ISO3 codes as Comtrade for partners
    lpi_filtered = lpi.loc[lpi["country_code"] != "IDN"].copy()

    merged = annual_trade.merge(
        lpi_filtered,
        left_on=["year", "partner_iso"],
        right_on=["year", "country_code"],
        how="left",
    )

    # Drop redundant country columns from LPI
    merged = merged.drop(columns=["country_code"])

    missing_lpi = merged["lpi_overall"].isnull().sum()
    log.info(f"Rows with missing LPI after merge: {missing_lpi}")
    log.info(f"LPI-trade merged shape: {merged.shape}")

    return merged


# Save All Outputs


def save_outputs(
    trade_features: pd.DataFrame, trade_balance: pd.DataFrame, lpi_merged: pd.DataFrame
) -> None:

    paths = {
        "comtrade_features.csv": trade_features,
        "trade_balance.csv": trade_balance,
        "lpi_trade_merged.csv": lpi_merged,
    }

    for filename, df in paths.items():
        out = os.path.join(PROCESSED_DIR, filename)
        df.to_csv(out, index=False)
        log.info(f"Saved: {out} | {len(df)} rows")


# Entry

if __name__ == "__main__":
    log.info("=== Starting feature engineering ===")

    trade, lpi = load_data()
    trade_features = build_time_series_features(trade)
    trade_balance = build_trade_balance(trade)
    lpi_merged = build_lpi_trade_merged(trade, lpi)

    save_outputs(trade_features, trade_balance, lpi_merged)

    log.info("=== Feature engineering complete ===")

    print("\n--- Features sample (China exports) ---")
    sample = trade_features.loc[
        (trade_features["partner_iso"] == "CHN")
        & (trade_features["flow_label"] == "exports")
    ][
        [
            "date",
            "primary_value_usd",
            "mom_growth",
            "yoy_growth",
            "rolling_12m_avg",
            "is_anomaly",
        ]
    ].head(10)
    print(sample.to_string())

    print("\n--- Trade balance sample ---")
    print(trade_balance.head(10).to_string())

    print("\n--- LPI merged sample ---")
    print(lpi_merged.head(5).to_string())
