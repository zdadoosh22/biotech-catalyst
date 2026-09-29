# 🧬 BioCatalyst: Biotech Catalyst & Clinical Trial Intelligence Engine

> **Autonomous Multi-Agent Diligence for Clinical Milestones & Capital Solvency**  
> *Bridging Molecular Biology, Trial Biostatistics, and Capital Market Asymmetry.*

---

## 🎯 Executive Overview

In biotechnology investing and clinical development, 90% of value creation or destruction occurs around **binary catalyst events**—Phase 2 signal readouts, Phase 3 pivotal data disclosures, and FDA PDUFA action dates (as famously exemplified by Moderna's mRNA-1273 and cancer neoantigen breakthroughs).

However, traditional market screeners fail because they treat biotech companies like standard software or industrial firms. **BioCatalyst** is an autonomous intelligence platform purpose-built around the realities of clinical development:
1. **Clinical Risk is Decoupled from Solvency Risk**: A drug can demonstrate 100% biological efficacy, but if the company's liquid cash runway expires 3 months *before* the Phase 3 data lock, existing shareholders will suffer massive dilution from a panic-induced secondary offering.
2. **Endpoint Rigor Dictates Commercial Reality**: Accelerated approval via unvalidated surrogate biomarkers carries immense regulatory vulnerability compared to hard clinical endpoints (Overall Survival).
3. **Evidence-First Multi-Agent Audit**: Rather than relying on generic LLM summaries, three specialized AI agents (Molecular Biologist, Clinical Biostatistician, Bio-Financial Strategist) rigorously audit each clinical asset and debate its risk/reward profile.

---

## 🏛️ System Architecture

```
                                  [ ClinicalTrials.gov v2 REST API ]
                                  [ NCBI PubMed E-Utilities ]
                                  [ yfinance / SEC 10-Q Cashflow ]
                                                  │
                                                  ▼
                                      [ Data Acquisition Layer ]
                             ┌────────────────────┼────────────────────┐
                             ▼                    ▼                    ▼
                   [ ClinicalTrialsClient ] [ MarketDataClient ] [ PubMedClient ]
                             └────────────────────┬────────────────────┘
                                                  │
                                                  ▼
                                      [ Local SQLite Database ]
                                                  │
                                                  ▼
                        ┌──────────────────────────────────────────────────┐
                        │      AI Multi-Agent Diligence Committee          │
                        │                                                  │
                        │  Agent 1: Dr. Elena Vance (Molecular Biologist)  │
                        │   • MoA Plausibility, Target Validation, Escape  │
                        │                                                  │
                        │  Agent 2: Dr. Marcus Thorne (Biostatistician)    │
                        │   • Sample Power, Blinding, Endpoint Hardness    │
                        │                                                  │
                        │  Agent 3: Alexander Vance, CFA (Financialist)    │
                        │   • Runway vs Readout Alignment, Dilution Radar  │
                        └─────────────────────────┬────────────────────────┘
                                                  │
                                                  ▼
                               [ Diligence Committee Consensus ]
                           • Composite Diligence Score (0 - 100)
                           • Verdict: STRONG_CONVICTION / ASYMMETRIC / AVOID
                           • Publication-Grade Markdown Dossier
                                                  │
                           ┌──────────────────────┴──────────────────────┐
                           ▼                                             ▼
                 [ Interactive CLI ]                          [ Streamlit Dashboard ]
```

---

## 🤖 The Multi-Agent Diligence Committee

| Agent | Identity & Role | Core Diligence Responsibilities |
| :--- | :--- | :--- |
| **Dr. Elena Vance** | Senior Molecular Biologist & Target Validation Specialist | • Audits biological target plausibility and mechanism of action (mRNA, LNP, ASO, Small Molecule, Monoclonal Antibody, etc.)<br>• Evaluates preclinical evidence strength and cellular escape/resistance pathways.<br>• Cross-references active target against PubMed literature. |
| **Dr. Marcus Thorne** | Regulatory Clinical Biostatistician & Methodologist | • Audits trial design rigor (Randomized, Double-Blind, Active-Controlled vs Single-Arm).<br>• Classifies endpoints: `HARD_CLINICAL` (Overall Survival) vs `SURROGATE_VALIDATED` (PFS/ORR) vs `SURROGATE_UNVALIDATED`.<br>• Flags statistical red flags, small sample sizes, and placebo effect vulnerabilities. |
| **Alexander Vance, CFA** | Biotech Capital Markets Strategist | • Computes net cash burn rate and months of liquid runway.<br>• Maps runway against expected trial readout dates.<br>• Detects the **Dilution Hazard Window** (when cash runs out before trial results).<br>• Quantifies binary exposure profile (Pure Binary Play vs Diversified Platform). |
| **Diligence Chairperson** | Consensus Synthesis Engine | • Synthesizes agent evaluations into a weighted composite score (0–100).<br>• Applies penalty deductions for methodological red flags.<br>• Issues Consensus Rating: `STRONG_CONVICTION`, `SPECULATIVE_ASYMMETRIC`, `NEUTRAL_WATCH`, or `HIGH_RISK_AVOID`. |

---

## 💰 The Financial Solvency Methodology

BioCatalyst computes cash burn and dilution risk using quarterly operating cash flows:

$$\text{Quarterly Burn Rate} = \frac{|\text{Operating Cash Flow}_{\text{TTM}}|}{4}$$

$$\text{Cash Runway (Months)} = \left(\frac{\text{Total Liquid Cash}}{\text{Quarterly Burn Rate}}\right) \times 3$$

### The Solvency Diagonal ($y = x$)
- **Above the Line ($y > x$)**: $\text{Runway} > \text{Months to Readout} + 6$. Company has a comfortable cash buffer. Management can afford to wait for data before negotiating partnerships or financing.
- **On the Line ($y \approx x$)**: $\text{Runway} \approx \text{Months to Readout}$. Tight liquidity. Management will likely tap an At-The-Market (ATM) offering or secondary 3–6 months *ahead* of the readout to protect the balance sheet.
- **Below the Line ($y < x$)**: $\text{Runway} < \text{Months to Readout}$. **CRITICAL DANGER ZONE**. The company will exhaust its cash reserves before the clinical data is unlocked. Dilution is mandatory and imminent.

---

## 🚀 Quickstart Guide

### 1. Requirements & Setup
BioCatalyst runs out-of-the-box on Python 3.10+ without any required paid subscriptions.

```bash
# Navigate to project directory
cd biotech-catalyst

# Activate your virtual environment
# Windows:
..\.venv\Scripts\Activate.ps1
# macOS/Linux:
source ../.venv/bin/activate

# Install dependencies (already installed in workspace)
pip install -r requirements.txt
```

### 2. Optional: Enable Google Gemini API
BioCatalyst includes an expert deterministic heuristic reasoning engine that runs 100% offline. To enable advanced Gemini LLM generation:
```bash
# Copy template and add your key
cp .env.example .env
# Edit .env and set:
# GEMINI_API_KEY="your_api_key_here"
```

---

## 💻 CLI Usage Guide

The BioCatalyst CLI provides instant terminal intelligence:

### 1. Scan ClinicalTrials.gov for Active Studies
```bash
# Scan by keyword
python cli.py scan --query "mRNA-4157" --limit 10

# Scan by condition
python cli.py scan --condition "Melanoma" --limit 10

# Scan by sponsor
python cli.py scan --sponsor "Moderna" --limit 5
```

### 2. Audit Balance Sheet Runway & Dilution Risk
```bash
# Audit specific ticker
python cli.py financials MRNA
python cli.py financials VKTX

# Audit all tracked sponsors in database
python cli.py financials
```

### 3. Convene the AI Diligence Committee
```bash
# Run 3-agent diligence on any NCT ID and export Markdown dossier
python cli.py audit NCT05933577 --export-md
python cli.py audit NCT07104500 --export-md
python cli.py audit NCT03313778 --export-md
```

### 4. Manage Catalyst Watchlist
```bash
# View active watchlist
python cli.py watchlist list

# Add ticker or clinical study
python cli.py watchlist add MRNA --alias "Moderna" --notes "mRNA cancer vaccine leader"
python cli.py watchlist add NCT05933577 --alias "mRNA-4157 Phase 3"

# Remove identifier
python cli.py watchlist remove MRNA
```

### 5. Export Data to CSV
```bash
python cli.py export-csv data/active_biotech_catalysts.csv
```

### 6. Launch Streamlit Interactive Web Dashboard
```bash
python cli.py serve
# OR directly:
streamlit run app.py
```

---

## 🖥️ Streamlit Interactive Web Dashboard

The web dashboard provides 5 specialized interfaces:
1. **📅 Catalyst Timeline & Calendar**: Gantt-style timeline visualization of Phase 1/2/3 trial readouts, expected catalyst quarters, and sponsor pipeline milestones.
2. **🎯 Dilution Radar & Runway**: Interactive scatter plot with the $y=x$ Solvency Threshold line. Instantly see which biotechs are safe vs which are in the mandatory dilution danger zone.
3. **🔬 AI Diligence Committee**: Select any study or type any NCT ID to run the live 3-Agent Committee. Review tabbed assessments from Dr. Elena Vance, Dr. Marcus Thorne, and Alexander Vance, CFA, with 1-click Markdown export.
4. **🔍 Live Trial Harvester**: Real-time querying against ClinicalTrials.gov API v2 with automatic ticker mapping and bulk SQLite ingestion.
5. **💼 Watchlist & Solvency**: Manage watched tickers and personal investment theses with 1-click presets for top biotechs.

---

## 🧪 Comprehensive Test Suite

BioCatalyst includes a full unit test suite covering models, database persistence, market data math, sponsor matching, and agent scoring:

```bash
# Run pytest
pytest tests/ -v
```

Output:
```
tests/test_agents.py::test_molecular_agent PASSED
tests/test_agents.py::test_biostat_agent PASSED
tests/test_agents.py::test_financial_agent PASSED
tests/test_agents.py::test_committee_consensus PASSED
tests/test_database.py::test_upsert_and_get_trial PASSED
tests/test_database.py::test_upsert_and_get_financials PASSED
tests/test_database.py::test_watchlist_operations PASSED
tests/test_exporter.py::test_markdown_export PASSED
tests/test_exporter.py::test_csv_export PASSED
tests/test_financials.py::test_runway_calculation_logic PASSED
tests/test_models.py::test_clinical_trial_model PASSED
tests/test_models.py::test_company_financials_model PASSED
tests/test_models.py::test_diligence_report_serialization PASSED
tests/test_sponsor_matcher.py::test_exact_sponsor_matching PASSED
tests/test_sponsor_matcher.py::test_suffix_cleaning_and_normalization PASSED
tests/test_sponsor_matcher.py::test_unknown_sponsor PASSED
==================== 16 passed in 0.71s ====================
```

---

## 📚 Real-World Case Studies Tested

1. **Moderna & Merck ($MRNA / $MRK - NCT05933577)**:
   - **Asset**: Intismeran Autogene (mRNA-4157 / V940) + Keytruda in High-Risk Melanoma.
   - **Verdict**: `STRONG_CONVICTION` (98.0 / 100).
   - **Biostat Score**: Randomized, active-controlled, Hard Clinical endpoint (Recurrence-Free Survival).
   - **Financial Buffer**: Mega-cap platform backing, cash flow positive/low dilution risk.

2. **Viking Therapeutics ($VKTX - NCT07104500)**:
   - **Asset**: VK2735 Dual GLP-1/GIP Receptor Agonist for Weight Management Phase 3.
   - **Verdict**: `STRONG_CONVICTION` (91.0 / 100).
   - **Financial Buffer**: `TIGHT` alignment. Cash runway (12.0 months) barely covers projected readout (10 months). High probability of capital raise into interim momentum.

---

*BioCatalyst Platform — Designed and engineered for evidence-first biotech intelligence.*
