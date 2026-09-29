import pytest
from core.models import ClinicalTrial
from agents.biostat_agent import BiostatisticianAgent

def test_disease_domain_sample_size():
    agent = BiostatisticianAgent()
    
    # 1. Rare Disease (N=50 in Phase 3 is well-powered)
    trial_rare = ClinicalTrial(
        nct_id="NCT0001",
        title="Pompe Disease Trial",
        sponsor_name="Mock",
        phases=["PHASE3"],
        conditions=["Pompe Disease"],
        enrollment=50
    )
    audit_rare = agent._heuristic_analysis(trial_rare)
    assert "well-powered" in audit_rare.power_and_sample_size_assessment.lower()
    
    # 2. Oncology (N=50 in Phase 3 is underpowered)
    trial_onc = ClinicalTrial(
        nct_id="NCT0002",
        title="Melanoma Trial",
        sponsor_name="Mock",
        phases=["PHASE3"],
        conditions=["Melanoma"],
        enrollment=50
    )
    audit_onc = agent._heuristic_analysis(trial_onc)
    assert "underpowered" in audit_onc.power_and_sample_size_assessment.lower()
    assert any("below standard statistical power thresholds" in flag for flag in audit_onc.red_flags)
    
    # 3. Broad Indication (N=200 in Phase 3 is underpowered, needs 300+)
    trial_broad = ClinicalTrial(
        nct_id="NCT0003",
        title="Hypertension Trial",
        sponsor_name="Mock",
        phases=["PHASE3"],
        conditions=["Hypertension"],
        enrollment=200
    )
    audit_broad = agent._heuristic_analysis(trial_broad)
    assert "underpowered" in audit_broad.power_and_sample_size_assessment.lower()
    
def test_master_protocol_detection():
    agent = BiostatisticianAgent()
    
    # Basket Trial
    trial_basket = ClinicalTrial(
        nct_id="NCT0004",
        title="Basket study of Drug X in multiple solid tumors",
        sponsor_name="Mock",
        phases=["PHASE2"],
        intervention_model="SINGLE_GROUP"
    )
    audit_basket = agent._heuristic_analysis(trial_basket)
    assert "basket design" in audit_basket.control_arm_critique.lower()
    
    # Umbrella Trial
    trial_umbrella = ClinicalTrial(
        nct_id="NCT0005",
        title="Platform study for NSCLC",
        sponsor_name="Mock",
        phases=["PHASE2"],
        intervention_model="PARALLEL"
    )
    audit_umbrella = agent._heuristic_analysis(trial_umbrella)
    assert "umbrella/platform design" in audit_umbrella.control_arm_critique.lower()

from core.models import Endpoint

def test_os_substring_false_positive():
    """'dose' or 'glucose' must NOT match 'os' as Overall Survival abbreviation."""
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0006",
        title="Glucose Study",
        sponsor_name="Mock",
        phases=["PHASE2"],
        conditions=["Diabetes"],
        primary_endpoints=[
            Endpoint(
                title="Blood Glucose Change",
                description="Change from baseline in fasting glucose dose at week 12",
                time_frame="12 weeks"
            )
        ],
        enrollment=80
    )
    audit = agent._heuristic_analysis(trial)
    # 'glucose dose' contains 'os' as substring but should NOT classify as HARD_CLINICAL
    assert audit.endpoint_quality != "HARD_CLINICAL", (
        "The string 'glucose dose' must not trigger Overall Survival detection via 'os' substring."
    )


def test_no_endpoints_registered_flags_risk():
    """A trial with no primary endpoints in the registry must surface a red flag."""
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0007",
        title="Early Phase Study",
        sponsor_name="Mock",
        phases=["PHASE1"],
        conditions=["Cancer"],
        primary_endpoints=[],  # Empty - not yet registered
        enrollment=20
    )
    audit = agent._heuristic_analysis(trial)
    assert any("No primary endpoints" in flag for flag in audit.red_flags)
    assert audit.endpoint_quality == "SURROGATE_UNVALIDATED"
    # Confidence should be significantly degraded
    assert audit.confidence_score < 0.80


def test_confidence_degrades_with_red_flags():
    """More red flags should lower the confidence score."""
    agent = BiostatisticianAgent()
    # Single-arm Phase 3 non-orphan with unspecified enrollment -> multiple red flags
    trial = ClinicalTrial(
        nct_id="NCT0008",
        title="Phase 3 Open-Label Single-Arm Study",
        sponsor_name="Mock",
        phases=["PHASE3"],
        conditions=["Hypertension"],  # Broad indication
        primary_endpoints=[
            Endpoint(
                title="Blood Pressure Biomarker",
                description="Change in biomarker level at week 24",
                time_frame="24 weeks"
            )
        ],
        enrollment=None,  # No enrollment specified
        masking="NONE",
        allocation="NON_RANDOMIZED",
        intervention_model="SINGLE_GROUP"
    )
    audit = agent._heuristic_analysis(trial)
    # Expect multiple red flags: no enrollment + single-arm phase 3 + biomarker endpoint + open-label
    assert len(audit.red_flags) >= 2
    # Confidence must not be 0.90 when there are multiple red flags
    assert audit.confidence_score < 0.80

def test_terminated_trial_fatal_flag():
    """Terminated study must trigger a terminal halt red flag and low design rigor."""
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0009",
        title="Terminated Phase 3 Oncology Trial",
        sponsor_name="Mock",
        phases=["PHASE3"],
        status="TERMINATED",
        conditions=["Cancer"],
        enrollment=500
    )
    audit = agent._heuristic_analysis(trial)
    assert any("TERMINATED" in flag for flag in audit.red_flags)
    assert audit.trial_design_rigor == "LOW"


def test_suspended_trial_flag():
    """Suspended study must trigger a clinical hold red flag."""
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0010",
        title="Suspended Phase 2 Trial",
        sponsor_name="Mock",
        phases=["PHASE2"],
        status="SUSPENDED",
        conditions=["Rare Disease"],
        enrollment=100
    )
    audit = agent._heuristic_analysis(trial)
    assert any("SUSPENDED" in flag for flag in audit.red_flags)
    assert audit.trial_design_rigor == "LOW"


def test_delinquent_overdue_trial_timeline():
    """Active trial with estimated completion date far in the past must be flagged as delinquent."""
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0011",
        title="Delinquent Phase 2 Trial",
        sponsor_name="Mock",
        phases=["PHASE2"],
        status="RECRUITING",
        conditions=["Cancer"],
        primary_completion_date="2023-01",
        primary_completion_date_type="ESTIMATED",
        enrollment=80
    )
    audit = agent._heuristic_analysis(trial)
    assert any("DELINQUENT" in flag for flag in audit.red_flags)

def test_endpoint_hierarchy_confidence_bump():
    "Trials with designated Key Secondary endpoints should get a confidence boost due to explicit alpha-spending."
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0012",
        title="Hierarchical Endpoint Trial",
        sponsor_name="Mock",
        phases=["PHASE3"],
        status="COMPLETED",
        conditions=["Asthma"],
        primary_endpoints=[
            Endpoint(title="FEV1", hierarchy="PRIMARY")
        ],
        secondary_endpoints=[
            Endpoint(title="Key Secondary: Asthma Exacerbations", hierarchy="KEY_SECONDARY"),
            Endpoint(title="Exploratory Biomarker IgE", hierarchy="EXPLORATORY")
        ],
        enrollment=500,
        masking="DOUBLE",
        intervention_model="PARALLEL",
        allocation="RANDOMIZED"
    )
    audit = agent._heuristic_analysis(trial)
    
    assert "key secondary endpoints" in audit.endpoint_analysis.lower()
    assert "exploratory" in audit.endpoint_analysis.lower()
    
    # Base is 0.90, +0.05 for key secondaries = 0.95
    assert audit.confidence_score == 0.95

def test_crossover_os_penalization():
    "Trials with crossover designs and Overall Survival endpoints should flag the OS dilution risk."
    agent = BiostatisticianAgent()
    trial = ClinicalTrial(
        nct_id="NCT0013",
        title="Crossover Oncology Trial",
        sponsor_name="Mock",
        phases=["PHASE3"],
        status="COMPLETED",
        conditions=["Cancer"],
        primary_endpoints=[
            Endpoint(title="Overall Survival", hierarchy="PRIMARY")
        ],
        enrollment=500,
        masking="NONE",
        intervention_model="CROSSOVER",
        allocation="RANDOMIZED"
    )
    audit = agent._heuristic_analysis(trial)
    
    assert "Crossover design dilutes Overall Survival" in "".join(audit.red_flags)
    assert "confounded by crossover design" in audit.endpoint_analysis
