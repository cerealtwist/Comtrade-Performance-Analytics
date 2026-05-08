"""
01_extract.py
-------------
Extracts Indonesia HS Chapter 85 trade data from UN Comtrade API
and World Bank LPI data for selected trading partners.

Data is saved as timestamped CSVs in data/raw/.
"""

import os
import time
import logging
import requests
import pandas as pd
import comtradeapicall
from datetime import datetime
from dotenv import load_dotenv

# Setup

load_dotenv()
API_KEY = os.getenv("COMTRADE_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/raw/extraction.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

os.makedirs("data/raw", exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d")

# Config

INDONESIA_CODE = "360"       # UN Comtrade reporter code for Indonesia
HS_CHAPTER     = "85"        # Electrical machinery and equipment
START_YEAR     = 2015
END_YEAR       = 2024

# Key trading partners: China, Japan, Singapore, USA, Germany, Malaysia, South Korea
PARTNER_CODES = {
    "156": "China",
    "392": "Japan",
    "702": "Singapore",
    "840": "USA",
    "276": "Germany",
    "458": "Malaysia",
    "410": "South Korea"
}

# World Bank LPI indicator codes
LPI_INDICATORS = {
    "LP.LPI.OVRL.XQ": "lpi_overall",
    "LP.LPI.CUST.XQ": "lpi_customs",
    "LP.LPI.INFR.XQ": "lpi_infrastructure",
    "LP.LPI.ITRN.XQ": "lpi_international_shipments",
    "LP.LPI.LOGS.XQ": "lpi_logistics_competence",
    "LP.LPI.TRAC.XQ": "lpi_tracking_tracing",
    "LP.LPI.TIME.XQ": "lpi_timeliness"
}

# World Bank country codes for our partners + Indonesia
WB_COUNTRIES = "IDN;CHN;JPN;SGP;USA;DEU;MYS;KOR"


# Comtrade Extraction

def build_periods(start_year: int, end_year: int) -> list[str]:
    """
    Build list of monthly period strings (YYYYMM) for the given year range.
    Comtrade monthly queries accept up to 12 months per call on the free tier.
    (Batching by year to stay inside limites)
    """
    periods = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            periods.append(f"{year}{month:02d}")
    return periods


def fetch_comtrade_year(year: int, flow: str) -> pd.DataFrame:
    """
    Fetch one year of monthly HS85 trade data for Indonesia.
    flow: 'X' for exports, 'M' for imports
    """
    period_str = ",".join([f"{year}{m:02d}" for m in range(1, 13)])

    log.info(f"Fetching Comtrade | year={year} | flow={flow}")

    df = comtradeapicall.previewFinalData(
        typeCode='C',
        freqCode='M',
        clCode='HS',
        period=period_str,
        reporterCode=INDONESIA_CODE,
        cmdCode=HS_CHAPTER,
        flowCode=flow,
        partnerCode=None,       # all partners
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=100000,
        format_output='JSON',
        aggregateBy=None,
        breakdownMode='classic',
        countOnly=None,
        includeDesc=True,
        subscription_key=API_KEY
    )

    if df is None or df.empty:
        log.warning(f"No data returned | year={year} | flow={flow}")
        return pd.DataFrame()

    log.info(f"Fetched {len(df)} records | year={year} | flow={flow}")
    return df


def extract_comtrade():
    """
    Loop through years and both flow directions.
    Save each year as a separate CSV, then combine into one master file.
    """
    all_frames = []

    for flow in ["X", "M"]:
        flow_label = "exports" if flow == "X" else "imports"

        for year in range(START_YEAR, END_YEAR + 1):
            try:
                df = fetch_comtrade_year(year, flow)

                if df.empty:
                    continue

                df["flow_label"] = flow_label

                # Save individual year file
                filename = f"data/raw/comtrade_hs85_{flow_label}_{year}_{TIMESTAMP}.csv"
                df.to_csv(filename, index=False)
                log.info(f"Saved: {filename}")

                all_frames.append(df)

                # Respect free tier rate limits - 1 second between calls
                time.sleep(1)

            except Exception as e:
                log.error(f"Failed | year={year} | flow={flow} | error={e}")
                continue

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        out_path = f"data/raw/comtrade_hs85_all_{TIMESTAMP}.csv"
        combined.to_csv(out_path, index=False)
        log.info(f"Combined Comtrade data saved: {out_path} | {len(combined)} total records")
    else:
        log.error("No Comtrade data was collected. Check API key and connection.")


# World Bank LPI Extraction

def fetch_lpi():
    """
    Fetch all LPI sub-indicators for Indonesia and key trading partners
    from the World Bank API. Covers all available years.
    """
    log.info("Fetching World Bank LPI data...")

    indicators_str = ";".join(LPI_INDICATORS.keys())
    url = (
        f"https://api.worldbank.org/v2/country/{WB_COUNTRIES}"
        f"/indicator/{indicators_str}"
        f"?format=json&per_page=1000&mrv=10"
    )

    all_frames = []

    for code, label in LPI_INDICATORS.items():
        indicator_url = (
            f"https://api.worldbank.org/v2/country/{WB_COUNTRIES}"
            f"/indicator/{code}"
            f"?format=json&per_page=1000"
        )

        try:
            response = requests.get(indicator_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if len(data) < 2 or not data[1]:
                log.warning(f"No data for indicator: {code}")
                continue

            records = []
            for entry in data[1]:
                records.append({
                    "country_code": entry["countryiso3code"],
                    "country_name": entry["country"]["value"],
                    "year":         entry["date"],
                    "indicator":    label,
                    "value":        entry["value"]
                })

            df = pd.DataFrame(records)
            all_frames.append(df)
            log.info(f"Fetched LPI indicator: {label} | {len(df)} records")

            time.sleep(0.5)

        except Exception as e:
            log.error(f"Failed to fetch LPI indicator {code}: {e}")
            continue

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)

        # Pivot so each indicator becomes a column
        pivoted = combined.pivot_table(
            index=["country_code", "country_name", "year"],
            columns="indicator",
            values="value"
        ).reset_index()
        pivoted.columns.name = None

        out_path = f"data/raw/worldbank_lpi_{TIMESTAMP}.csv"
        pivoted.to_csv(out_path, index=False)
        log.info(f"LPI data saved: {out_path} | {len(pivoted)} rows")
    else:
        log.error("No LPI data collected.")


# Entry

if __name__ == "__main__":
    log.info("=== Starting data extraction ===")
    log.info(f"Timestamp: {TIMESTAMP}")

    log.info("--- Comtrade extraction ---")
    extract_comtrade()

    log.info("--- World Bank LPI extraction ---")
    fetch_lpi()

    log.info("=== Extraction complete ===")
