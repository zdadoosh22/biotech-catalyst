"""ClinicalTrials.gov API v2 client.

Fetches clinical study protocols, endpoints, interventions, timelines,
and parses them into structured ClinicalTrial models.
"""

import requests
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.models import ClinicalTrial, Endpoint, Intervention
from core.config import CLINICAL_TRIALS_API_URL, DEFAULT_TIMEOUT_SEC
from core.http_client import get_retry_session
from core.protocol_validator import validate_trial_integrity
from clients.sponsor_matcher import SponsorMatcher


class ClinicalTrialsClient:
    def __init__(self, matcher: Optional[SponsorMatcher] = None, timeout: int = DEFAULT_TIMEOUT_SEC):
        self.base_url = CLINICAL_TRIALS_API_URL
        self.matcher = matcher or SponsorMatcher()
        self.timeout = timeout
        self.session = get_retry_session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "BioCatalyst-Intelligence-Engine/2.0"
        })
        self._last_request_time = 0.0
        self._min_request_interval = 0.5

    def _rate_limit(self):
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def fetch_trial_by_nct(self, nct_id: str) -> Optional[ClinicalTrial]:
        """Fetches a single clinical study by NCT identifier."""
        clean_id = nct_id.strip().upper()
        url = f"{self.base_url}/{clean_id}"
        try:
            self._rate_limit()
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                return self._fetch_via_query(clean_id)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_study(data)
        except Exception:
            return self._fetch_via_query(clean_id)

    def search_trials(
        self,
        query: Optional[str] = None,
        condition: Optional[str] = None,
        sponsor: Optional[str] = None,
        intervention: Optional[str] = None,
        phases: Optional[List[str]] = None,
        status: Optional[str] = None,
        page_size: int = 20,
        page_token: Optional[str] = None
    ) -> List[ClinicalTrial]:
        """Searches clinical studies with modular filtering."""
        params: Dict[str, Any] = {"pageSize": min(page_size, 50)}

        term_parts = []
        if query:
            term_parts.append(query)
        if sponsor:
            term_parts.append(sponsor)

        if term_parts:
            params["query.term"] = " ".join(term_parts)
        if condition:
            params["query.cond"] = condition
        if intervention:
            params["query.intr"] = intervention

        # Status filter (ClinicalTrials.gov v2 uses pipe delimiter for multiple statuses)
        if status:
            params["filter.overallStatus"] = status
        else:
            params["filter.overallStatus"] = "RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION"

        if page_token:
            params["pageToken"] = page_token

        try:
            self._rate_limit()
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            studies_raw = data.get("studies", [])
            results = []
            for study in studies_raw:
                parsed = self._parse_study(study)
                if parsed:
                    # Filter by phase if specified
                    if phases:
                        trial_phases = [p.lower() for p in parsed.phases]
                        wanted_phases = [p.lower() for p in phases]
                        if not any(wp in " ".join(trial_phases) for wp in wanted_phases):
                            continue
                    results.append(parsed)
            return results
        except Exception:
            return []

    def _fetch_via_query(self, nct_id: str) -> Optional[ClinicalTrial]:
        try:
            self._rate_limit()
            resp = self.session.get(f"{self.base_url}?query.term={nct_id}&pageSize=1", timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            studies = data.get("studies", [])
            if studies:
                return self._parse_study(studies[0])
            return None
        except Exception:
            return None

    def _parse_study(self, data: Dict[str, Any]) -> Optional[ClinicalTrial]:
        try:
            protocol = data.get("protocolSection", {})
            if not protocol:
                return None

            ident = protocol.get("identificationModule", {})
            nct_id = ident.get("nctId", "")
            title = ident.get("briefTitle") or ident.get("officialTitle", "Untitled Study")
            official_title = ident.get("officialTitle")

            status_mod = protocol.get("statusModule", {})
            status = status_mod.get("overallStatus", "UNKNOWN")
            
            # Dates and their actual/estimated types
            start_date_struct = status_mod.get("startDateStruct", {})
            start_date = start_date_struct.get("date")
            start_date_type = start_date_struct.get("type", "UNKNOWN")
            
            pcd_struct = status_mod.get("primaryCompletionDateStruct", {})
            primary_completion_date = pcd_struct.get("date")
            primary_completion_date_type = pcd_struct.get("type", "UNKNOWN")
            
            cd_struct = status_mod.get("completionDateStruct", {})
            completion_date = cd_struct.get("date")
            completion_date_type = cd_struct.get("type", "UNKNOWN")
            
            last_updated = status_mod.get("lastUpdateSubmitDate") or status_mod.get("lastUpdatePostDateStruct", {}).get("date")

            sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
            lead_sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "Unknown Sponsor")
            collabs = [c.get("name") for c in sponsor_mod.get("collaborators", []) if c.get("name")]

            desc_mod = protocol.get("descriptionModule", {})
            brief_summary = desc_mod.get("briefSummary", "")
            detailed_description = desc_mod.get("detailedDescription")

            cond_mod = protocol.get("conditionsModule", {})
            conditions = cond_mod.get("conditions", [])

            design_mod = protocol.get("designModule", {})
            phases = design_mod.get("phases", [])
            study_type = design_mod.get("studyType", "INTERVENTIONAL")
            design_info = design_mod.get("designInfo", {})
            allocation = design_info.get("allocation")
            intervention_model = design_info.get("interventionModel")
            masking_info = design_info.get("maskingInfo", {})
            masking = masking_info.get("masking")
            enrollment = design_mod.get("enrollmentInfo", {}).get("count")

            arms_mod = protocol.get("armsInterventionsModule", {})
            interventions = []
            for inter in arms_mod.get("interventions", []):
                interventions.append(Intervention(
                    name=inter.get("name", "Unknown Intervention"),
                    type=inter.get("type", "DRUG"),
                    description=inter.get("description", "")
                ))

            outcomes_mod = protocol.get("outcomesModule", {})
            primary_endpoints = []
            for po in outcomes_mod.get("primaryOutcomes", []):
                primary_endpoints.append(Endpoint(
                    title=po.get("measure", "Primary Outcome"),
                    description=po.get("description", ""),
                    time_frame=po.get("timeFrame", ""),
                    is_primary=True,
                    hierarchy="PRIMARY"
                ))

            secondary_endpoints = []
            for so in outcomes_mod.get("secondaryOutcomes", []):
                title = so.get("measure", "Secondary Outcome")
                desc = so.get("description", "")
                
                combined_text = f"{title} {desc}".lower()
                if any(x in combined_text for x in ["exploratory", "pharmacokinet", "pharmacodynam", " pk ", " pd "]):
                    hier = "EXPLORATORY"
                elif "key secondary" in combined_text or "key" in title.lower():
                    hier = "KEY_SECONDARY"
                else:
                    hier = "SECONDARY"

                secondary_endpoints.append(Endpoint(
                    title=title,
                    description=desc,
                    time_frame=so.get("timeFrame", ""),
                    is_primary=False,
                    hierarchy=hier
                ))

            # Calculate estimated catalyst window (quarter and year)
            # Differentiate if it's already actual vs estimated.
            if primary_completion_date_type == "ACTUAL" and primary_completion_date:
                estimated_window = f"Historical (Data Locked: {primary_completion_date})"
            else:
                estimated_window = self._calculate_catalyst_window(primary_completion_date or completion_date)

            # Resolve ticker
            ticker, _ = self.matcher.match_sponsor(lead_sponsor)
            if not ticker and collabs:
                for collab in collabs:
                    t_collab, _ = self.matcher.match_sponsor(collab)
                    if t_collab:
                        ticker = t_collab
                        break

            return ClinicalTrial(
                nct_id=nct_id,
                title=title,
                official_title=official_title,
                brief_summary=brief_summary,
                detailed_description=detailed_description,
                phases=phases,
                status=status,
                sponsor_name=lead_sponsor,
                collaborators=collabs,
                conditions=conditions,
                interventions=interventions,
                primary_endpoints=primary_endpoints,
                secondary_endpoints=secondary_endpoints,
                enrollment=enrollment,
                start_date=start_date,
                start_date_type=start_date_type,
                primary_completion_date=primary_completion_date,
                primary_completion_date_type=primary_completion_date_type,
                completion_date=completion_date,
                completion_date_type=completion_date_type,
                study_type=study_type,
                allocation=allocation,
                intervention_model=intervention_model,
                masking=masking,
                estimated_catalyst_window=estimated_window,
                matched_ticker=ticker,
                last_updated=last_updated
            )
            trial.data_integrity_warnings = validate_trial_integrity(trial)
            return trial
        except Exception:
            return None

    @staticmethod
    def _calculate_catalyst_window(date_str: Optional[str]) -> Optional[str]:
        """Extracts Quarter and Year from date strings like '2026-11-15' or 'November 2026'."""
        if not date_str:
            return None

        clean = date_str.strip()

        # Handle YYYY-MM or YYYY-MM-DD
        iso_match = re.match(r"^(\d{4})-(\d{1,2})", clean)
        if iso_match:
            year = int(iso_match.group(1))
            month = int(iso_match.group(2))
            quarter = (month - 1) // 3 + 1
            return f"Q{quarter} {year}"

        # Handle "Month YYYY" e.g., "October 2026"
        month_names = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        for name, month_num in month_names.items():
            if name in clean.lower():
                yr_match = re.search(r"\b(20\d\d)\b", clean)
                if yr_match:
                    year = int(yr_match.group(1))
                    quarter = (month_num - 1) // 3 + 1
                    return f"Q{quarter} {year}"

        # Just year if nothing else
        yr_only = re.search(r"\b(20\d\d)\b", clean)
        if yr_only:
            return f"FY {yr_only.group(1)}"

        return clean
