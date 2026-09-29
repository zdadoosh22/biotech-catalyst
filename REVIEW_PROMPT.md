# BioCatalyst Intelligence Engine: Architectural & Code Review Prompt

**Instructions for the Reviewing AI**:
You are a Staff-Level Software Engineer and Biotech Quantitative Analyst. You have been asked to conduct a comprehensive structural, architectural, and financial methodology review of the **BioCatalyst** project.

The codebase is located at: `C:\Users\aidan\PycharmProjects\WelcomeScreen\biotech-catalyst`

## 1. Project Context
BioCatalyst is a local, multi-agent intelligence platform designed to evaluate biotech clinical catalyst events. It decouples **clinical efficacy risk** (e.g., will the drug work?) from **balance sheet solvency risk** (e.g., will the company run out of cash and dilute shareholders before the trial data is published?).

It features:
- **Data Acquisition**: Live fetching from ClinicalTrials.gov API v2, PubMed E-Utilities, and yfinance.
- **Local Storage**: A persistent SQLite database using Pydantic models.
- **AI Multi-Agent Committee**: 
  - *Dr. Elena Vance*: Evaluates Molecular mechanism of action (MoA) and target validation.
  - *Dr. Marcus Thorne*: Evaluates biostatistical rigor, sample sizing, and endpoint quality (hard clinical vs surrogate).
  - *Alexander Vance, CFA*: Evaluates cash runway, quarterly burn rate, and computes the "Dilution Hazard Window".
- **Interfaces**: A rich terminal CLI (`cli.py`) and an interactive Streamlit UI (`app.py`).

## 2. Review Objectives
Please analyze the project files (specifically the `core/`, `clients/`, `agents/`, `tests/`, and interface scripts) and provide a detailed evaluation covering the following domains:

### A. Architectural & Software Engineering Review
- Evaluate the separation of concerns between the data acquisition clients, the Pydantic data models, the SQLite database manager, and the agent logic.
- Assess the robustness of the fallback mechanism in `agents/base_agent.py` (which falls back to a deterministic heuristic engine if the Gemini API is unavailable or fails).
- Review the test suite (`tests/` directory). Are the tests comprehensive? Do they adequately mock or isolate network calls?

### B. Biotech & Financial Methodology Evaluation
- Review the logic in `clients/market_data.py` and `agents/financial_agent.py`. Is the calculation for Quarterly Burn Rate and Cash Runway logically sound for clinical-stage pre-revenue biotechs?
- Evaluate the "Solvency Diagonal" concept (comparing months of cash runway vs. expected months until clinical trial primary completion). Is the classification of `SAFE_BUFFER`, `TIGHT`, and `DILUTION_IMMINENT` financially rigorous?
- Review the trial protocol parser in `clients/clinical_trials.py`. Does it accurately extract and interpret Catalyst Windows (e.g., Q1 2027) from the ClinicalTrials.gov version 2 API JSON structure?

### C. Multi-Agent System Design
- Evaluate the `DiligenceCommittee` synthesis logic in `agents/committee.py`. How well does the composite scoring system (0-100) weight the molecular, biostatistical, and financial factors?
- Are the penalty deductions for biostatistical "red flags" and impending dilution risks appropriately scaled?

## 3. Requested Output Format
Please structure your evaluation as follows:
1. **Executive Summary**: A high-level assessment of the platform's viability and code quality.
2. **Strengths & Innovations**: What architectural or methodological choices stand out as exceptional?
3. **Vulnerabilities & Edge Cases**: Identify edge cases (e.g., how the system handles giant conglomerates like Pfizer vs pre-revenue microcaps, or handling of complex adaptive trial designs).
4. **Actionable Recommendations**: Provide specific, prioritized recommendations for improving the code robustness, error handling, or financial calculations (e.g., integrating SEC EDGAR directly for higher fidelity cash burn analysis).

Begin your review by analyzing the codebase structure and parsing the module interactions.