# Indonesia Electrical Machinery Supply Chain Analytics
## HS Chapter 85 | 2015-2024 | UN Comtrade & World Bank LPI

> An end-to-end supply chain analytics project analyzing Indonesia's trade performance in electrical machinery and equipment across 11 key trading partners over a decade. Built with Python, Tableau, and open government data.

---

## Project Overview

This project investigates two interconnected supply chain problems:

**Track A - Demand Volatility:** How has demand for electrical machinery fluctuated over time, which partners drive the most volatility, and where did the COVID-19 shock hit hardest?

**Track B - Logistics Bottleneck:** Does a trading partner's logistics performance correlate with bilateral trade volume, and which logistics dimensions most constrain Indonesia's supply chain?

The analysis covers January 2015 through December 2024, spanning the pre-pandemic period, COVID-19 shock (2019-2021), and post-pandemic recovery including the 2024 AI hardware demand surge.

---

## Key Findings

1. Indonesia runs a structural trade deficit with China of **-$14.22B in 2024**, up 137.7% from -$5.98B in 2015. Every single year shows a negative balance with no reversal.

2. Indonesia is a **net exporter to the United States**, averaging $1.62B annual surplus - confirming competitive manufacturing capability in specific HS85 segments.

3. The supply chain showed **pre-shock fragility in 2019**, before COVID arrived, driven by US-China trade war escalation. Anomalies appeared across 6 partners in 2019.

4. Indonesia's **LPI ranking fell from 46th to 61st** between 2018 and 2022 while all ASEAN peers improved. Customs efficiency at 2.8/5.0 and 6-7 day average clearance times are the critical bottlenecks.

5. Indonesia's imports of electronic integrated circuits **(HS 8542) grew 120.87% year-on-year** in late 2024, driven by AI hardware demand - a structural demand shift, not a temporary spike.

---

## Project Structure

```
Comtrade-Performance-Analytics/
├── data/
│   ├── raw/                          # Raw API outputs (not committed to git)
│   │   ├── comtrade_hs85_all_*.csv   # UN Comtrade master file
│   │   ├── comtrade_hs85_exports_*.csv
│   │   ├── comtrade_hs85_imports_*.csv
│   │   ├── worldbank_lpi_*.csv       # World Bank LPI raw data
│   │   └── extraction.log            # Pipeline execution log
│   └── processed/                    # Analysis-ready datasets
│       ├── comtrade_hs85_clean.csv   # Cleaned partner-level trade data
│       ├── comtrade_hs85_world.csv   # World aggregate trade data
│       ├── lpi_annual_clean.csv      # LPI scores expanded to annual
│       ├── comtrade_features.csv     # Feature-engineered trade data
│       ├── trade_balance.csv         # Annual trade balance per partner
│       └── lpi_trade_merged.csv      # LPI scores merged with trade data
├── notebooks/
│   └── analysis.ipynb                # Full analysis with visualizations
├── scripts/
│   ├── 01_extract.py                 # Data extraction from APIs
│   ├── 01b_resume.py                 # Resume script after crash
│   ├── 02_clean.py                   # Data cleaning pipeline
│   └── 03_features.py                # Feature engineering
├── dashboard/
│   └── Indonesia_HS85_Supply_Chain_Analytics.twbx
├── docs/
│   └── technical_report.docx         # Full technical report
└── README.md
```

---

## Data Sources

| Source | Description | Access | Coverage |
|--------|-------------|--------|----------|
| UN Comtrade API | Monthly merchandise trade statistics | Free with registration at comtradeplus.un.org | 2015-2024, monthly |
| World Bank LPI | Logistics Performance Index scores | Free at data.worldbank.org | 2007-2022, periodic |

**Trading partners covered:** China, Japan, Singapore, United States, Germany, Malaysia, South Korea, Vietnam, Thailand, Philippines, Taiwan

**Commodity scope:** HS Chapter 85 - Electrical machinery and equipment, sound recorders, television equipment, and parts thereof

---

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/Comtrade-Performance-Analytics.git
cd Comtrade-Performance-Analytics
```

### 2. Set up environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install comtradeapicall pandas numpy requests python-dotenv matplotlib seaborn scipy
```

### 3. Configure API key

Create a `.env` file in the project root:

```
COMTRADE_API_KEY=your_key_here
```

Register for a free API key at: `https://comtradedeveloper.un.org`

### 4. Run the pipeline in order

```bash
python scripts/01_extract.py     # ~15 minutes, fetches 10 years of data
python scripts/02_clean.py       # ~30 seconds
python scripts/03_features.py    # ~30 seconds
```

### 5. Open the notebook

```bash
jupyter notebook notebooks/analysis.ipynb
```

Run all cells top to bottom. All charts save automatically to `data/processed/`.

### 6. Open the Tableau dashboard

Open `dashboard/Indonesia_HS85_Supply_Chain_Analytics.twbx` in Tableau Desktop or Tableau Public.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Data extraction, cleaning, feature engineering |
| pandas | Data manipulation and transformation |
| numpy | Numerical operations |
| requests | World Bank API calls |
| comtradeapicall | UN Comtrade API wrapper |
| python-dotenv | Secure API key management |
| matplotlib + seaborn | Exploratory and publication charts |
| scipy | Statistical analysis and correlation |
| Jupyter Notebook | Analysis narrative and visualization |
| Tableau Desktop | Interactive dashboard |
| GitHub | Version control and portfolio hosting |

---

## Limitations

- Analysis covers 11 trading partners representing approximately 50% of Indonesia's total HS85 trade. Vietnam ($12.3B), Thailand ($10.8B), and Hong Kong ($9.6B) are included; further partners remain outside scope.
- LPI data is published every 2-4 years. Annual series are forward-filled between publication years, introducing measurement error in interim years.
- Anomaly detection uses a descriptive 2-standard-deviation rolling window approach. Formal structural break testing using ADF unit root tests and Error Correction Models is recommended for classifying permanent vs temporary demand shifts.
- Data operates at HS Chapter level (2-digit aggregation). Weight data is not reported at this level. Sub-category dynamics such as the HS 8542 semiconductor surge require 6-digit disaggregation.
- Philippines 2021 YoY growth of 471% reflects a base effect from COVID-19 trade collapse in 2020, compounded by mirror data discrepancy between CIF and FOB valuation methods.

---

## References

- UN Comtrade Database: https://comtradeplus.un.org
- World Bank Logistics Performance Index: https://lpi.worldbank.org
- World Bank LPI 2023 Report: Connecting to Compete 2023
- Making Indonesia 4.0 Roadmap: Ministry of Industry, Republic of Indonesia
- ASCM Supply Chain Dictionary
- McKinsey Global Institute: Supply Chain Resilience Reports

---

## Author

**Farand** | Data Science Student, Telkom University
