"""Unit tests for ClinicalTrialsClient."""

import pytest
from clients.clinical_trials import ClinicalTrialsClient


def test_calculate_catalyst_window():
    client = ClinicalTrialsClient(timeout=1)
    
    # Standard Date
    assert client._calculate_catalyst_window("2026-11-15") == "Q4 2026"
    assert client._calculate_catalyst_window("2026-01-01") == "Q1 2026"
    assert client._calculate_catalyst_window("2028-06-30") == "Q2 2028"
    assert client._calculate_catalyst_window("2029-07-01") == "Q3 2029"

    # Month Year format
    assert client._calculate_catalyst_window("November 2026") == "Q4 2026"
    assert client._calculate_catalyst_window("January 2024") == "Q1 2024"
    assert client._calculate_catalyst_window("May 2030") == "Q2 2030"

    # Year only format
    assert client._calculate_catalyst_window("2035") == "FY 2035"

    # Edge cases
    assert client._calculate_catalyst_window(None) is None
    assert client._calculate_catalyst_window("") is None


def test_parse_study_date_types():
    client = ClinicalTrialsClient(timeout=1)
    
    # Simulated JSON protocol section from CT.gov API v2
    mock_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT99999999",
                "briefTitle": "Mock Trial"
            },
            "statusModule": {
                "overallStatus": "RECRUITING",
                "primaryCompletionDateStruct": {
                    "date": "2027-10-15",
                    "type": "ESTIMATED"
                },
                "completionDateStruct": {
                    "date": "2028-12",
                    "type": "ACTUAL"
                }
            }
        }
    }
    
    trial = client._parse_study(mock_study)
    assert trial is not None
    assert trial.nct_id == "NCT99999999"
    assert trial.primary_completion_date == "2027-10-15"
    assert trial.primary_completion_date_type == "ESTIMATED"
    assert trial.completion_date == "2028-12"
    assert trial.completion_date_type == "ACTUAL"
    
    # It derived catalyst window from primary completion date which is estimated
    assert trial.estimated_catalyst_window == "Q4 2027"

def test_parse_study_actual_past_date():
    client = ClinicalTrialsClient(timeout=1)
    mock_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT88888888",
                "briefTitle": "Mock Trial 2"
            },
            "statusModule": {
                "overallStatus": "COMPLETED",
                "primaryCompletionDateStruct": {
                    "date": "2022-05",
                    "type": "ACTUAL"
                }
            }
        }
    }
    
    trial = client._parse_study(mock_study)
    assert trial is not None
    assert trial.primary_completion_date_type == "ACTUAL"
    # The catalyst window should be marked as actual/locked, not as a future forecast.
    assert "Historical" in trial.estimated_catalyst_window
    assert "2022-05" in trial.estimated_catalyst_window

def test_parse_study_endpoint_hierarchy():
    client = ClinicalTrialsClient(timeout=1)
    mock_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT77777777",
                "briefTitle": "Mock Trial 3"
            },
            "outcomesModule": {
                "primaryOutcomes": [
                    {"measure": "Overall Survival", "description": "Time to death"}
                ],
                "secondaryOutcomes": [
                    {"measure": "Key Secondary: Progression Free Survival", "description": "Time to progression"},
                    {"measure": "Quality of Life", "description": "Questionnaire score"},
                    {"measure": "Exploratory Biomarker", "description": "PD marker"}
                ]
            }
        }
    }
    
    trial = client._parse_study(mock_study)
    assert trial is not None
    assert len(trial.primary_endpoints) == 1
    assert trial.primary_endpoints[0].hierarchy == "PRIMARY"
    
    assert len(trial.secondary_endpoints) == 3
    assert trial.secondary_endpoints[0].hierarchy == "KEY_SECONDARY"
    assert trial.secondary_endpoints[1].hierarchy == "SECONDARY"
    assert trial.secondary_endpoints[2].hierarchy == "EXPLORATORY"
