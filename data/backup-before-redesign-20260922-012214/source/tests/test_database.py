"""Unit tests for SQLite DatabaseManager."""

import pytest
from core.db import DatabaseManager
from core.models import ClinicalTrial, CompanyFinancials, DilutionRiskLevel


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_biocatalyst.db"
    db = DatabaseManager(db_path=str(db_file))
    return db


def test_upsert_and_get_trial(temp_db):
    trial = ClinicalTrial(
        nct_id="NCT00001111",
        title="Sample Phase 2 Trial",
        phases=["Phase 2"],
        sponsor_name="ModernaTX, Inc.",
        matched_ticker="MRNA",
        primary_completion_date="2027-06-30",
        estimated_catalyst_window="Q2 2027"
    )
    temp_db.upsert_trial(trial)

    retrieved = temp_db.get_trial("NCT00001111")
    assert retrieved is not None
    assert retrieved.nct_id == "NCT00001111"
    assert retrieved.matched_ticker == "MRNA"
    assert retrieved.estimated_catalyst_window == "Q2 2027"


def test_upsert_and_get_financials(temp_db):
    fin = CompanyFinancials(
        ticker="MRNA",
        company_name="Moderna, Inc.",
        market_cap=60000000000.0,
        total_liquid_cash=5000000000.0,
        quarterly_burn_rate=500000000.0,
        cash_runway_months=30.0,
        dilution_risk_level=DilutionRiskLevel.LOW
    )
    temp_db.upsert_financials(fin)

    retrieved = temp_db.get_financials("MRNA")
    assert retrieved is not None
    assert retrieved.ticker == "MRNA"
    assert retrieved.cash_runway_months == 30.0
    assert retrieved.dilution_risk_level == DilutionRiskLevel.LOW


def test_watchlist_operations(temp_db):
    # Add
    assert temp_db.add_to_watchlist("MRNA", "TICKER", alias="Moderna", notes="mRNA platform leader")
    assert temp_db.add_to_watchlist("NCT00001111", "NCT", alias="Phase 2 trial")

    wl = temp_db.get_watchlist()
    assert len(wl) == 2

    # Remove
    assert temp_db.remove_from_watchlist("MRNA")
    wl_after = temp_db.get_watchlist()
    assert len(wl_after) == 1
    assert wl_after[0]["identifier"] == "NCT00001111"
