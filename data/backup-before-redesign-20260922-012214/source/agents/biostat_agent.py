"""Clinical Biostatistician & Trial Methodology Auditor Agent.

Audits trial statistical power, sample sizes, blinding, control arms,
study status, and distinguishes hard clinical endpoints from surrogate/unvalidated markers.
"""

from typing import Optional, List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import ClinicalTrial, BiostatAudit
from core.protocol_validator import validate_trial_integrity


class BiostatisticianAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Dr. Marcus Thorne",
            role="Lead Regulatory Biostatistician & Clinical Trial Methodologist"
        )

    def analyze(self, trial: ClinicalTrial) -> BiostatAudit:
        """Audits trial statistical design, endpoints, and methodology."""
        # 1. Attempt Gemini Generation
        prompt = self._build_prompt(trial)
        llm_result = self.call_gemini(prompt)

        if llm_result:
            try:
                return BiostatAudit(
                    trial_design_rigor=llm_result.get("trial_design_rigor", "MODERATE"),
                    endpoint_quality=llm_result.get("endpoint_quality", "SURROGATE_VALIDATED"),
                    endpoint_analysis=llm_result.get("endpoint_analysis", ""),
                    power_and_sample_size_assessment=llm_result.get("power_and_sample_size_assessment", ""),
                    control_arm_critique=llm_result.get("control_arm_critique", ""),
                    blinding_rigor=llm_result.get("blinding_rigor", ""),
                    red_flags=llm_result.get("red_flags", []),
                    confidence_score=float(llm_result.get("confidence_score", 0.88))
                )
            except Exception:
                pass

        # 2. Fallback to Deterministic Biostatistical Auditor
        return self._heuristic_analysis(trial)

    def _build_prompt(self, trial: ClinicalTrial) -> str:
        pe_text = "\n".join([f"- [PRIMARY] {e.title} (Timeframe: {e.time_frame}): {e.description}" for e in trial.primary_endpoints])
        
        key_secondaries = [e for e in trial.secondary_endpoints if e.hierarchy == "KEY_SECONDARY"]
        exploratory = [e for e in trial.secondary_endpoints if e.hierarchy == "EXPLORATORY"]
        other = [e for e in trial.secondary_endpoints if e.hierarchy == "SECONDARY"]
        
        se_lines = []
        for e in key_secondaries:
            se_lines.append(f"- [KEY SECONDARY] {e.title} (Timeframe: {e.time_frame})")
        for e in other[:3]:
            se_lines.append(f"- [SECONDARY] {e.title} (Timeframe: {e.time_frame})")
        for e in exploratory[:2]:
            se_lines.append(f"- [EXPLORATORY] {e.title} (Timeframe: {e.time_frame})")
        
        se_text = "\n".join(se_lines) if se_lines else "None specified"

        return f"""
        You are {self.name}, {self.role}.
        Critique the statistical and regulatory design of this clinical trial:

        Trial ID: {trial.nct_id}
        Status: {trial.status}
        Phase: {", ".join(trial.phases)}
        Enrollment Target: {trial.enrollment or 'Unspecified'}
        Allocation: {trial.allocation or 'Unspecified'}
        Intervention Model: {trial.intervention_model or 'Unspecified'}
        Masking: {trial.masking or 'Unspecified'}
        Primary Endpoints:
        {pe_text}
        Secondary Endpoints:
        {se_text}

        Respond in strict JSON with the following schema:
        {{
            "trial_design_rigor": "HIGH" | "MODERATE" | "LOW",
            "endpoint_quality": "HARD_CLINICAL" | "SURROGATE_VALIDATED" | "SURROGATE_UNVALIDATED",
            "endpoint_analysis": "Detailed critique of whether primary endpoints satisfy FDA/EMA accelerated vs full approval requirements",
            "power_and_sample_size_assessment": "Assessment of sample size power for effect size detection",
            "control_arm_critique": "Critique of active comparator vs placebo vs single arm",
            "blinding_rigor": "Critique of blinding design (Double-blind vs open-label risks)",
            "red_flags": ["List of critical statistical or regulatory design vulnerabilities"],
            "confidence_score": 0.88
        }}
        """

    def _heuristic_analysis(self, trial: ClinicalTrial) -> BiostatAudit:
        red_flags: List[str] = []
        is_phase3 = any("3" in p for p in trial.phases)
        is_phase2 = any("2" in p for p in trial.phases)

        # 0. Study Status Audit (Critical Fatal & Regulatory Checks)
        status_upper = (trial.status or "UNKNOWN").upper()
        if status_upper == "TERMINATED":
            red_flags.append("TERMINAL TRIAL HALT: Study status is TERMINATED. Premature termination indicates severe toxicity, safety hold, programmatic abandonment, or statistical futility.")
        elif status_upper == "WITHDRAWN":
            red_flags.append("TRIAL WITHDRAWN: Study was withdrawn prior to enrolling participants; zero clinical efficacy or safety evidence can be generated.")
        elif status_upper == "SUSPENDED":
            red_flags.append("CLINICAL HOLD / SUSPENSION: Study status is SUSPENDED. High risk of regulatory safety intervention or unresolved adverse events.")

        # Check for Delinquent/Overdue Estimated Completion Date
        if trial.primary_completion_date_type == "ESTIMATED" and trial.primary_completion_date:
            try:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                clean_pcd = trial.primary_completion_date.strip()
                pcd_year, pcd_month = None, None
                import re
                m = re.match(r"^(\d{4})-(\d{1,2})", clean_pcd)
                if m:
                    pcd_year, pcd_month = int(m.group(1)), int(m.group(2))
                elif len(clean_pcd) == 4 and clean_pcd.isdigit():
                    pcd_year, pcd_month = int(clean_pcd), 12

                if pcd_year and pcd_month:
                    months_past = (now.year - pcd_year) * 12 + (now.month - pcd_month)
                    if months_past > 6 and status_upper in ["RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "UNKNOWN"]:
                        red_flags.append(
                            f"DELINQUENT TRIAL TIMELINE: Estimated completion date ({clean_pcd}) is {months_past} months in the past without study completion or protocol update, signaling substantial enrollment stall."
                        )
            except Exception:
                pass

        # Detect disease domain for adaptive logic across the audit
        conditions_combined = " ".join(trial.conditions).lower()
        is_rare_disease = any(kw in conditions_combined for kw in [
            "rare", "orphan", "genetic", "dystrophy", "fibrosis", "amyotrophic",
            "huntington", "pompe", "gaucher"
        ])
        is_oncology = any(kw in conditions_combined for kw in [
            "cancer", "tumor", "carcinoma", "leukemia", "lymphoma", "melanoma",
            "sarcoma", "oncology", "malignancy"
        ])

        # 1. Endpoint Analysis
        # Use multi-token phrases and word-boundary checks to avoid false substring matches.
        pe_combined = " ".join([f"{e.title} {e.description}".lower() for e in trial.primary_endpoints])
        pe_padded = f" {pe_combined} "

        def phrase_match(text: str, phrases: List[str]) -> bool:
            """Check if any phrase appears as a standalone word/phrase in the text."""
            import re
            for phrase in phrases:
                if len(phrase) <= 3:
                    if re.search(rf"\b{re.escape(phrase)}\b", text):
                        return True
                else:
                    if phrase in text:
                        return True
            return False

        hard_endpoint_keywords = [
            "overall survival", "all-cause mortality", "cardiovascular death",
            "recurrence-free survival", "rfs", "event-free survival", "efs",
            "relapse-free survival", "mortality",
        ]
        if phrase_match(pe_padded, hard_endpoint_keywords) or \
                (" os " in pe_padded and any(ctx in pe_padded for ctx in ["overall survival", "primary os", "os benefit", "os endpoint"])):
            endpoint_quality = "HARD_CLINICAL"
            endpoint_analysis = "Primary endpoint measures true hard clinical outcome (survival / mortality), optimal for full FDA/EMA standard approval."
        elif phrase_match(pe_padded, [
            "progression-free survival", "pfs", "disease-free survival", "dfs",
            "objective response rate", "orr", "hba1c", "weight loss", "body weight",
            "fev1", "lowering of ldl", "complete remission", "complete response",
            "pathological complete response", "pcr", "minimal residual disease", "mrd"
        ]):
            endpoint_quality = "SURROGATE_VALIDATED"
            endpoint_analysis = "Primary endpoint relies on clinically validated surrogate (PFS/ORR/Metabolic markers), eligible for accelerated approval but subject to confirmatory OS trial."
        else:
            endpoint_quality = "SURROGATE_UNVALIDATED"
            endpoint_analysis = "Primary endpoint relies on biomarker, pharmacodynamic or subjective symptom measures, presenting heightened regulatory scrutiny risk."
            red_flags.append("Primary outcome is exploratory or surrogate biomarker rather than definitive clinical benefit.")
        
        # Flag if NO endpoints are registered in the protocol
        if not trial.primary_endpoints:
            endpoint_quality = "SURROGATE_UNVALIDATED"
            endpoint_analysis = "No primary endpoints listed in protocol registry. This may indicate early-stage placeholder registration or data entry gap."
            red_flags.append("No primary endpoints registered in trial protocol.")
            
        # Hierarchy analysis
        key_secondaries = [e for e in trial.secondary_endpoints if e.hierarchy == "KEY_SECONDARY"]
        exploratory = [e for e in trial.secondary_endpoints if e.hierarchy == "EXPLORATORY"]
        
        if key_secondaries or exploratory:
            hierarchy_note = f" Protocol separates {len(key_secondaries)} key secondary endpoints from {len(exploratory)} exploratory measures."
            if not trial.primary_endpoints and key_secondaries:
                hierarchy_note += " Lacks primary endpoint, but designates key secondaries."
            endpoint_analysis += hierarchy_note

        # 2. Power and Sample Size
        enrollment = trial.enrollment or 0
        
        # Determine adequate power threshold based on domain
        if is_rare_disease:
            p3_threshold = 40
            p2_threshold = 15
            domain_context = "rare disease/orphan indication"
        elif is_oncology:
            p3_threshold = 150
            p2_threshold = 40
            domain_context = "oncology indication"
        else:
            p3_threshold = 300
            p2_threshold = 60
            domain_context = "broad indication"

        if is_phase3:
            if enrollment >= p3_threshold:
                power_assessment = f"Pivotal Phase 3 study with N={enrollment} is well-powered for a {domain_context}."
            elif enrollment > 0:
                power_assessment = f"Phase 3 study with N={enrollment} may be underpowered for a {domain_context} unless effect size is exceptionally large."
                red_flags.append(f"Phase 3 enrollment (N={enrollment}) is below standard statistical power thresholds for a {domain_context} (expected >{p3_threshold}).")
            else:
                power_assessment = "Enrollment count unspecified in registry; power cannot be independently verified."
                red_flags.append("Enrollment count unspecified in Phase 3 protocol.")
        elif is_phase2:
            if enrollment >= p2_threshold:
                power_assessment = f"Phase 2 signal-seeking cohort with N={enrollment} provides robust statistical discrimination for a {domain_context}."
            elif enrollment > 0:
                power_assessment = f"Phase 2 sample size N={enrollment} provides limited statistical power for a {domain_context} and higher vulnerability to baseline heterogeneity."
            else:
                power_assessment = "Phase 2 cohort size unspecified."
        else:
            power_assessment = f"Early phase exploration with N={enrollment} focused primarily on safety, tolerability, and MTD escalation."

        # 3. Blinding & Allocation
        masking = (trial.masking or "").lower()
        allocation = (trial.allocation or "").lower()

        if "double" in masking or "triple" in masking or "quadruple" in masking:
            blinding_rigor = "Double/multi-blinded protocol protects against investigator and patient reporting bias."
        elif "open" in masking or "none" in masking:
            blinding_rigor = "Open-label design increases vulnerability to investigator evaluation bias and placebo effects."
            if "randomized" not in allocation and is_phase3:
                red_flags.append("Open-label design in late-stage trial creates regulatory scrutiny on subjective endpoints.")
        else:
            blinding_rigor = "Masking protocol not explicitly defined in registry."

        # 4. Control Arm Critique & Trial Design
        model = (trial.intervention_model or "").lower()
        title_desc = f"{trial.title} {trial.brief_summary}".lower()
        
        is_basket = "basket" in title_desc
        is_umbrella = "umbrella" in title_desc or "platform" in title_desc
        
        design_note = ""
        if is_basket:
            design_note = " Master protocol (Basket design) identified; evaluates one targeted therapy across multiple diseases. High efficiency but risks confounding from disease heterogeneity."
        elif is_umbrella:
            design_note = " Master protocol (Umbrella/Platform design) identified; evaluates multiple targeted therapies for a single disease. Enables adaptive dropping/adding of arms."

        if "single" in model:
            control_arm = "Single-arm trial lacking an active control group; results will depend on historical control comparisons." + design_note
            if is_phase3 and not is_rare_disease:
                red_flags.append("Single-arm pivotal Phase 3 design poses severe regulatory approval barriers for non-orphan indications.")
        elif "crossover" in model or "cross-over" in model or "crossover" in title_desc or "cross-over" in title_desc:
            control_arm = "Crossover design identified. Active crossover allows control patients to switch to the experimental drug." + design_note
            if endpoint_quality == "HARD_CLINICAL":
                red_flags.append("Crossover design dilutes Overall Survival (OS) benefit, as control patients receive the active drug upon disease progression. OS may appear statistically non-significant despite true biological efficacy.")
                endpoint_analysis += " Note: OS endpoint is severely confounded by crossover design; regulators may rely more on PFS."
        elif "parallel" in model and "randomized" in allocation:
            control_arm = "Randomized parallel assignment against active standard of care or matched placebo." + design_note
        else:
            control_arm = "Controlled design with standard allocation protocol." + design_note

        # Check Protocol Data Integrity & Registration Contradictions
        integrity_alerts = trial.data_integrity_warnings or validate_trial_integrity(trial)
        for alert in integrity_alerts:
            formatted_alert = f"Data Integrity Alert: {alert}"
            if formatted_alert not in red_flags:
                red_flags.append(formatted_alert)

        # Compute overall rigor
        if len(red_flags) == 0 and endpoint_quality in ("HARD_CLINICAL", "SURROGATE_VALIDATED"):
            design_rigor = "HIGH"
        elif len(red_flags) <= 1 and status_upper not in ["TERMINATED", "WITHDRAWN", "SUSPENDED"]:
            design_rigor = "MODERATE"
        else:
            design_rigor = "LOW"

        # Confidence degrades based on data availability, status flaws, and red flag count
        base_confidence = 0.90
        if status_upper in ["TERMINATED", "WITHDRAWN", "SUSPENDED"]:
            base_confidence -= 0.15
        if not trial.primary_endpoints:
            base_confidence -= 0.25
        if trial.enrollment is None:
            base_confidence -= 0.10
        if not trial.masking:
            base_confidence -= 0.05
        
        # Methodological rigor bonuses
        if key_secondaries:
            base_confidence += 0.05  # Explicit hierarchy implies pre-specified alpha spending

        base_confidence -= len(red_flags) * 0.04
        confidence = round(max(0.35, min(0.95, base_confidence)), 2)

        return BiostatAudit(
            trial_design_rigor=design_rigor,
            endpoint_quality=endpoint_quality,
            endpoint_analysis=endpoint_analysis,
            power_and_sample_size_assessment=power_assessment,
            control_arm_critique=control_arm,
            blinding_rigor=blinding_rigor,
            red_flags=red_flags,
            confidence_score=confidence
        )
