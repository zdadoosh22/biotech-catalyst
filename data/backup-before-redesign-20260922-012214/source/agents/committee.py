"""Multi-Agent Biotech Diligence Committee Chairperson.

Synthesizes molecular, biostatistical, and financial audits into a unified
evidence-backed consensus verdict, overall score, and strategic action plan.
"""

from typing import Optional, List, Dict, Any

from core.models import (
    ClinicalTrial,
    CompanyFinancials,
    DiligenceReport,
    ConsensusVerdict,
    MolecularAnalysis,
    BiostatAudit,
    FinancialCatalystAudit,
    utc_now_iso
)
from agents.molecular_agent import MolecularAnalystAgent
from agents.biostat_agent import BiostatisticianAgent
from agents.financial_agent import FinancialCatalystAgent
from clients.pubmed import PubMedClient


class DiligenceCommittee:
    def __init__(
        self,
        molecular_agent: Optional[MolecularAnalystAgent] = None,
        biostat_agent: Optional[BiostatisticianAgent] = None,
        financial_agent: Optional[FinancialCatalystAgent] = None,
        pubmed_client: Optional[PubMedClient] = None
    ):
        self.molecular_agent = molecular_agent or MolecularAnalystAgent()
        self.biostat_agent = biostat_agent or BiostatisticianAgent()
        self.financial_agent = financial_agent or FinancialCatalystAgent()
        self.pubmed_client = pubmed_client or PubMedClient()

    def conduct_diligence(
        self,
        trial: ClinicalTrial,
        financials: Optional[CompanyFinancials] = None,
        include_pubmed: bool = True
    ) -> DiligenceReport:
        """Runs the full multi-agent audit suite and synthesizes committee consensus."""
        # 1. Harvest relevant scientific literature if enabled
        literature = []
        if include_pubmed:
            query_term = trial.interventions[0].name if trial.interventions else trial.title
            pmids = self.pubmed_client.search(query_term, max_results=3)
            if pmids:
                literature = self.pubmed_client.fetch_abstracts(pmids)

        # 2. Parallel / Sequential Agent Audits
        mol_audit: MolecularAnalysis = self.molecular_agent.analyze(trial, literature)
        bio_audit: BiostatAudit = self.biostat_agent.analyze(trial)
        fin_audit: FinancialCatalystAudit = self.financial_agent.analyze(trial, financials)

        # 3. Composite Scoring Engine
        score, audit_trail = self._compute_composite_score(mol_audit, bio_audit, fin_audit, financials, trial)

        # 4. Consensus Verdict Classification
        # Fatal protocol statuses override to HIGH_RISK_AVOID regardless of component scores
        status_upper = (trial.status or "UNKNOWN").upper()
        if status_upper in ["TERMINATED", "WITHDRAWN", "SUSPENDED"]:
            verdict = ConsensusVerdict.HIGH_RISK_AVOID
        elif score >= 78.0:
            verdict = ConsensusVerdict.STRONG_CONVICTION
        elif score >= 60.0:
            verdict = ConsensusVerdict.SPECULATIVE_ASYMMETRIC
        elif score >= 45.0:
            verdict = ConsensusVerdict.NEUTRAL_WATCH
        else:
            verdict = ConsensusVerdict.HIGH_RISK_AVOID

        # 5. Key Catalysts and Critical Risks Synthesis
        catalysts, risks = self._extract_catalysts_and_risks(trial, mol_audit, bio_audit, fin_audit, financials)

        # 6. Executive Summary
        exec_summary = self._generate_executive_summary(
            trial, financials, mol_audit, bio_audit, fin_audit, verdict, score
        )

        return DiligenceReport(
            nct_id=trial.nct_id,
            trial_title=trial.title,
            sponsor=trial.sponsor_name,
            ticker=financials.ticker if financials else trial.matched_ticker,
            molecular_analysis=mol_audit,
            biostat_audit=bio_audit,
            financial_audit=fin_audit,
            consensus_verdict=verdict,
            overall_score=round(score, 1),
            scoring_audit_trail=audit_trail,
            executive_summary=exec_summary,
            key_catalysts=catalysts,
            critical_risks=risks,
            created_at=utc_now_iso()
        )

    def _compute_composite_score(
        self,
        mol: MolecularAnalysis,
        bio: BiostatAudit,
        fin: FinancialCatalystAudit,
        financials: Optional[CompanyFinancials],
        trial: Optional[ClinicalTrial] = None
    ) -> tuple[float, List[str]]:
        audit = []
        # Base Points
        mol_score = 25.0
        bio_score = 25.0
        fin_score = 25.0
        audit.append("Base component scores: Molecular (25.0), Biostat (25.0), Financial (25.0)")

        # Molecular Weighting (max 35)
        if mol.biological_plausibility == "HIGH":
            mol_score += 7.0
            audit.append("+7.0 (Molecular): HIGH biological plausibility.")
        elif mol.biological_plausibility == "MODERATE":
            mol_score += 4.0
            audit.append("+4.0 (Molecular): MODERATE biological plausibility.")
        elif mol.biological_plausibility == "EXPERIMENTAL":
            mol_score += 1.0
            audit.append("+1.0 (Molecular): EXPERIMENTAL biological plausibility.")

        if mol.preclinical_evidence_strength == "STRONG":
            mol_score += 3.0
            audit.append("+3.0 (Molecular): STRONG preclinical evidence.")
        elif mol.preclinical_evidence_strength == "MODERATE":
            mol_score += 1.0
            audit.append("+1.0 (Molecular): MODERATE preclinical evidence.")

        # Biostatistical Weighting (max 35)
        if bio.trial_design_rigor == "HIGH":
            bio_score += 6.0
            audit.append("+6.0 (Biostat): HIGH trial design rigor.")
        elif bio.trial_design_rigor == "MODERATE":
            bio_score += 3.0
            audit.append("+3.0 (Biostat): MODERATE trial design rigor.")

        if bio.endpoint_quality == "HARD_CLINICAL":
            bio_score += 4.0
            audit.append("+4.0 (Biostat): HARD_CLINICAL primary endpoint.")
        elif bio.endpoint_quality == "SURROGATE_VALIDATED":
            bio_score += 2.0
            audit.append("+2.0 (Biostat): SURROGATE_VALIDATED primary endpoint.")
        else:
            bio_score -= 4.0  # Penalty for unvalidated surrogate
            audit.append("-4.0 (Biostat PENALTY): SURROGATE_UNVALIDATED primary endpoint.")

        # Financial & Runway Weighting (max 30)
        if fin.runway_vs_readout_alignment == "SAFE_BUFFER":
            fin_score += 5.0
            audit.append("+5.0 (Financial): SAFE_BUFFER for cash runway vs readout.")
        elif fin.runway_vs_readout_alignment == "TIGHT":
            fin_score -= 2.0
            audit.append("-2.0 (Financial PENALTY): TIGHT cash runway vs readout.")
        elif fin.runway_vs_readout_alignment == "DILUTION_IMMINENT":
            fin_score -= 12.0  # Severe penalty for dilution risk
            audit.append("-12.0 (Financial PENALTY): DILUTION_IMMINENT before readout.")

        if fin.asymmetry_ratio == "FAVORABLE":
            fin_score += 3.0
            audit.append("+3.0 (Financial): FAVORABLE binary asymmetry.")
        elif fin.asymmetry_ratio == "UNFAVORABLE":
            fin_score -= 4.0
            audit.append("-4.0 (Financial PENALTY): UNFAVORABLE binary asymmetry.")

        # Penalties for red flags
        total_penalties = len(bio.red_flags) * 4.0
        if total_penalties > 0:
            audit.append(f"-{total_penalties:.1f} (Biostat PENALTY): {len(bio.red_flags)} methodology red flags.")

        total_score_raw = mol_score + bio_score + fin_score - total_penalties

        # === Agent Confidence Weighting ===
        # Each agent's additive contribution above/below the neutral 25-point base
        # is scaled by that agent's confidence score. This ensures that analyses
        # based on sparse data (low confidence) shrink toward the uninformed prior.
        mol_conf = mol.confidence_score or 0.70
        bio_conf = bio.confidence_score or 0.70
        fin_conf = fin.confidence_score or 0.70

        # Deviation from the 25.0 neutral base for each component
        mol_dev = mol_score - 25.0
        bio_dev = (bio_score - 25.0) - total_penalties  # includes red flag penalty
        fin_dev = fin_score - 25.0

        # Reconstruct confidence-weighted total: base (75.0) + weighted deviations
        total_score = 75.0 + (mol_dev * mol_conf) + (bio_dev * bio_conf) + (fin_dev * fin_conf)

        if abs(mol_conf - 1.0) > 0.01 or abs(bio_conf - 1.0) > 0.01 or abs(fin_conf - 1.0) > 0.01:
            audit.append(
                f"Confidence weighting applied: Mol conf={mol_conf:.2f}, "
                f"Bio conf={bio_conf:.2f}, Fin conf={fin_conf:.2f}. "
                f"Low-confidence analyses shrink additive contributions toward the base."
            )
        
        # Apply Multiplicative Gating / Probability Curves
        penalty_factor = 1.0

        if fin.runway_vs_readout_alignment == "DILUTION_IMMINENT":
            penalty_factor *= 0.45
            audit.append("x0.45 MULTIPLICATIVE PENALTY (Financial): Terminal solvency risk caps scientific upside.")
            
        if bio.endpoint_quality == "SURROGATE_UNVALIDATED" and len(bio.red_flags) >= 2:
            penalty_factor *= 0.60
            audit.append("x0.60 MULTIPLICATIVE PENALTY (Biostat): Unvalidated surrogate combined with trial flaws poses severe FDA rejection risk.")

        if mol.biological_plausibility == "EXPERIMENTAL" and mol.preclinical_evidence_strength == "WEAK":
            penalty_factor *= 0.65
            audit.append("x0.65 MULTIPLICATIVE PENALTY (Molecular): Speculative biology with weak evidence.")

        # Fatal protocol status gating penalties
        if trial:
            status_upper = (trial.status or "").upper()
            if status_upper in ["TERMINATED", "WITHDRAWN"]:
                penalty_factor *= 0.15
                audit.append(f"x0.15 MULTIPLICATIVE PENALTY (Fatal Protocol Halt): Trial status is {status_upper}.")
            elif status_upper == "SUSPENDED":
                penalty_factor *= 0.40
                audit.append("x0.40 MULTIPLICATIVE PENALTY (Regulatory Safety Hold): Trial status is SUSPENDED.")

        # Debt cliff gating penalty
        if financials and financials.short_term_debt and financials.total_liquid_cash and financials.total_liquid_cash > 0:
            if financials.short_term_debt >= financials.total_liquid_cash:
                penalty_factor *= 0.50
                audit.append(f"x0.50 MULTIPLICATIVE PENALTY (Financial Solvency): Short-term debt (${financials.short_term_debt:,.0f}) equals or exceeds liquid cash reserves.")

        total_score *= penalty_factor
        
        if total_score > 98.0:
            audit.append(f"Score clamped from {total_score:.1f} to max 98.0")
        elif total_score < 5.0:
            audit.append(f"Score clamped from {total_score:.1f} to min 5.0")
            
        return max(5.0, min(98.0, total_score)), audit

    def _extract_catalysts_and_risks(
        self,
        trial: ClinicalTrial,
        mol: MolecularAnalysis,
        bio: BiostatAudit,
        fin: FinancialCatalystAudit,
        financials: Optional[CompanyFinancials]
    ) -> tuple[List[str], List[str]]:
        catalysts = []
        risks = []

        # Catalysts
        if trial.estimated_catalyst_window:
            catalysts.append(f"Primary endpoint readout targeted for {trial.estimated_catalyst_window}.")
        if trial.primary_endpoints:
            catalysts.append(f"Topline disclosure on primary metric: {trial.primary_endpoints[0].title}.")
        catalysts.append(f"Therapeutic modality: {mol.modality} targeting {mol.target_name}.")
        if fin.binary_risk_exposure == "PURE_BINARY_PLAY":
            catalysts.append("High-beta binary event: Positive outcome could trigger multi-fold re-rating.")
        elif fin.binary_risk_exposure == "HIGHLY_DIVERSIFIED":
            catalysts.append("De-risked commercial platform expansion potential.")

        # Risks
        status_upper = (trial.status or "").upper()
        if status_upper in ["TERMINATED", "WITHDRAWN", "SUSPENDED"]:
            risks.append(f"PROTOCOL HALT: Study status is {status_upper}.")

        for rf in bio.red_flags:
            risks.append(f"Methodology Vulnerability: {rf}")
        if fin.runway_vs_readout_alignment == "DILUTION_IMMINENT":
            risks.append("Capital Solvency Threat: Cash runway expires prior to projected trial readout date.")
        elif fin.runway_vs_readout_alignment == "TIGHT":
            risks.append("Secondary Offering Risk: Management likely to raise capital or sell shares into any data strength.")
        if financials and financials.short_term_debt and financials.total_liquid_cash and financials.total_liquid_cash > 0:
            if financials.short_term_debt >= 0.50 * financials.total_liquid_cash:
                risks.append(f"Debt Maturity Overhang: Short-term debt (${financials.short_term_debt:,.0f}) represents {financials.short_term_debt/financials.total_liquid_cash*100:.0f}% of cash reserves.")
        if mol.resistance_risk_notes:
            risks.append(f"Biological Resistance: {mol.resistance_risk_notes}")

        return catalysts, risks

    def _generate_executive_summary(
        self,
        trial: ClinicalTrial,
        financials: Optional[CompanyFinancials],
        mol: MolecularAnalysis,
        bio: BiostatAudit,
        fin: FinancialCatalystAudit,
        verdict: ConsensusVerdict,
        score: float
    ) -> str:
        ticker_str = f" (${financials.ticker})" if financials else ""
        window_str = trial.estimated_catalyst_window or "Upcoming Quarters"
        return (
            f"Diligence Committee synthesizes a **{verdict.value}** rating (Score: {score:.1f}/100) for "
            f"{trial.sponsor_name}{ticker_str} on trial {trial.nct_id} ('{trial.title[:70]}...'). "
            f"The asset utilizes a {mol.modality} approach targeting {mol.target_name} with {mol.biological_plausibility.lower()} biological plausibility. "
            f"Statistical rigor is rated as {bio.trial_design_rigor.lower()} with {bio.endpoint_quality.lower()} endpoints. "
            f"From a balance sheet perspective, the catalyst window ({window_str}) displays a {fin.runway_vs_readout_alignment.lower()} alignment "
            f"with an {fin.asymmetry_ratio.lower()} asymmetry risk profile."
        )
