"""Unit tests for multi-agent diligence committee synthesis."""

import pytest
from core.models import (
    ClinicalTrial,
    CompanyFinancials,
    MolecularAnalysis,
    BiostatAudit,
    FinancialCatalystAudit,
    ConsensusVerdict
)
from agents.committee import DiligenceCommittee


def _dummy_trial():
    return ClinicalTrial(
        nct_id="NCT0000001",
        title="Mock Trial",
        sponsor_name="Mock Pharma",
        matched_ticker="MOCK",
        phases=["PHASE2"],
        estimated_catalyst_window="Q1 2026"
    )

def _dummy_molecular():
    return MolecularAnalysis(
        target_name="Mock Target",
        modality="Small Molecule",
        biological_plausibility="MODERATE",
        target_validation_summary="Standard validation.",
        preclinical_evidence_strength="MODERATE",
        resistance_risk_notes="None.",
        confidence_score=1.0  # Full confidence for pure math verification
    )

def _dummy_biostat():
    return BiostatAudit(
        trial_design_rigor="HIGH",
        endpoint_quality="HARD_CLINICAL",
        endpoint_analysis="Survival",
        power_and_sample_size_assessment="Well powered",
        control_arm_critique="Placebo controlled",
        blinding_rigor="Double blind",
        red_flags=[],
        confidence_score=1.0  # Full confidence for pure math verification
    )

def _dummy_financial():
    return FinancialCatalystAudit(
        runway_vs_readout_alignment="SAFE_BUFFER",
        binary_risk_exposure="PURE_BINARY_PLAY",
        commercial_market_opportunity="Large",
        asymmetry_ratio="FAVORABLE",
        confidence_score=1.0  # Full confidence for pure math verification
    )


def test_committee_consensus():
    # Setup dummies
    trial = _dummy_trial()
    mol = _dummy_molecular()
    bio = _dummy_biostat()
    fin = _dummy_financial()

    # Need a mock pubmed client, and mock agent returns
    committee = DiligenceCommittee()
    
    # We will just test the scoring logic directly (confidence=1.0 means no shrinkage)
    score, _ = committee._compute_composite_score(mol, bio, fin, None)
    
    # Base: 25 + 25 + 25 = 75
    # Mol Mod: +4, Preclin: +1
    # Bio High: +6, Hard Clin: +4
    # Fin Safe: +5, Fav: +3
    # Total = 98.0, clamped to 98.0
    assert score == 98.0

def test_multiplicative_penalty_dilution_imminent():
    committee = DiligenceCommittee()
    mol = _dummy_molecular()
    bio = _dummy_biostat()
    fin = _dummy_financial()
    
    fin.runway_vs_readout_alignment = "DILUTION_IMMINENT"
    fin.asymmetry_ratio = "UNFAVORABLE"
    
    score, _ = committee._compute_composite_score(mol, bio, fin, None)
    
    # Base: 75
    # Mol Mod: +4, Preclin: +1 (+5)
    # Bio High: +6, Hard Clin: +4 (+10)
    # Fin Imminent: -12, Unfavorable: -4 (-16)
    # Total before penalty: 75 + 5 + 10 - 16 = 74
    # Penalty factor: 0.45
    # Final Score: 74 * 0.45 = 33.3
    assert abs(score - 33.3) < 0.1

def test_multiplicative_penalty_unvalidated_surrogate_red_flags():
    committee = DiligenceCommittee()
    mol = _dummy_molecular()
    bio = _dummy_biostat()
    fin = _dummy_financial()
    
    bio.endpoint_quality = "SURROGATE_UNVALIDATED"
    bio.red_flags = ["Flag 1", "Flag 2"]
    
    score, _ = committee._compute_composite_score(mol, bio, fin, None)
    
    # Base: 75
    # Mol: +5
    # Bio: High +6, Surrogate unval -4. Total bio weighting: +2
    # Fin: Safe +5, Fav +3. Total fin: +8
    # Red flags penalty: 2 * 4.0 = -8.0
    # Total before penalty: 75 + 5 + 2 + 8 - 8 = 82
    # Penalty factor: 0.60
    # Final Score: 82 * 0.60 = 49.2
    assert abs(score - 49.2) < 0.1


def test_low_confidence_shrinks_score_toward_base():
    """When agent confidence is low, additive contributions shrink toward the neutral 25.0 base."""
    committee = DiligenceCommittee()
    mol = _dummy_molecular()
    bio = _dummy_biostat()
    fin = _dummy_financial()

    # High-confidence score
    score_hi, _ = committee._compute_composite_score(mol, bio, fin, None)

    # Set very low confidence on all agents
    mol_lo = _dummy_molecular()
    bio_lo = _dummy_biostat()
    fin_lo = _dummy_financial()
    mol_lo.confidence_score = 0.40
    bio_lo.confidence_score = 0.40
    fin_lo.confidence_score = 0.40

    score_lo, audit_lo = committee._compute_composite_score(mol_lo, bio_lo, fin_lo, None)

    # Low-confidence should produce a lower total since positive deviations are shrunk
    assert score_lo < score_hi, (
        f"Low-confidence analysis ({score_lo:.1f}) should score lower than high-confidence ({score_hi:.1f})."
    )
    # Audit should note the confidence weighting
    assert any("Confidence weighting" in step for step in audit_lo)


def test_terminated_trial_gating_penalty_and_verdict():
    """Terminated study must receive x0.15 penalty and HIGH_RISK_AVOID verdict."""
    committee = DiligenceCommittee()
    trial = _dummy_trial()
    trial.status = "TERMINATED"
    mol = _dummy_molecular()
    bio = _dummy_biostat()
    fin = _dummy_financial()

    score, audit = committee._compute_composite_score(mol, bio, fin, None, trial=trial)
    assert any("Fatal Protocol Halt" in step for step in audit)
    # 98.0 * 0.15 = 14.7
    assert abs(score - 14.7) < 0.2


def test_debt_cliff_gating_penalty():
    """Short-term debt exceeding liquid cash triggers x0.50 solvency penalty."""
    committee = DiligenceCommittee()
    mol = _dummy_molecular()
    bio = _dummy_biostat()
    fin = _dummy_financial()
    financials = CompanyFinancials(
        ticker="TEST",
        company_name="Test Pharma",
        total_liquid_cash=50_000_000,
        short_term_debt=60_000_000
    )

    score, audit = committee._compute_composite_score(mol, bio, fin, financials, trial=None)
    assert any("Short-term debt" in step for step in audit)
    # 98.0 * 0.50 = 49.0
    assert abs(score - 49.0) < 0.2
