"""Unit tests for financial solvency and runway calculations."""

import pytest
import pandas as pd
from unittest.mock import MagicMock
from core.models import DilutionRiskLevel
from clients.market_data import MarketDataClient


def test_runway_calculation_logic():
    client = MarketDataClient()

    # Case 1: Standard pre-revenue biotech (Cash: $100M, Burn: $25M/qtr)
    # Runway = ($100M / $25M) * 3 = 12 months -> MODERATE
    info = {"operatingCashflow": -100_000_000}
    
    yt_mock = MagicMock()
    yt_mock.quarterly_cashflow = None
    
    burn, runway, risk, freshness = client._compute_runway_and_burn(yt_mock, info, 100_000_000)
    assert burn == 25_000_000
    assert runway == 12.0
    assert risk == DilutionRiskLevel.MODERATE

    # Case 2: Critical dilution danger (Cash: $20M, Burn: $20M/qtr)
    # Runway = ($20M / $20M) * 3 = 3 months -> CRITICAL
    info = {"operatingCashflow": -80_000_000}
    burn, runway, risk, freshness = client._compute_runway_and_burn(yt_mock, info, 20_000_000)
    assert burn == 20_000_000
    assert runway == 3.0
    assert risk == DilutionRiskLevel.CRITICAL

    # Case 3: Profitable / Cash flow positive (Cash: $500M, operatingCashflow: +$100M)
    # Runway = 999.0 (indefinite) -> LOW
    info = {"operatingCashflow": 100_000_000}
    burn, runway, risk, freshness = client._compute_runway_and_burn(yt_mock, info, 500_000_000)
    assert burn == 0.0
    assert runway == 999.0
    assert risk == DilutionRiskLevel.LOW


def test_median_runway_with_milestone_spike():
    client = MarketDataClient()
    
    yt_mock = MagicMock()
    
    # Simulate a dataframe with a recent milestone payment spiking cash flow
    # Quarter 1 (most recent): +$100M, Quarter 2: -$30M, Quarter 3: -$30M, Quarter 4: -$30M
    mock_qcf = pd.DataFrame({
        "Q1": [100_000_000],
        "Q2": [-30_000_000],
        "Q3": [-30_000_000],
        "Q4": [-30_000_000],
    }, index=["Operating Cash Flow"])
    
    yt_mock.quarterly_cashflow = mock_qcf
    
    # Without median smoothing, the $100M spike would make the system think it's 
    # cash flow positive. With median smoothing, it should correctly identify the -$30M core burn.
    info = {} # Information doesn't matter if QCF exists
    burn, runway, risk, freshness = client._compute_runway_and_burn(yt_mock, info, 90_000_000)
    
    assert burn == 30_000_000
    assert runway == 9.0  # (90M / 30M) * 3
    assert risk == DilutionRiskLevel.HIGH
from datetime import datetime, timedelta, timezone

def test_data_freshness_warning():
    client = MarketDataClient()
    yt_mock = MagicMock()
    
    # Simulate a dataframe with a timestamp older than 105 days
    stale_date = datetime.now(timezone.utc) - timedelta(days=120)
    mock_qcf = pd.DataFrame({
        stale_date: [-30_000_000],
    }, index=["Operating Cash Flow"])
    
    yt_mock.quarterly_cashflow = mock_qcf
    info = {}
    
    burn, runway, risk, freshness = client._compute_runway_and_burn(yt_mock, info, 90_000_000)
    
    assert freshness is not None
    assert "Financial data is stale" in freshness

from agents.financial_agent import FinancialCatalystAgent
from core.models import ClinicalTrial, CompanyFinancials, DilutionRiskLevel


def _make_trial(phases=None, completion_date="2027-06-01", completion_date_type="ESTIMATED"):
    return ClinicalTrial(
        nct_id="NCT0000001",
        title="Test Trial",
        sponsor_name="Test Pharma",
        phases=phases or ["PHASE2"],
        primary_completion_date=completion_date,
        primary_completion_date_type=completion_date_type,
    )


def _make_financials(runway_months=None, burn_rate=None, mcap=500_000_000):
    return CompanyFinancials(
        ticker="TEST",
        company_name="Test Pharma Inc.",
        total_liquid_cash=100_000_000,
        quarterly_burn_rate=burn_rate,
        cash_runway_months=runway_months,
        dilution_risk_level=DilutionRiskLevel.MODERATE,
        market_cap=mcap
    )


def test_unknown_runway_is_not_silently_assumed_funded():
    """Critical: if runway_months is None, the agent must NOT treat it as 12 months funded."""
    agent = FinancialCatalystAgent()
    trial = _make_trial()
    # cash_runway_months=None means we couldn't compute it (no burn data)
    financials = _make_financials(runway_months=None, burn_rate=None)
    result = agent._heuristic_analysis(trial, financials)
    # Should NOT return SAFE_BUFFER for unknown runway
    assert result.runway_vs_readout_alignment != "SAFE_BUFFER", (
        "Unknown runway must not be classified as SAFE_BUFFER."
    )
    assert "WARNING" in (result.projected_dilution_window or ""), (
        "Unknown runway must surface a warning in the dilution window text."
    )
    # Confidence should be lower due to missing data
    assert result.confidence_score < 0.80, (
        "Confidence should degrade significantly when both runway and burn are unknown."
    )


def test_pure_binary_safe_buffer_is_favorable():
    """Small-cap fully funded through readout = genuine FAVORABLE asymmetry."""
    agent = FinancialCatalystAgent()
    # Readout 12 months out, runway 30 months
    trial = _make_trial(completion_date="2027-09-01", completion_date_type="ACTUAL")
    financials = _make_financials(runway_months=30.0, burn_rate=5_000_000, mcap=200_000_000)
    result = agent._heuristic_analysis(trial, financials)
    assert result.binary_risk_exposure == "PURE_BINARY_PLAY"
    assert result.runway_vs_readout_alignment == "SAFE_BUFFER"
    assert result.asymmetry_ratio == "FAVORABLE", (
        "A small-cap fully funded through readout is a high-reward asymmetric bet."
    )


def test_dilution_imminent_is_always_unfavorable():
    """DILUTION_IMMINENT always overrides to UNFAVORABLE regardless of market cap."""
    agent = FinancialCatalystAgent()
    # Runway: 3 months, readout: 20 months out
    trial = _make_trial(completion_date="2028-06-01", completion_date_type="ESTIMATED")
    financials = _make_financials(runway_months=3.0, burn_rate=10_000_000, mcap=20_000_000_000)
    result = agent._heuristic_analysis(trial, financials)
    assert result.runway_vs_readout_alignment == "DILUTION_IMMINENT"
    assert result.asymmetry_ratio == "UNFAVORABLE"

def test_short_term_debt_cliff_elevation():
    """MarketDataClient elevates risk to CRITICAL when short-term debt exceeds total cash."""
    client = MarketDataClient()
    yt_mock = MagicMock()
    yt_mock.quarterly_cashflow = None
    info = {"operatingCashflow": -40_000_000}
    # Cash , burn /qtr (15mo runway), but  short-term debt due <1yr
    burn, runway, risk, freshness = client._compute_runway_and_burn(
        yt_mock, info, total_cash=50_000_000, short_term_debt=60_000_000
    )
    assert risk == DilutionRiskLevel.CRITICAL, "Debt exceeding total cash must trigger CRITICAL dilution risk."


def test_financial_agent_debt_cliff():
    """FinancialCatalystAgent flags debt cliff as DILUTION_IMMINENT and UNFAVORABLE."""
    agent = FinancialCatalystAgent()
    trial = _make_trial(completion_date="2027-06-01")
    financials = CompanyFinancials(
        ticker="TEST",
        company_name="Test Pharma",
        total_liquid_cash=50_000_000,
        quarterly_burn_rate=5_000_000,
        cash_runway_months=30.0,
        short_term_debt=55_000_000,  # Debt cliff > cash
        market_cap=200_000_000
    )
    result = agent._heuristic_analysis(trial, financials)
    assert result.runway_vs_readout_alignment == "DILUTION_IMMINENT"
    assert result.asymmetry_ratio == "UNFAVORABLE"
    assert "DEBT CLIFF" in (result.projected_dilution_window or "")


def test_financial_agent_terminated_trial():
    """FinancialCatalystAgent handles terminated protocols as UNFAVORABLE with zero ongoing catalyst."""
    agent = FinancialCatalystAgent()
    trial = ClinicalTrial(
        nct_id="NCT0000002",
        title="Terminated Trial",
        sponsor_name="Test Pharma",
        phases=["PHASE3"],
        status="TERMINATED"
    )
    financials = _make_financials(runway_months=36.0, burn_rate=5_000_000)
    result = agent._heuristic_analysis(trial, financials)
    assert result.asymmetry_ratio == "UNFAVORABLE"
    assert result.runway_vs_readout_alignment == "DILUTION_IMMINENT"
    assert "TERMINATED" in result.commercial_market_opportunity


def test_probabilistic_catalyst_timing_event_driven():
    """Event-driven primary endpoints must expand slippage variance (higher P50 and P90)."""
    from core.models import Endpoint
    agent = FinancialCatalystAgent()
    # Trial A: Fixed endpoint (e.g. LDL reduction)
    trial_fixed = ClinicalTrial(
        nct_id="NCT0010001",
        title="Cholesterol Trial",
        sponsor_name="CardioPharma",
        phases=["PHASE3"],
        primary_completion_date="2027-06-01",
        primary_completion_date_type="ESTIMATED",
        primary_endpoints=[Endpoint(title="Change in LDL-C at 12 Weeks")]
    )
    # Trial B: Event-driven endpoint (Overall Survival)
    trial_event = ClinicalTrial(
        nct_id="NCT0010002",
        title="Oncology Survival Trial",
        sponsor_name="OncoPharma",
        phases=["PHASE3"],
        primary_completion_date="2027-06-01",
        primary_completion_date_type="ESTIMATED",
        primary_endpoints=[Endpoint(title="Overall Survival")]
    )
    fin = _make_financials(runway_months=24.0, burn_rate=5_000_000)

    res_fixed = agent._heuristic_analysis(trial_fixed, fin)
    res_event = agent._heuristic_analysis(trial_event, fin)

    assert res_fixed.p50_readout_months is not None
    assert res_event.p50_readout_months is not None
    # Event-driven endpoint must have higher expected completion and wider P90 horizon
    assert res_event.p50_readout_months > res_fixed.p50_readout_months
    assert res_event.p90_readout_months > res_fixed.p90_readout_months
    assert any("Event-driven" in factor for factor in res_event.slippage_risk_factors)


def test_probabilistic_dilution_probability_triggers_dilution_imminent():
    """When runway runs out before P50/P90, dilution_probability must be high and trigger DILUTION_IMMINENT."""
    agent = FinancialCatalystAgent()
    # Readout estimated ~12 months out. With Phase 3 slippage, P50 is ~18mo, P90 is ~21mo.
    trial = _make_trial(phases=["PHASE3"], completion_date="2027-06-01", completion_date_type="ESTIMATED")
    # Runway is 10 months (less than P50)
    financials = _make_financials(runway_months=10.0, burn_rate=10_000_000, mcap=300_000_000)

    res = agent._heuristic_analysis(trial, financials)
    assert res.runway_vs_readout_alignment == "DILUTION_IMMINENT"
    assert res.dilution_probability_before_readout is not None
    assert res.dilution_probability_before_readout >= 0.65
    assert res.asymmetry_ratio == "UNFAVORABLE"


def test_data_locked_actual_date_has_zero_slippage_uncertainty():
    """ACTUAL completion dates must have 0.0 uncertainty for P10, P50, and P90."""
    agent = FinancialCatalystAgent()
    trial = _make_trial(phases=["PHASE3"], completion_date="2026-01-01", completion_date_type="ACTUAL")
    financials = _make_financials(runway_months=18.0, burn_rate=5_000_000, mcap=500_000_000)

    res = agent._heuristic_analysis(trial, financials)
    assert res.p10_readout_months == 0.0
    assert res.p50_readout_months == 0.0
    assert res.p90_readout_months == 0.0
    assert res.dilution_probability_before_readout == 0.0
    assert res.runway_vs_readout_alignment == "SAFE_BUFFER"


def test_concentrated_midcap_biotech_is_classified_pure_binary_play():
    """A $3B market cap biotech with single lead asset focus must NOT be falsely classified as diversified."""
    agent = FinancialCatalystAgent()
    trial = ClinicalTrial(
        nct_id="NCT0020001",
        title="Pivotal Metabolic Study",
        sponsor_name="Viking Therapeutics, Inc.",
        phases=["PHASE3"],
        primary_completion_date="2027-12-01",
        primary_completion_date_type="ESTIMATED"
    )
    # $3.5B market cap mid-cap biotech
    financials = _make_financials(runway_months=30.0, burn_rate=15_000_000, mcap=3_500_000_000)

    res = agent._heuristic_analysis(trial, financials)
    assert res.binary_risk_exposure == "PURE_BINARY_PLAY", (
        "Viking Therapeutics has valuation concentrated in lead incretin asset; must be PURE_BINARY_PLAY."
    )
    assert "concentrated in lead program" in res.commercial_market_opportunity
