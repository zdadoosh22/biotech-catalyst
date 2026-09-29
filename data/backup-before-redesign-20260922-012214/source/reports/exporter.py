"""Report Exporter: Generates publication-grade Markdown dossiers, JSON, and CSV data.
"""

import json
from typing import Optional, List
from pathlib import Path
import pandas as pd

from core.models import DiligenceReport, ClinicalTrial, CompanyFinancials


class ReportExporter:
    @staticmethod
    def export_to_markdown(
        report: DiligenceReport,
        trial: ClinicalTrial,
        financials: Optional[CompanyFinancials] = None
    ) -> str:
        ticker_badge = f"`${financials.ticker}`" if financials else "`Private / Unlisted`"
        mcap_str = f"${financials.market_cap:,.0f}" if financials and financials.market_cap else "N/A"
        cash_str = f"${financials.total_liquid_cash:,.0f}" if financials and financials.total_liquid_cash else "N/A"
        burn_str = f"${financials.quarterly_burn_rate:,.0f}/qtr" if financials and financials.quarterly_burn_rate else "N/A"
        runway_str = f"{financials.cash_runway_months:.1f} months" if financials and financials.cash_runway_months else "N/A"
        dilution_badge = f"`{financials.dilution_risk_level.value}`" if financials else "`N/A`"

        debt_str = f"${financials.short_term_debt:,.0f}" if financials and financials.short_term_debt else "None / Undisclosed"
        st_inv_str = f"${financials.short_term_investments:,.0f}" if financials and financials.short_term_investments else "N/A"

        verdict_color = "🟢" if report.consensus_verdict.value == "STRONG_CONVICTION" else (
            "🟡" if report.consensus_verdict.value == "SPECULATIVE_ASYMMETRIC" else (
                "🔵" if report.consensus_verdict.value == "NEUTRAL_WATCH" else "🔴"
            )
        )

        md = f"""# {verdict_color} BioCatalyst Intelligence Dossier: {report.nct_id}
**Asset Title**: {report.trial_title}  
**Lead Sponsor**: {report.sponsor} ({ticker_badge}) | **Generated**: {report.created_at[:10]}  
**Consensus Rating**: **{report.consensus_verdict.value}** | **Composite Score**: **{report.overall_score:.1f} / 100**

---

## Executive Summary
{report.executive_summary}

---

## 🔬 Asset & Protocol Specifications
| Metric | Specification |
| :--- | :--- |
| **NCT Identifier** | [{report.nct_id}](https://clinicaltrials.gov/study/{report.nct_id}) |
| **Study Status** | `{trial.status}` |
| **Development Phase** | {', '.join(trial.phases) if trial.phases else 'Unspecified'} |
| **Primary Completion** | {trial.primary_completion_date or 'Unspecified'} ({trial.primary_completion_date_type or 'UNKNOWN'}) |
| **Estimated Catalyst** | **{trial.estimated_catalyst_window or 'TBD'}** |
| **Target Enrollment** | {trial.enrollment or 'Unspecified'} patients |
| **Allocation / Design** | {trial.allocation or 'Unspecified'} / {trial.intervention_model or 'Unspecified'} |
| **Masking Protocol** | {trial.masking or 'Unspecified'} |
| **Interventions** | {', '.join([i.name for i in trial.interventions]) if trial.interventions else 'None listed'} |
| **Primary Indications**| {', '.join(trial.conditions) if trial.conditions else 'None listed'} |

---

## 💰 Capital Solvency & Dilution Risk Radar
| Financial Metric | Balance Sheet Status |
| :--- | :--- |
| **Stock Ticker** | {ticker_badge} |
| **Market Capitalization** | {mcap_str} |
| **Total Liquid Cash Reserves** | {cash_str} |
| **Short-Term Investments (Treasuries)** | {st_inv_str} |
| **Short-Term Debt (<1yr Maturity)** | {debt_str} |
| **Quarterly Cash Burn** | {burn_str} |
| **Cash Runway** | **{runway_str}** |
| **Dilution Risk Level** | {dilution_badge} |
| **Runway Alignment** | `{report.financial_audit.runway_vs_readout_alignment}` |
| **Readout Horizon (P10 / P50 / P90)** | **{f'{report.financial_audit.p10_readout_months:.1f} / {report.financial_audit.p50_readout_months:.1f} / {report.financial_audit.p90_readout_months:.1f} mos' if report.financial_audit.p50_readout_months is not None else 'N/A'}** |
| **Pre-Readout Dilution Probability** | **{f'{report.financial_audit.dilution_probability_before_readout * 100:.0f}%' if report.financial_audit.dilution_probability_before_readout is not None else 'N/A'}** |
| **Projected Dilution Window** | {report.financial_audit.projected_dilution_window or 'N/A'} |

---

## 🧬 1. Molecular Biology & MoA Audit
*Conducted by Dr. Elena Vance (Target Validation Specialist)*

- **Target Identifier**: `{report.molecular_analysis.target_name}`
- **Drug Modality**: `{report.molecular_analysis.modality}`
- **Biological Plausibility**: `{report.molecular_analysis.biological_plausibility}`
- **Target Validation Evaluation**:
  > {report.molecular_analysis.target_validation_summary}
- **Preclinical Evidence Strength**: `{report.molecular_analysis.preclinical_evidence_strength}`
- **Biological Resistance & Escape Risks**:
  > {report.molecular_analysis.resistance_risk_notes}

---

## 📊 2. Clinical Biostatistics & Trial Methodology Audit
*Conducted by Dr. Marcus Thorne (Regulatory Biostatistician)*

- **Design Rigor Score**: `{report.biostat_audit.trial_design_rigor}`
- **Endpoint Classification**: `{report.biostat_audit.endpoint_quality}`
- **Primary Endpoint Rigor Analysis**:
  > {report.biostat_audit.endpoint_analysis}
- **Statistical Power & Sample Size**:
  > {report.biostat_audit.power_and_sample_size_assessment}
- **Control Arm & Comparator Rigor**:
  > {report.biostat_audit.control_arm_critique}
- **Blinding Protocol & Bias Control**:
  > {report.biostat_audit.blinding_rigor}
"""

        if report.biostat_audit.red_flags:
            md += "\n### ⚠️ Critical Methodology Red Flags Flagged:\n"
            for rf in report.biostat_audit.red_flags:
                md += f"- ❌ **{rf}**\n"

        md += f"""
---

## 📈 3. Bio-Financial Risk & Asymmetry Audit
*Conducted by Alexander Vance, CFA (Biotech Capital Markets Strategist)*

- **Binary Exposure Profile**: `{report.financial_audit.binary_risk_exposure}`
- **Asymmetry Risk/Reward**: `{report.financial_audit.asymmetry_ratio}`
- **Commercial Market Opportunity**:
  > {report.financial_audit.commercial_market_opportunity}
- **Dilution Timing Risk Analysis**:
  > {report.financial_audit.projected_dilution_window or 'No immediate financing hazard identified.'}
"""
        if report.financial_audit.slippage_risk_factors:
            md += "\n- **Timeline & Accrual Slippage Drivers**:\n"
            for srf in report.financial_audit.slippage_risk_factors:
                md += f"  - ⏳ {srf}\n"

        md += f"""
---

## 🎯 Key Catalyst Milestones & Critical Risks

### 🚀 Catalysts to Watch
"""
        for cat in report.key_catalysts:
            md += f"- **[CATALYST]** {cat}\n"

        md += "\n### ⚠️ Critical Downside Risks\n"
        for risk in report.critical_risks:
            md += f"- **[RISK]** {risk}\n"

        # Add data freshness warning if present
        if financials and financials.data_freshness_warning:
            md += f"\n> ⚠️ **DATA STALENESS WARNING**: {financials.data_freshness_warning}\n"

        # Scoring audit trail
        if report.scoring_audit_trail:
            md += "\n---\n\n## ⚖️ Composite Score Audit Trail\n"
            md += f"*Final Composite Score: **{report.overall_score:.1f} / 100** (Agent confidence-weighted)*\n\n"
            for step in report.scoring_audit_trail:
                if "PENALTY" in step or "MULTIPLICATIVE" in step:
                    md += f"- 🔴 {step}\n"
                elif step.startswith("+"):
                    md += f"- 🟢 {step}\n"
                elif "Confidence weighting" in step:
                    md += f"- 🔵 {step}\n"
                else:
                    md += f"- ⚪ {step}\n"

        # Agent confidence disclosure
        md += "\n---\n\n## 📋 Agent Confidence Disclosure\n"
        md += f"| Agent | Confidence Score |\n"
        md += f"| :--- | :--- |\n"
        md += f"| Dr. Elena Vance (Molecular) | `{report.molecular_analysis.confidence_score:.2f}` |\n"
        md += f"| Dr. Marcus Thorne (Biostat) | `{report.biostat_audit.confidence_score:.2f}` |\n"
        md += f"| Alexander Vance, CFA (Financial) | `{report.financial_audit.confidence_score:.2f}` |\n"

        md += "\n---\n*BioCatalyst Platform Diligence Engine — Evidence-backed scientific & market synthesis.*\n"
        return md

    @staticmethod
    def export_trials_to_csv(trials: List[ClinicalTrial], filepath: str) -> None:
        records = []
        for t in trials:
            records.append({
                "NCT ID": t.nct_id,
                "Title": t.title,
                "Sponsor": t.sponsor_name,
                "Ticker": t.matched_ticker or "",
                "Phases": ", ".join(t.phases),
                "Status": t.status,
                "Conditions": "; ".join(t.conditions),
                "Primary Completion": t.primary_completion_date or "",
                "Catalyst Window": t.estimated_catalyst_window or "",
                "Enrollment": t.enrollment or 0
            })
        df = pd.DataFrame(records)
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False)
