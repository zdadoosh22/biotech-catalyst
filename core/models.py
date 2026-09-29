"""Pydantic data models for the BioCatalyst intelligence platform.

Covers clinical trials, financial runway metrics, specialized multi-agent diligence
reports, and synthesis verdicts.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StudyPhase(str, Enum):
    PHASE1 = "Phase 1"
    PHASE1_PHASE2 = "Phase 1/Phase 2"
    PHASE2 = "Phase 2"
    PHASE2_PHASE3 = "Phase 2/Phase 3"
    PHASE3 = "Phase 3"
    PHASE4 = "Phase 4"
    NA = "Not Applicable"
    EARLY_PHASE1 = "Early Phase 1"
    UNKNOWN = "Unknown"


class DilutionRiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConsensusVerdict(str, Enum):
    STRONG_CONVICTION = "STRONG_CONVICTION"
    SPECULATIVE_ASYMMETRIC = "SPECULATIVE_ASYMMETRIC"
    NEUTRAL_WATCH = "NEUTRAL_WATCH"
    HIGH_RISK_AVOID = "HIGH_RISK_AVOID"


class EndpointHierarchy(str, Enum):
    PRIMARY = "PRIMARY"
    KEY_SECONDARY = "KEY_SECONDARY"
    EXPLORATORY = "EXPLORATORY"
    SECONDARY = "SECONDARY"


class Endpoint(BaseModel):
    title: str
    description: Optional[str] = ""
    time_frame: Optional[str] = ""
    is_primary: bool = False
    hierarchy: EndpointHierarchy = EndpointHierarchy.SECONDARY


class Intervention(BaseModel):
    name: str
    type: str = "OTHER"
    description: Optional[str] = ""


class ClinicalTrial(BaseModel):
    nct_id: str
    title: str
    official_title: Optional[str] = None
    brief_summary: str = ""
    detailed_description: Optional[str] = None
    phases: List[str] = Field(default_factory=list)
    status: str = "UNKNOWN"
    sponsor_name: str = "Unknown Sponsor"
    collaborators: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    interventions: List[Intervention] = Field(default_factory=list)
    primary_endpoints: List[Endpoint] = Field(default_factory=list)
    secondary_endpoints: List[Endpoint] = Field(default_factory=list)
    enrollment: Optional[int] = None
    start_date: Optional[str] = None
    start_date_type: Optional[str] = None
    primary_completion_date: Optional[str] = None
    primary_completion_date_type: Optional[str] = None
    completion_date: Optional[str] = None
    completion_date_type: Optional[str] = None
    study_type: Optional[str] = "INTERVENTIONAL"
    allocation: Optional[str] = None
    intervention_model: Optional[str] = None
    masking: Optional[str] = None
    estimated_catalyst_window: Optional[str] = None
    matched_ticker: Optional[str] = None
    last_updated: Optional[str] = None
    data_integrity_warnings: List[str] = Field(default_factory=list)


class CompanyFinancials(BaseModel):
    ticker: str
    company_name: str
    market_cap: Optional[float] = None
    stock_price: Optional[float] = None
    total_liquid_cash: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    short_term_investments: Optional[float] = None
    quarterly_burn_rate: Optional[float] = None
    cash_runway_months: Optional[float] = None
    dilution_risk_level: DilutionRiskLevel = DilutionRiskLevel.MODERATE
    debt_to_equity: Optional[float] = None
    short_term_debt: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    currency: str = "USD"
    data_freshness_warning: Optional[str] = None
    fetched_at: str = Field(default_factory=utc_now_iso)


class MolecularAnalysis(BaseModel):
    target_name: str
    modality: str
    biological_plausibility: str  # HIGH, MODERATE, LOW, EXPERIMENTAL
    target_validation_summary: str
    preclinical_evidence_strength: str  # STRONG, MODERATE, WEAK
    resistance_risk_notes: str
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)


class BiostatAudit(BaseModel):
    trial_design_rigor: str  # HIGH, MODERATE, LOW
    endpoint_quality: str  # HARD_CLINICAL, SURROGATE_VALIDATED, SURROGATE_UNVALIDATED
    endpoint_analysis: str
    power_and_sample_size_assessment: str
    control_arm_critique: str
    blinding_rigor: str
    red_flags: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)


class FinancialCatalystAudit(BaseModel):
    runway_vs_readout_alignment: str  # SAFE_BUFFER, TIGHT, DILUTION_IMMINENT
    binary_risk_exposure: str  # PURE_BINARY_PLAY, MODERATE_PIPELINE_BUFFER, HIGHLY_DIVERSIFIED
    commercial_market_opportunity: str
    asymmetry_ratio: str  # FAVORABLE, BALANCED, UNFAVORABLE
    projected_dilution_window: Optional[str] = None
    p10_readout_months: Optional[float] = None
    p50_readout_months: Optional[float] = None
    p90_readout_months: Optional[float] = None
    dilution_probability_before_readout: Optional[float] = None  # Estimated probability 0.0 - 1.0 of cash exhaustion before data
    slippage_risk_factors: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)


class DiligenceReport(BaseModel):
    id: Optional[int] = None
    nct_id: str
    trial_title: str
    sponsor: str
    ticker: Optional[str] = None
    molecular_analysis: MolecularAnalysis
    biostat_audit: BiostatAudit
    financial_audit: FinancialCatalystAudit
    consensus_verdict: ConsensusVerdict
    overall_score: float = Field(ge=0.0, le=100.0)
    scoring_audit_trail: List[str] = Field(default_factory=list)
    executive_summary: str
    key_catalysts: List[str] = Field(default_factory=list)
    critical_risks: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
