"""Unit tests for Pydantic data models."""

import pytest
from core.models import (
    ClinicalTrial,
    CompanyFinancials,
    Endpoint,
    Intervention,
    MolecularAnalysis,
    BiostatAudit,
    FinancialCatalystAudit,
    DiligenceReport,
    DilutionRiskLevel,
    ConsensusVerdict,
)


def test_clinical_trial_model():
    trial = ClinicalTrial(
        nct_id="NCT12345678",
        title="Phase 3 Study of mRNA Vaccine in Solid Tumors",
        phases=["Phase 3"],
        sponsor_name="ModernaTX, Inc.",
        matched_ticker="MRNA",
        primary_endpoints=[
            Endpoint(title="Overall Survival", time_frame="36 months", is_primary=True)
        ],
        interventions=[
            Intervention(name="mRNA-4157", type="DRUG", description="Neoantigen mRNA")
        ],
        enrollment=500
    )
    assert trial.nct_id == "NCT12345678"
    assert trial.matched_ticker == "MRNA"
    assert trial.primary_endpoints[0].is_primary is True
    assert trial.interventions[0].name == "mRNA-4157"


def test_company_financials_model():
    fin = CompanyFinancials(
        ticker="VKTX",
        company_name="Viking Therapeutics",
        market_cap=3500000000.0,
        total_liquid_cash=500000000.0,
        quarterly_burn_rate=50000000.0,
        cash_runway_months=30.0,
        dilution_risk_level=DilutionRiskLevel.LOW
    )
    assert fin.ticker == "VKTX"
    assert fin.cash_runway_months == 30.0
    assert fin.dilution_risk_level == DilutionRiskLevel.LOW


def test_diligence_report_serialization():
    mol = MolecularAnalysis(
        target_name="KRAS G12C",
        modality="Small Molecule Inhibitor",
        biological_plausibility="HIGH",
        target_validation_summary="Clinically proven pocket inhibition.",
        preclinical_evidence_strength="STRONG",
        resistance_risk_notes="Secondary mutations.",
        confidence_score=0.9
    )
    bio = BiostatAudit(
        trial_design_rigor="HIGH",
        endpoint_quality="HARD_CLINICAL",
        endpoint_analysis="Overall survival primary outcome.",
        power_and_sample_size_assessment="Adequately powered.",
        control_arm_critique="Randomized vs Standard of Care.",
        blinding_rigor="Double blind.",
        red_flags=[]
    )
    fin_audit = FinancialCatalystAudit(
        runway_vs_readout_alignment="SAFE_BUFFER",
        binary_risk_exposure="MODERATE_PIPELINE_BUFFER",
        commercial_market_opportunity="Multi-billion blockbuster.",
        asymmetry_ratio="FAVORABLE",
        projected_dilution_window="None"
    )

    report = DiligenceReport(
        nct_id="NCT99999999",
        trial_title="Test Trial",
        sponsor="Test Biotech",
        ticker="TEST",
        molecular_analysis=mol,
        biostat_audit=bio,
        financial_audit=fin_audit,
        consensus_verdict=ConsensusVerdict.STRONG_CONVICTION,
        overall_score=88.5,
        executive_summary="Excellent clinical outlook."
    )

    json_str = report.model_dump_json()
    assert "NCT99999999" in json_str
    assert "STRONG_CONVICTION" in json_str
