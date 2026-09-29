"""OpenFDA API Client.

Interrogates FDA regulatory databases for prior drug approvals, application types (NDA, BLA, ANDA),
and adverse event safety signals.
"""

import requests
from typing import Dict, Any, Optional, List
from core.config import OPENFDA_BASE_URL, DEFAULT_TIMEOUT_SEC
from core.http_client import get_retry_session


class OpenFDAClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT_SEC):
        self.base_url = OPENFDA_BASE_URL
        self.timeout = timeout
        self.session = get_retry_session()
        self.session.headers.update({
            "User-Agent": "BioCatalyst-FDA-Monitor/1.0"
        })

    def search_approvals(self, drug_name: str) -> List[Dict[str, Any]]:
        """Searches Drugs@FDA for approved products matching a brand or generic name."""
        if not drug_name:
            return []

        url = f"{self.base_url}/drugsfda.json"
        clean_name = drug_name.strip()
        params = {
            "search": f'openfda.brand_name:"{clean_name}" OR openfda.generic_name:"{clean_name}"',
            "limit": 5
        }

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = []
            for item in data.get("results", []):
                sponsor = item.get("sponsor_name", "Unknown")
                app_num = item.get("application_number", "")
                products = []
                for p in item.get("products", []):
                    products.append({
                        "brand_name": p.get("brand_name"),
                        "dosage_form": p.get("dosage_form"),
                        "route": p.get("route"),
                        "marketing_status": p.get("marketing_status")
                    })
                results.append({
                    "application_number": app_num,
                    "sponsor_name": sponsor,
                    "products": products
                })
            return results
        except Exception:
            return []

    def check_adverse_events_count(self, drug_name: str) -> Optional[int]:
        """Queries OpenFDA FAERS (Adverse Event Reporting System) count for a drug name."""
        if not drug_name:
            return None

        url = f"{self.base_url}/event.json"
        params = {
            "search": f'patient.drug.medicinalproduct:"{drug_name.strip().upper()}"',
            "count": "receivedate"
        }
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                total_events = sum(item.get("count", 0) for item in data.get("results", []))
                return total_events
            return None
        except Exception:
            return None
