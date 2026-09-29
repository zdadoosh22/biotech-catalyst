"""Molecular Biology & Mechanism of Action (MoA) Analyst Agent.

Audits target biological plausibility, drug modality, preclinical literature,
and potential biological resistance pathways.
"""

import re
from typing import Optional, List, Dict, Any
from agents.base_agent import BaseAgent
from core.models import ClinicalTrial, MolecularAnalysis
from clients.uniprot import UniProtClient


class MolecularAnalystAgent(BaseAgent):
    def __init__(self, uniprot_client: Optional[UniProtClient] = None):
        super().__init__(
            name="Dr. Elena Vance",
            role="Principal Molecular Biologist & Target Validation Specialist"
        )
        self.uniprot_client = uniprot_client or UniProtClient()

    def analyze(self, trial: ClinicalTrial, literature: Optional[List[Dict[str, Any]]] = None) -> MolecularAnalysis:
        """Audits the molecular biology and mechanism of action."""
        # 1. Attempt Gemini Generation
        prompt = self._build_prompt(trial, literature)
        llm_result = self.call_gemini(prompt)

        if llm_result:
            try:
                return MolecularAnalysis(
                    target_name=llm_result.get("target_name", "Target Identified in Protocol"),
                    modality=llm_result.get("modality", "Biological / Small Molecule"),
                    biological_plausibility=llm_result.get("biological_plausibility", "MODERATE"),
                    target_validation_summary=llm_result.get("target_validation_summary", ""),
                    preclinical_evidence_strength=llm_result.get("preclinical_evidence_strength", "MODERATE"),
                    resistance_risk_notes=llm_result.get("resistance_risk_notes", ""),
                    confidence_score=float(llm_result.get("confidence_score", 0.85))
                )
            except Exception:
                pass

        # 2. Fallback to Expert Heuristic Engine
        return self._heuristic_analysis(trial, literature)

    def _build_prompt(self, trial: ClinicalTrial, literature: Optional[List[Dict[str, Any]]]) -> str:
        lit_summary = ""
        if literature:
            lit_summary = "\nRelevant Published Literature:\n" + "\n".join(
                [f"- [{pub.get('year')}] {pub.get('title')}: {pub.get('abstract')[:200]}..." for pub in literature[:3]]
            )

        interventions_text = ", ".join([f"{i.name} ({i.type}): {i.description}" for i in trial.interventions])
        return f"""
        You are {self.name}, {self.role}.
        Conduct an expert molecular biology and pharmacology audit on this clinical asset:

        Trial ID: {trial.nct_id}
        Title: {trial.title}
        Conditions: {", ".join(trial.conditions)}
        Interventions: {interventions_text}
        Brief Summary: {trial.brief_summary}
        {lit_summary}

        Respond in strict JSON with the following schema:
        {{
            "target_name": "Specific gene, protein, or receptor target (e.g. KRAS G12C, GLP-1R/GIP, Claudin 18.2, mRNA Neoantigen)",
            "modality": "Modality (e.g. mRNA-LNP, Bispecific Monoclonal Antibody, ADC, Small Molecule Inhibitor, CRISPR-Cas9)",
            "biological_plausibility": "HIGH" | "MODERATE" | "LOW" | "EXPERIMENTAL",
            "target_validation_summary": "2-3 sentences assessing whether target biology is proven vs speculative",
            "preclinical_evidence_strength": "STRONG" | "MODERATE" | "WEAK",
            "resistance_risk_notes": "Mechanisms by which tumor or pathogen may develop bypass resistance",
            "confidence_score": 0.85
        }}
        """

    def _extract_target_candidate(self, trial: ClinicalTrial) -> Optional[str]:
        """Extracts candidate target gene or drug mechanism from interventions, title, and summary."""
        # 1. Direct drug name mappings to validated drug targets
        drug_target_map = {
            "osimertinib": "EGFR",
            "erlotinib": "EGFR",
            "gefitinib": "EGFR",
            "sotorasib": "KRAS",
            "adagrasib": "KRAS",
            "trastuzumab": "ERBB2",
            "pertuzumab": "ERBB2",
            "ibrutinib": "BTK",
            "acalabrutinib": "BTK",
            "palbociclib": "CDK4",
            "ribociclib": "CDK4",
            "abemaciclib": "CDK4",
            "semaglutide": "GLP1R",
            "tirzepatide": "GLP1R",
            "liraglutide": "GLP1R",
            "venetoclax": "BCL2",
            "olaparib": "PARP1",
            "rucaparib": "PARP1",
            "niraparib": "PARP1",
            "pembrolizumab": "PDCD1",
            "nivolumab": "PDCD1",
            "atezolizumab": "CD274",
            "durvalumab": "CD274",
            "ipilimumab": "CTLA4",
            "dupilumab": "IL4R",
            "teclistamab": "TNFRSF17",
            "ciltacabtagene": "TNFRSF17",
            "idecabtagene": "TNFRSF17",
        }
        for inter in trial.interventions:
            iname = (inter.name or "").lower()
            for drug, target in drug_target_map.items():
                if drug in iname:
                    return target

        # 2. Match canonical gene/target tokens across title, interventions, and summary
        combined_text = f"{trial.title} {' '.join(i.name for i in trial.interventions)} {trial.brief_summary}"
        gene_pattern = re.compile(
            r"\b(KRAS|EGFR|HER2|ERBB2|BRAF|NRAS|HRAS|ALK|MET|RET|ROS1|NTRK[1-3]|CDK[46]|"
            r"BRCA[12]|PARP[12]?|BTK|JAK[1-3]|TYK2|STAT3|PD-?1|PD-?L1|CTLA-?4|LAG-?3|TIGIT|"
            r"CD19|CD20|BCMA|GLP-?1R?|GIPR?|GCGR|FGFR[1-4]|VEGF[A-D]?|FLT3|KIT|BCL2|MCL1|"
            r"AR|ESR1|PCSK9|CFTR|SMN1|DMD)\b",
            re.IGNORECASE
        )
        match = gene_pattern.search(combined_text)
        if match:
            return match.group(1).upper()

        return None

    def _heuristic_analysis(self, trial: ClinicalTrial, literature: Optional[List[Dict[str, Any]]]) -> MolecularAnalysis:
        full_text = f"{trial.title} {trial.brief_summary} {' '.join(trial.conditions)}".lower()
        for i in trial.interventions:
            full_text += f" {i.name.lower()} {i.description.lower()}"

        # Detect Modality
        modality = "Targeted Therapeutic"
        if "mrna" in full_text or "lipid nanoparticle" in full_text or "lnp" in full_text:
            modality = "mRNA / Lipid Nanoparticle (LNP)"
        elif "antibody-drug conjugate" in full_text or "adc" in full_text:
            modality = "Antibody-Drug Conjugate (ADC)"
        elif "car-t" in full_text or "chimeric antigen receptor" in full_text:
            modality = "Autologous CAR-T Cell Therapy"
        elif "crispr" in full_text or "cas9" in full_text or "gene edit" in full_text:
            modality = "CRISPR-Cas9 Gene Editing"
        elif "rnai" in full_text or "sirna" in full_text or "antisense" in full_text:
            modality = "RNA Interference (RNAi / ASO)"
        elif "bispecific" in full_text:
            modality = "Bispecific Monoclonal Antibody"
        elif "monoclonal" in full_text or "mab" in full_text:
            modality = "Monoclonal Antibody (mAb)"
        elif "inhibitor" in full_text or "small molecule" in full_text:
            modality = "Small Molecule Targeted Inhibitor"
        elif "glp-1" in full_text or "incretin" in full_text or "gip" in full_text:
            modality = "Peptide Incretin Receptor Agonist"

        # Check UniProt for verified mechanistic target data
        candidate = self._extract_target_candidate(trial)
        uniprot_data = None
        if candidate and self.uniprot_client:
            try:
                uniprot_data = self.uniprot_client.fetch_target_details(candidate)
            except Exception:
                uniprot_data = None

        if uniprot_data:
            target_name = f"{uniprot_data['protein_name']} ({uniprot_data['gene_name']} / UniProt:{uniprot_data['accession']})"
            plausibility = "HIGH"
            preclinical_strength = "STRONG"
            base_confidence = 0.88

            func_text = uniprot_data["function"][:220]
            if len(uniprot_data["function"]) > 220:
                func_text += "..."

            dis_text = f" Pathological disease linkage: {', '.join(uniprot_data['diseases'][:2])}." if uniprot_data.get("diseases") else ""
            loc_text = f" Cellular localization: {', '.join(uniprot_data['subcellular_locations'][:2])}." if uniprot_data.get("subcellular_locations") else ""
            validation_summary = (
                f"Mechanistically validated human target via Swiss-Prot ({uniprot_data['accession']}): "
                f"{func_text}{dis_text}{loc_text}"
            )

            cand_upper = candidate.upper()
            if any(k in cand_upper for k in ["KRAS", "EGFR", "ALK", "BRAF", "RET", "ROS1", "MET", "BTK"]):
                resistance_notes = "Acquired gatekeeper/switch mutations, secondary kinase domain alterations, or parallel RTK/MAPK bypass cascade activation."
            elif any(k in cand_upper for k in ["PD", "CTLA", "LAG", "TIGIT"]):
                resistance_notes = "Immune evasion via HLA downregulation, beta-2-microglobulin loss, or alternative immunosuppressive checkpoint upregulation."
            elif any(k in cand_upper for k in ["GLP", "GIP", "GCGR"]):
                resistance_notes = "Receptor desensitization/internalization, GI tolerability discontinuation barriers, or counter-regulatory neuroendocrine feedback."
            else:
                resistance_notes = "Target downregulation, secondary point mutations, or alternative compensatory pathway activation."
        else:
            # Fallback to Expert Taxonomy Heuristic
            target_name = "Target Pathway in " + (trial.conditions[0] if trial.conditions else "Indication")
            plausibility = "MODERATE"
            validation_summary = "Target is under clinical investigation with moderate biological rationale."
            resistance_notes = "Standard pharmacological resistance or metabolic clearance pathways apply."
            preclinical_strength = "MODERATE"

            if "mrna" in full_text and ("cancer" in full_text or "melanoma" in full_text or "neoantigen" in full_text):
                target_name = "Patient-Specific Tumor Neoantigens (mRNA Encoded)"
                plausibility = "HIGH"
                validation_summary = "mRNA-encoded patient-specific neoantigens induce targeted cytotoxic T-cell expansion against tumor mutanomes, validated by Phase 2 survival benefit."
                resistance_notes = "Tumor immune escape via HLA downregulation, beta-2-microglobulin loss, or exhaustion in cold tumor microenvironments."
                preclinical_strength = "STRONG"
            elif "kras" in full_text:
                target_name = "KRAS Oncoprotein (G12C / G12D / Pan-RAS)"
                plausibility = "HIGH"
                validation_summary = "KRAS was historically considered 'undruggable' but modern covalent and switch-II pocket allosteric inhibitors show direct biochemical target engagement."
                resistance_notes = "Acquired secondary mutations (e.g. Y96D, A59S), MET amplification, or activation of parallel RTK-MAPK bypass cascades."
                preclinical_strength = "STRONG"
            elif "glp-1" in full_text or "incretin" in full_text or "gip" in full_text:
                target_name = "GLP-1R / GIPR Incretin Receptors"
                plausibility = "HIGH"
                validation_summary = "Incretin dual/triple co-agonism is clinically validated to deliver synergistic glycemic control, central satiety signaling, and fat mass reduction."
                resistance_notes = "Receptor desensitization and GI tolerability discontinuation rates; counter-regulatory ghrelin or metabolic adaptation."
                preclinical_strength = "STRONG"
            elif "pd-1" in full_text or "pdl1" in full_text or "checkpoint" in full_text:
                target_name = "PD-1 / PD-L1 Immune Checkpoint Axis"
                plausibility = "HIGH"
                validation_summary = "Reversing T-cell exhaustion via checkpoint blockade is standard of care with gold-standard validation across solid tumors."
                resistance_notes = "Immunologically cold phenotype, absence of tumor-infiltrating lymphocytes (TILs), or alternative checkpoint upregulation (LAG-3, TIGIT)."
                preclinical_strength = "STRONG"
            elif "adc" in full_text or "trop2" in full_text or "her2" in full_text:
                target_name = "Cell-Surface Tumor Antigen + Cytotoxic Payload"
                plausibility = "HIGH"
                validation_summary = "High-affinity antibody binding internalizes payload for intracellular release, generating both direct cytotoxicity and bystander killing."
                resistance_notes = "Antigen downregulation, payload efflux pump overexpression (MDR1/P-gp), or premature linker cleavage causing systemic toxicity."
                preclinical_strength = "STRONG"
            elif "crispr" in full_text or "gene" in full_text:
                target_name = "Genomic Locus / Endogenous Gene Repair"
                plausibility = "HIGH"
                validation_summary = "Direct DNA double-strand break repair or base modification restores functional protein expression at the root genetic level."
                resistance_notes = "Off-target cleavage risks, vector immunogenicity, or incomplete cellular transduction in target tissue."
                preclinical_strength = "STRONG"
            elif "kinase" in full_text or "rtk" in full_text or "jak" in full_text or "tyrosine" in full_text:
                target_name = "Kinase / Intracellular Signaling Cascade"
                plausibility = "HIGH"
                validation_summary = "Kinase inhibitors are highly validated for interrupting intracellular phosphorylation cascades driving aberrant proliferation or inflammation."
                resistance_notes = "ATP-binding pocket gatekeeper mutations (e.g., T315I, T790M) or bypass signaling loop activation."
                preclinical_strength = "STRONG"
            elif "gpcr" in full_text or "receptor agonist" in full_text or "receptor antagonist" in full_text or "g-protein" in full_text:
                target_name = "G Protein-Coupled Receptor (GPCR)"
                plausibility = "HIGH"
                validation_summary = "GPCRs are extensively validated pharmacological targets modulating downstream secondary messenger cascades (cAMP, Calcium)."
                resistance_notes = "Receptor downregulation, desensitization via beta-arrestin recruitment, or compensatory neuroendocrine feedback."
                preclinical_strength = "STRONG"
            elif "ion channel" in full_text or "nav" in full_text or "cav" in full_text or "kv" in full_text:
                target_name = "Ion Channel"
                plausibility = "MODERATE"
                validation_summary = "Ion channel modulation provides rapid physiological action potential changes, though achieving isoform selectivity remains challenging."
                resistance_notes = "Subunit expression shifts, channel state-dependent binding limitations, or counter-regulatory ionic balances."
                preclinical_strength = "MODERATE"

            if plausibility == "MODERATE" and target_name.startswith("Target Pathway"):
                base_confidence = 0.50
            elif plausibility in ("HIGH", "STRONG"):
                base_confidence = 0.72
            else:
                base_confidence = 0.65

        if literature and len(literature) >= 2:
            base_confidence += 0.08
            preclinical_strength = "STRONG"
        elif literature and len(literature) == 1:
            base_confidence += 0.04

        confidence = round(min(0.92, base_confidence), 2)

        return MolecularAnalysis(
            target_name=target_name,
            modality=modality,
            biological_plausibility=plausibility,
            target_validation_summary=validation_summary,
            preclinical_evidence_strength=preclinical_strength,
            resistance_risk_notes=resistance_notes,
            confidence_score=confidence
        )
