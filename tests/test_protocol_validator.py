"""Unit tests for automated clinical protocol consistency and data integrity auditor."""

import pytest
from core.models import ClinicalTrial, Endpoint, Intervention
from core.protocol_validator import validate_trial_integrity
from agents.biostat_agent import BiostatisticianAgent


def test_phase_discrepancy_detection():
    """Flags when title/summary claims Phase 3/pivotal but registered phases are Phase 1/2."""
    trial = ClinicalTrial(
        nct_id="NCT0900001",
        title="Pivotal Phase 3 Trial of Novel Kinase Inhibitor in Melanoma",
        sponsor_name="Biotech Corp",
        phases=["PHASE1"],
        status="RECRUITING"
    )
    warnings = validate_trial_integrity(trial)
    assert any("Phase discrepancy" in w and "Phase 3 or pivotal" in w for w in warnings)


def test_phase1_vs_phase3_contradiction():
    """Flags when title claims Phase 1 first-in-human dose escalation but registered phase is Phase 3."""
    trial = ClinicalTrial(
        nct_id="NCT0900002",
        title="A First-in-Human Phase 1 Dose Escalation Study of Compound X",
        sponsor_name="Biotech Corp",
        phases=["PHASE3"],
        status="RECRUITING"
    )
    warnings = validate_trial_integrity(trial)
    assert any("Phase discrepancy" in w and "first-in-human" in w for w in warnings)


def test_completed_status_estimated_date_contradiction():
    """Flags when status is COMPLETED but primary completion date is still marked ESTIMATED."""
    trial = ClinicalTrial(
        nct_id="NCT0900003",
        title="Completed Oncology Study",
        sponsor_name="Biotech Corp",
        phases=["PHASE2"],
        status="COMPLETED",
        primary_completion_date="2025-06-01",
        primary_completion_date_type="ESTIMATED"
    )
    warnings = validate_trial_integrity(trial)
    assert any("Timeline contradiction" in w and "COMPLETED" in w for w in warnings)


def test_design_randomized_single_group_contradiction():
    """Flags contradiction when allocation is RANDOMIZED but intervention model is SINGLE_GROUP."""
    trial = ClinicalTrial(
        nct_id="NCT0900004",
        title="Single Arm Study",
        sponsor_name="Biotech Corp",
        phases=["PHASE2"],
        status="RECRUITING",
        allocation="RANDOMIZED",
        intervention_model="SINGLE_GROUP"
    )
    warnings = validate_trial_integrity(trial)
    assert any("Design contradiction" in w and "SINGLE_GROUP" in w for w in warnings)


def test_blinding_single_group_contradiction():
    """Flags contradiction when masking is DOUBLE/QUADRUPLE but intervention model is SINGLE_GROUP."""
    trial = ClinicalTrial(
        nct_id="NCT0900005",
        title="Blinded Single Arm Study",
        sponsor_name="Biotech Corp",
        phases=["PHASE2"],
        status="RECRUITING",
        masking="DOUBLE",
        intervention_model="SINGLE_GROUP"
    )
    warnings = validate_trial_integrity(trial)
    assert any("Blinding contradiction" in w and "SINGLE_GROUP" in w for w in warnings)


def test_phase3_safety_only_endpoint_incongruity():
    """Flags Phase 3 pivotal study whose primary endpoint exclusively assesses safety/tolerability without efficacy."""
    trial = ClinicalTrial(
        nct_id="NCT0900006",
        title="Pivotal Efficacy Study",
        sponsor_name="Biotech Corp",
        phases=["PHASE3"],
        status="RECRUITING",
        primary_endpoints=[
            Endpoint(title="Incidence of Treatment-Emergent Adverse Events (Safety and Tolerability)")
        ]
    )
    warnings = validate_trial_integrity(trial)
    assert any("Methodology incongruity" in w and "Phase 3" in w for w in warnings)


def test_zero_enrollment_anomaly():
    """Flags when active recruiting trial has enrollment count registered as 0."""
    trial = ClinicalTrial(
        nct_id="NCT0900007",
        title="Active Study with Zero Target Enrollment",
        sponsor_name="Biotech Corp",
        phases=["PHASE2"],
        status="RECRUITING",
        enrollment=0
    )
    warnings = validate_trial_integrity(trial)
    assert any("Enrollment anomaly" in w and "registered as 0" in w for w in warnings)


def test_biostat_agent_incorporates_integrity_alerts():
    """BiostatisticianAgent surfaces data integrity alerts in red_flags and penalizes design rigor."""
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0900008",
        title="Phase 3 Study with Design Inconsistencies",
        sponsor_name="Biotech Corp",
        phases=["PHASE3"],
        status="RECRUITING",
        allocation="RANDOMIZED",
        intervention_model="SINGLE_GROUP",
        enrollment=200,
        primary_endpoints=[Endpoint(title="Overall Survival")]
    )
    audit = agent._heuristic_analysis(trial)
    assert any("Data Integrity Alert" in rf for rf in audit.red_flags)
