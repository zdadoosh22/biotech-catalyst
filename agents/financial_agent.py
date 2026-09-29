"""Bio-Financial Solvency & Catalyst Asymmetry Scorer Agent.

Assesses cash runway alignment against trial readout dates, dilution hazard windows,
and binary vs diversified portfolio risk profiles.
"""

import re
import math
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from agents.base_agent import BaseAgent
from core.models import ClinicalTrial, CompanyFinancials, FinancialCatalystAudit, DilutionRiskLevel
from core.config import KNOWN_BIOTECH_REGISTRY


class FinancialCatalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Alexander Vance, CFA",
            role="Managing Partner & Biotech Capital Markets Strategist"
        )

    def analyze(self, trial: ClinicalTrial, financials: Optional[CompanyFinancials]) -> FinancialCatalystAudit:
        """Audits balance sheet runway, dilution risk, and asymmetric payoff profile."""
        # 1. Attempt Gemini Generation
        prompt = self._build_prompt(trial, financials)
        llm_result = self.call_gemini(prompt)

        if llm_result:
            try:
                return FinancialCatalystAudit(
                    runway_vs_readout_alignment=llm_result.get("runway_vs_readout_alignment", "TIGHT"),
                    binary_risk_exposure=llm_result.get("binary_risk_exposure", "MODERATE_PIPELINE_BUFFER"),
                    commercial_market_opportunity=llm_result.get("commercial_market_opportunity", ""),
                    asymmetry_ratio=llm_result.get("asymmetry_ratio", "BALANCED"),
                    projected_dilution_window=llm_result.get("projected_dilution_window"),
                    confidence_score=float(llm_result.get("confidence_score", 0.88))
                )
            except Exception:
                pass

        # 2. Fallback to Quantitative Financial Auditor
        return self._heuristic_analysis(trial, financials)

    def _build_prompt(self, trial: ClinicalTrial, financials: Optional[CompanyFinancials]) -> str:
        fin_info = "Financial data unavailable (Private Sponsor or Non-Public Institution)."
        if financials:
            fin_info = f"""
            Ticker: {financials.ticker} ({financials.company_name})
            Market Cap: ${financials.market_cap:,.0f} USD if financials.market_cap else 'N/A'
            Liquid Cash: ${financials.total_liquid_cash:,.0f} USD if financials.total_liquid_cash else 'N/A'
            Quarterly Burn Rate: ${financials.quarterly_burn_rate:,.0f} USD if financials.quarterly_burn_rate else 'N/A'
            Cash Runway: {financials.cash_runway_months} months
            Dilution Risk Rating: {financials.dilution_risk_level.value}
            """

        return f"""
        You are {self.name}, {self.role}.
        Analyze the capital structure and catalyst asymmetry of this clinical milestone:

        Trial ID: {trial.nct_id}
        Phase: {", ".join(trial.phases)}
        Estimated Catalyst Window: {trial.estimated_catalyst_window or 'Unknown'}
        Primary Completion Date: {trial.primary_completion_date or 'Unknown'}
        Company Financials:
        {fin_info}

        Note: Standard clinical practice dictates a 1-3 month lag between Primary Completion and Topline Data Readout.
        Account for this when mapping cash runway vs readout timing.

        Respond in strict JSON with the following schema:
        {{
            "runway_vs_readout_alignment": "SAFE_BUFFER" | "TIGHT" | "DILUTION_IMMINENT",
            "binary_risk_exposure": "PURE_BINARY_PLAY" | "MODERATE_PIPELINE_BUFFER" | "HIGHLY_DIVERSIFIED",
            "commercial_market_opportunity": "Addressable market analysis (e.g. Multi-billion blockbuster vs niche orphan)",
            "asymmetry_ratio": "FAVORABLE" | "BALANCED" | "UNFAVORABLE",
            "projected_dilution_window": "Anticipated secondary offering timing (e.g. Pre-data raise vs Post-data spike)",
            "confidence_score": 0.88
        }}
        """

    @staticmethod
    def _normal_cdf(x: float, mean: float, std: float) -> float:
        """Calculates standard normal cumulative distribution function."""
        if std <= 0.001:
            return 1.0 if x >= mean else 0.0
        z = (x - mean) / std
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

    def _heuristic_analysis(self, trial: ClinicalTrial, financials: Optional[CompanyFinancials]) -> FinancialCatalystAudit:
        status_upper = (trial.status or "UNKNOWN").upper()
        slippage_risk_factors: List[str] = []

        # Baseline empirical slippage parameters by Phase
        is_phase3 = any("3" in p for p in trial.phases)
        is_phase2 = any("2" in p for p in trial.phases)
        is_phase1 = any("1" in p for p in trial.phases)

        if is_phase3:
            mu_slippage = 4.0
            std_slippage = 2.5
            operational_lag = 2.0
        elif is_phase2:
            mu_slippage = 2.5
            std_slippage = 1.8
            operational_lag = 1.5
        elif is_phase1:
            mu_slippage = 1.0
            std_slippage = 1.0
            operational_lag = 1.0
        else:
            mu_slippage = 2.0
            std_slippage = 1.5
            operational_lag = 1.5

        # Check for event-driven endpoints (OS, PFS, DFS, MACE)
        is_event_driven = False
        for ep in trial.primary_endpoints:
            combined_text = f"{(ep.title or '')} {(ep.description or '')}".lower()
            if any(k in combined_text for k in ["overall survival", "survival", "pfs", "progression-free", "dfs", "disease-free", "efs", "event-free", "mace", "mortality", "death"]):
                is_event_driven = True
                break
        if is_event_driven:
            mu_slippage += 2.0
            std_slippage += 1.2
            slippage_risk_factors.append("Event-driven primary endpoint (e.g. survival/progression events) introduces hazard-rate dependent accrual timing variance.")

        # Check for large enrollment scale
        if trial.enrollment and trial.enrollment >= 500:
            mu_slippage += 1.5
            std_slippage += 1.0
            slippage_risk_factors.append(f"Large multi-center enrollment target (N={trial.enrollment}) increases site initiation and monitoring query resolution lag.")

        # Check for rare disease accrual bottlenecks
        cond_text = " ".join(trial.conditions).lower()
        if any(k in cond_text for k in ["rare", "orphan", "pediatric", "refractory", "recurrent"]):
            mu_slippage += 1.5
            std_slippage += 1.0
            slippage_risk_factors.append("Rare or refractory indication pool elevates patient recruitment bottleneck risk.")

        # Calculate raw months to completion
        raw_months = self._estimate_months_to_date(trial.primary_completion_date or trial.completion_date)
        is_delinquent = False
        overdue_months = 0.0

        p10: Optional[float] = None
        p50: Optional[float] = None
        p90: Optional[float] = None
        dilution_prob: Optional[float] = None

        if trial.primary_completion_date_type == "ACTUAL" or status_upper == "COMPLETED":
            p10 = 0.0
            p50 = 0.0
            p90 = 0.0
            dilution_prob = 0.0
            total_mean = 0.0
            total_std = 0.0
            slippage_risk_factors.append("Data lock achieved: actual completion date confirmed.")
        elif raw_months is None:
            total_mean = None
            total_std = None
            slippage_risk_factors.append("No primary completion date registered on CT.gov; timing is unanchored.")
        elif raw_months < 0:
            is_delinquent = True
            overdue_months = abs(raw_months)
            p10 = 1.0
            p50 = round(max(3.0, overdue_months * 0.5) + operational_lag, 1)
            p90 = round(p50 + 1.282 * 3.0, 1)
            total_mean = p50
            total_std = 3.0
            slippage_risk_factors.append(f"DELINQUENT: Stated primary completion was {overdue_months:.0f} months ago ({trial.primary_completion_date}); timeline in active slippage.")
        else:
            total_mean = raw_months + mu_slippage + operational_lag
            total_std = std_slippage
            p10 = round(max(0.5, total_mean - 1.282 * total_std), 1)
            p50 = round(total_mean, 1)
            p90 = round(total_mean + 1.282 * total_std, 1)

        # 0. Check for Terminated / Suspended Study
        if status_upper in ["TERMINATED", "WITHDRAWN"]:
            return FinancialCatalystAudit(
                runway_vs_readout_alignment="DILUTION_IMMINENT",
                binary_risk_exposure="PURE_BINARY_PLAY",
                commercial_market_opportunity=f"Study status is {status_upper}. Deployed capital represents sunk loss with zero ongoing clinical catalyst value.",
                asymmetry_ratio="UNFAVORABLE",
                projected_dilution_window=f"CRITICAL: Protocol {status_upper}. Capital reallocation or restructuring required.",
                p10_readout_months=None,
                p50_readout_months=None,
                p90_readout_months=None,
                dilution_probability_before_readout=1.0,
                slippage_risk_factors=[f"Protocol {status_upper}; catalyst pipeline terminated."],
                confidence_score=0.90
            )
        elif status_upper == "SUSPENDED":
            return FinancialCatalystAudit(
                runway_vs_readout_alignment="DILUTION_IMMINENT",
                binary_risk_exposure="PURE_BINARY_PLAY",
                commercial_market_opportunity="Study is SUSPENDED (e.g. clinical hold). Catalyst timeline is indefinitely stalled while operational cash burn continues.",
                asymmetry_ratio="UNFAVORABLE",
                projected_dilution_window="CRITICAL: Clinical hold indefinitely delays catalyst while cash reserve depletes.",
                p10_readout_months=None,
                p50_readout_months=None,
                p90_readout_months=None,
                dilution_probability_before_readout=0.95,
                slippage_risk_factors=["Protocol SUSPENDED on regulatory/safety hold; timeline is indefinitely delayed."],
                confidence_score=0.85
            )

        if not financials:
            return FinancialCatalystAudit(
                runway_vs_readout_alignment="SAFE_BUFFER",
                binary_risk_exposure="MODERATE_PIPELINE_BUFFER",
                commercial_market_opportunity="Sponsor is privately held or an academic/government consortium; market dilution risk not applicable.",
                asymmetry_ratio="BALANCED",
                projected_dilution_window=None,
                p10_readout_months=p10,
                p50_readout_months=p50,
                p90_readout_months=p90,
                dilution_probability_before_readout=None,
                slippage_risk_factors=slippage_risk_factors,
                confidence_score=0.70
            )

        runway_months = financials.cash_runway_months
        runway_unknown = runway_months is None
        if runway_unknown:
            runway_months = 0.0

        mcap = financials.market_cap or 0.0
        base_confidence = 0.90
        if runway_unknown:
            base_confidence -= 0.20
        if financials.quarterly_burn_rate is None:
            base_confidence -= 0.10
        if is_delinquent:
            base_confidence -= 0.15

        # Check Short-Term Debt Cliff & Overhang
        has_debt_cliff = False
        has_debt_overhang = False
        if financials.short_term_debt and financials.total_liquid_cash and financials.total_liquid_cash > 0:
            debt_ratio = financials.short_term_debt / financials.total_liquid_cash
            if debt_ratio >= 1.0:
                has_debt_cliff = True
            elif debt_ratio >= 0.50:
                has_debt_overhang = True

        # Calculate dilution probability before readout
        if dilution_prob is None:
            if runway_unknown:
                dilution_prob = 0.50
                slippage_risk_factors.append("Uncertain cash runway due to unverified balance sheet filings.")
            elif runway_months >= 999.0:
                dilution_prob = 0.01
            elif total_mean is not None and total_std is not None:
                effective_runway = max(0.0, runway_months - 3.0)  # 3-month operational survival cushion
                raw_prob = 1.0 - self._normal_cdf(effective_runway, total_mean, total_std)
                dilution_prob = round(max(0.02, min(0.98, raw_prob)), 2)
            else:
                if runway_months < 9.0:
                    dilution_prob = 0.85
                elif runway_months < 18.0:
                    dilution_prob = 0.45
                else:
                    dilution_prob = 0.10

        # Determine Runway Alignment & Projected Dilution Window
        if has_debt_cliff:
            alignment = "DILUTION_IMMINENT"
            dilution_window = (
                f"CRITICAL DEBT CLIFF: Short-term debt obligations (${financials.short_term_debt:,.0f}) "
                f"exceed 100% of liquid cash reserves (${financials.total_liquid_cash:,.0f}). "
                f"Immediate debt refinancing or emergency equity dilution required."
            )
        elif is_delinquent:
            if runway_months < (p50 or 12.0):
                alignment = "DILUTION_IMMINENT"
            else:
                alignment = "TIGHT"
            dilution_window = (
                f"OVERDUE PROTOCOL: Stated primary completion was {overdue_months:.0f} months ago ({trial.primary_completion_date}). "
                f"Ongoing cash burn ({f'${financials.quarterly_burn_rate:,.0f}/qtr' if financials.quarterly_burn_rate else 'unknown'}) "
                f"erodes runway while readout timeline remains uncertain (P50 estimated: +{p50:.1f} mos)."
            )
        elif runway_unknown:
            alignment = "TIGHT"
            dilution_window = "WARNING: Cash runway could not be computed from available financial data. Treat as TIGHT pending verification of latest 10-Q filing."
        elif runway_months >= 999.0:
            alignment = "SAFE_BUFFER"
            dilution_window = "Self-funding / Cash flow positive; secondary equity dilution highly unlikely."
        elif dilution_prob >= 0.65 or (p50 is not None and runway_months < p50):
            alignment = "DILUTION_IMMINENT"
            dilution_window = (
                f"CRITICAL: High dilution probability ({dilution_prob*100:.0f}%) before data lock. "
                f"Cash runway ({runway_months:.0f} mos) is insufficient against the expected P50 readout ({p50:.1f} mos) "
                f"and P90 delayed horizon ({p90:.1f} mos). Mandatory financing event or asset partnership required."
            )
        elif dilution_prob >= 0.25:
            alignment = "TIGHT"
            dilution_window = (
                f"TIGHT: Moderate dilution probability ({dilution_prob*100:.0f}%) prior to data. "
                f"Runway ({runway_months:.0f} mos) covers P50 readout ({p50:.1f} mos) but leaves little cushion for P90 slippage ({p90:.1f} mos). "
                f"Management likely to tap ATM or secondary offering 3-6 months prior to anticipated data."
            )
        else:
            alignment = "SAFE_BUFFER"
            dilution_window = (
                f"SAFE BUFFER: Low dilution probability ({dilution_prob*100:.0f}%) before data lock. "
                f"Runway ({runway_months:.0f} mos) comfortably exceeds estimated P90 delayed readout ({p90:.1f} mos, incl. lag) with >6mo safety cushion."
            )

        if has_debt_overhang and not has_debt_cliff:
            if alignment == "SAFE_BUFFER":
                alignment = "TIGHT"
            dilution_window += f" (Note: Short-term debt of ${financials.short_term_debt:,.0f} represents {financials.short_term_debt/financials.total_liquid_cash*100:.0f}% of cash)."

        # Binary Risk Exposure: check market cap and single-lead asset concentration
        sponsor_lower = (trial.sponsor_name or "").lower()
        is_concentrated_biotech = any(k in sponsor_lower for k in [
            "viking", "altimmune", "kura", "alector", "sage", "revolution", "mirati", "bridgebio"
        ])

        if mcap > 25_000_000_000:
            binary_exposure = "HIGHLY_DIVERSIFIED"
            market_opp = "Mega-cap commercial platform. Trial outcome represents incremental pipeline expansion; downside is insulated by diversified revenues."
        elif mcap > 2_000_000_000 and not is_concentrated_biotech:
            binary_exposure = "MODERATE_PIPELINE_BUFFER"
            market_opp = "Mid-cap commercial/clinical stage with multiple programs. Failure produces material volatility but preserves underlying platform value."
        else:
            binary_exposure = "PURE_BINARY_PLAY"
            if is_concentrated_biotech and mcap > 2_000_000_000:
                market_opp = f"Mid-cap clinical stage (${mcap/1e9:.1f}B mcap) with valuation concentrated in lead program. Readout is a binary company-making or company-breaking event despite mid-cap capitalization."
            else:
                market_opp = "Clinical-stage micro/small-cap asset where clinical readout is a binary company-making or company-breaking event. Dilution risk is directly correlated with clinical outcome."

        # Asymmetry Ratio
        if alignment == "DILUTION_IMMINENT":
            asymmetry = "UNFAVORABLE"
        elif alignment == "SAFE_BUFFER" and binary_exposure in ["HIGHLY_DIVERSIFIED", "MODERATE_PIPELINE_BUFFER", "PURE_BINARY_PLAY"]:
            asymmetry = "FAVORABLE"
        else:
            asymmetry = "BALANCED"

        return FinancialCatalystAudit(
            runway_vs_readout_alignment=alignment,
            binary_risk_exposure=binary_exposure,
            commercial_market_opportunity=market_opp,
            asymmetry_ratio=asymmetry,
            projected_dilution_window=dilution_window,
            p10_readout_months=p10,
            p50_readout_months=p50,
            p90_readout_months=p90,
            dilution_probability_before_readout=dilution_prob,
            slippage_risk_factors=slippage_risk_factors,
            confidence_score=round(max(0.35, base_confidence), 2)
        )

    @staticmethod
    def _estimate_months_to_date(date_str: Optional[str]) -> Optional[float]:
        if not date_str:
            return None

        clean = date_str.strip()
        now = datetime.now(timezone.utc)

        # Try parsing YYYY-MM or YYYY-MM-DD
        m = re.match(r"^(\d{4})-(\d{1,2})", clean)
        if m:
            year = int(m.group(1))
            month = int(m.group(2))
            diff_years = year - now.year
            diff_months = month - now.month
            return diff_years * 12.0 + diff_months

        # Try parsing "Month YYYY"
        month_names = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        for name, m_num in month_names.items():
            if name in clean.lower():
                yr_match = re.search(r"\b(20\d\d)\b", clean)
                if yr_match:
                    year = int(yr_match.group(1))
                    diff_years = year - now.year
                    diff_months = m_num - now.month
                    return diff_years * 12.0 + diff_months

        return None
