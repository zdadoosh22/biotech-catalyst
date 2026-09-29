"""Automated Clinical Protocol Data Integrity and Consistency Validator.

Inspects ClinicalTrials.gov registered protocol records for contradictions,
misclassified phases, delinquent timelines, and design incongruities.
"""

import re
from datetime import datetime, timezone
from typing import List
from core.models import ClinicalTrial


def validate_trial_integrity(trial: ClinicalTrial) -> List[str]:
    """Scans a clinical trial record for internal registration contradictions."""
    warnings: List[str] = []

    title_text = f"{(trial.title or '')} {(trial.official_title or '')} {(trial.brief_summary or '')}".lower()
    phases_upper = [p.upper() for p in trial.phases]

    # 1. Phase Discrepancy Checks
    has_p3_claim = any(k in title_text for k in ["phase 3", "phase iii", "pivotal", "registrational"])
    has_p1_claim = any(k in title_text for k in ["phase 1", "phase i", "first-in-human", "dose escalation"]) and not any(
        k in title_text for k in ["phase 1/2", "phase 1b/2", "phase i/ii", "phase 2/3", "phase ii/iii"]
    )

    if has_p3_claim and phases_upper and not any("3" in p for p in phases_upper):
        warnings.append(
            f"Phase discrepancy: Protocol title/summary indicates Phase 3 or pivotal intent, "
            f"but registered design phase is {', '.join(trial.phases)}."
        )

    if has_p1_claim and any("3" in p for p in phases_upper):
        warnings.append(
            "Phase discrepancy: Title indicates early Phase 1 first-in-human dose escalation, "
            "but registered design phase is Phase 3."
        )

    # 2. Status vs Timeline Contradictions
    status_upper = (trial.status or "").upper()

    if status_upper == "COMPLETED" and trial.primary_completion_date_type == "ESTIMATED":
        warnings.append(
            "Timeline contradiction: Protocol status is marked COMPLETED, "
            "but primary completion date type is still listed as ESTIMATED."
        )

    if status_upper in ["RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"]:
        if trial.primary_completion_date:
            parts = trial.primary_completion_date.split("-")
            if len(parts) >= 1 and parts[0].isdigit():
                try:
                    yr = int(parts[0])
                    mo = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 6
                    now = datetime.now(timezone.utc)
                    diff_months = (yr - now.year) * 12 + (mo - now.month)
                    if diff_months < -6.0:
                        warnings.append(
                            f"Delinquent timeline: Study status is active ({trial.status}), "
                            f"but primary completion date passed {abs(diff_months):.0f} months ago "
                            f"({trial.primary_completion_date}) without an updated completion or results status."
                        )
                except Exception:
                    pass

    # 3. Design Allocation vs Intervention Model Contradictions
    alloc_upper = (trial.allocation or "").upper()
    model_upper = (trial.intervention_model or "").upper()
    mask_upper = (trial.masking or "").upper()

    if alloc_upper == "RANDOMIZED" and model_upper in ["SINGLE_GROUP", "SINGLE GROUP"]:
        warnings.append(
            "Design contradiction: Allocation is registered as RANDOMIZED, "
            "but intervention model is specified as SINGLE_GROUP (single-arm studies cannot be randomized)."
        )

    if mask_upper in ["QUADRUPLE", "TRIPLE", "DOUBLE"] and model_upper in ["SINGLE_GROUP", "SINGLE GROUP"]:
        warnings.append(
            f"Blinding contradiction: Masking is registered as {mask_upper}, "
            f"but intervention model is SINGLE_GROUP with no comparator arm."
        )

    # 4. Endpoint vs Phase Incongruity
    if any("3" in p for p in phases_upper) and trial.primary_endpoints:
        all_ep_text = " ".join(f"{(ep.title or '')} {(ep.description or '')}" for ep in trial.primary_endpoints).lower()
        has_safety_keywords = any(k in all_ep_text for k in [
            "safety", "tolerability", "adverse events", "maximum tolerated dose", "mtd", "pharmacokinetics", "dose limiting"
        ])
        has_efficacy_keywords = any(k in all_ep_text for k in [
            "overall survival", "survival", "pfs", "response rate", "orr", "complete response", "remission",
            "disease-free", "dfs", "event-free", "efs", "hba1c", "change from baseline", "fev1", "efficacy"
        ])
        if has_safety_keywords and not has_efficacy_keywords:
            warnings.append(
                "Methodology incongruity: Study is registered as a pivotal Phase 3 trial, "
                "but primary endpoint measures exclusively assess safety, tolerability, or PK "
                "without pre-specified formal efficacy endpoints."
            )

    # 5. Enrollment Anomaly
    if status_upper in ["RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED"]:
        if trial.enrollment is not None and trial.enrollment == 0:
            warnings.append(
                f"Enrollment anomaly: Study status is active/completed ({trial.status}), "
                f"but target enrollment count is registered as 0."
            )
        elif trial.enrollment is not None and trial.enrollment < 20 and any("3" in p for p in phases_upper):
            cond_text = " ".join(trial.conditions).lower()
            if not any(k in cond_text for k in ["rare", "orphan", "pediatric"]):
                warnings.append(
                    f"Under-enrollment anomaly: Phase 3 trial registered with only N={trial.enrollment} "
                    f"target enrollment in a non-orphan indication."
                )

    return warnings
