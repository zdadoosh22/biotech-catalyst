"""Unit tests for report exporter."""

import pytest
import tempfile
from pathlib import Path

from core.models import ClinicalTrial, CompanyFinancials, DilutionRiskLevel, DiligenceReport, MolecularAnalysis, BiostatAudit, FinancialCatalystAudit, ConsensusVerdict
from reports.exporter import ReportExporter


def test_markdown_export():
    mol = MolecularAnalysis(
        target_name="mRNA-4157 Neoantigen",
        modality="mRNA / Lipid Nanoparticle",
        biological_plausibility="HIGH",
        target_validation_summary="High neoantigen validation.",
        preclinical_evidence_strength="STRONG",
        resistance_risk_notes="Immune exhaustion.",
        confidence_score=0.9
    )
    bio = BiostatAudit(
        trial_design_rigor="HIGH",
        endpoint_quality="HARD_CLINICAL",
        endpoint_analysis="Overall survival hard endpoint.",
        power_and_sample_size_assessment="Well powered N=1089.",
        control_arm_critique="Standard of care control.",
        blinding_rigor="Double blind.",
        red_flags=[]
    )
    fin_audit = FinancialCatalystAudit(
        runway_vs_readout_alignment="SAFE_BUFFER",
        binary_risk_exposure="HIGHLY_DIVERSIFIED",
        commercial_market_opportunity="Blockbuster oncology market.",
        asymmetry_ratio="FAVORABLE",
        projected_dilution_window="None"
    )

    report = DiligenceReport(
        nct_id="NCT05933577",
        trial_title="Phase 3 mRNA-4157 Study",
        sponsor="ModernaTX, Inc.",
        ticker="MRNA",
        molecular_analysis=mol,
        biostat_audit=bio,
        financial_audit=fin_audit,
        consensus_verdict=ConsensusVerdict.STRONG_CONVICTION,
        overall_score=91.0,
        executive_summary="Exceptional scientific and financial outlook."
    )

    trial = ClinicalTrial(
        nct_id="NCT05933577",
        title="Phase 3 mRNA-4157 Study",
        sponsor_name="ModernaTX, Inc.",
        matched_ticker="MRNA"
    )

    md = ReportExporter.export_to_markdown(report, trial, None)
    assert "# 🟢 BioCatalyst Intelligence Dossier: NCT05933577" in md
    assert "Dr. Elena Vance" in md
    assert "Dr. Marcus Thorne" in md
    assert "Alexander Vance, CFA" in md
    assert "STRONG_CONVICTION" in md
    assert "Readout Horizon (P10 / P50 / P90)" in md
    assert "Pre-Readout Dilution Probability" in md


def test_csv_export():
    trials = [
        ClinicalTrial(
            nct_id="NCT00000001",
            title="Trial One",
            sponsor_name="Sponsor A",
            matched_ticker="AAA"
        ),
        ClinicalTrial(
            nct_id="NCT00000002",
            title="Trial Two",
            sponsor_name="Sponsor B",
            matched_ticker="BBB"
        )
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        tmp_csv = f.name

    ReportExporter.export_trials_to_csv(trials, tmp_csv)
    content = Path(tmp_csv).read_text(encoding="utf-8")
    assert "NCT00000001" in content
    assert "Trial Two" in content
    Path(tmp_csv).unlink(missing_ok=True)
