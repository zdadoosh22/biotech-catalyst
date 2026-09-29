import pytest
from core.models import ClinicalTrial, Intervention
from agents.molecular_agent import MolecularAnalystAgent

def test_protein_taxonomy_detection():
    agent = MolecularAnalystAgent()
    
    # 1. GPCR
    trial_gpcr = ClinicalTrial(
        nct_id="NCT0001",
        title="Novel GPCR Agonist for Obesity",
        sponsor_name="Mock",
        conditions=["Obesity"],
        interventions=[Intervention(name="Drug X", description="receptor agonist")]
    )
    audit_gpcr = agent._heuristic_analysis(trial_gpcr, None)
    assert "G Protein-Coupled Receptor (GPCR)" in audit_gpcr.target_name
    assert audit_gpcr.biological_plausibility == "HIGH"
    
    # 2. Kinase
    trial_kinase = ClinicalTrial(
        nct_id="NCT0002",
        title="Tyrosine Kinase Inhibitor in CML",
        sponsor_name="Mock",
        conditions=["CML"],
        interventions=[Intervention(name="Drug Y", description="Kinase inhibitor")]
    )
    audit_kinase = agent._heuristic_analysis(trial_kinase, None)
    assert "Kinase" in audit_kinase.target_name
    assert audit_kinase.biological_plausibility == "HIGH"
    
    # 3. Unknown/Exotic (Should fallback to Moderate)
    trial_unknown = ClinicalTrial(
        nct_id="NCT0003",
        title="Exotic pathway modulator",
        sponsor_name="Mock",
        conditions=["Rare Disease"],
        interventions=[Intervention(name="Drug Z", description="Unknown mechanism")]
    )
    audit_unknown = agent._heuristic_analysis(trial_unknown, None)
    assert "Target Pathway in Rare Disease" in audit_unknown.target_name
    assert audit_unknown.biological_plausibility == "MODERATE"


def test_uniprot_client_mocked():
    """UniProtClient correctly parses Swiss-Prot protein name, function, and disease linkage."""
    import responses
    from clients.uniprot import UniProtClient

    client = UniProtClient()
    mock_payload = {
        "results": [
            {
                "entryType": "UniProtKB reviewed (Swiss-Prot)",
                "primaryAccession": "P01116",
                "genes": [{"geneName": {"value": "KRAS"}}],
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "GTPase KRas"}}
                },
                "comments": [
                    {
                        "commentType": "FUNCTION",
                        "texts": [{"value": "Signal transducer in the Ras-MAPK signaling pathway."}]
                    },
                    {
                        "commentType": "DISEASE",
                        "disease": {"diseaseId": "Carcinoma of the pancreas"}
                    },
                    {
                        "commentType": "SUBCELLULAR LOCATION",
                        "subcellularLocations": [{"location": {"value": "Cell membrane"}}]
                    }
                ]
            }
        ]
    }

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_payload,
            status=200
        )
        res = client.fetch_target_details("KRAS")

    assert res is not None
    assert res["accession"] == "P01116"
    assert res["gene_name"] == "KRAS"
    assert res["protein_name"] == "GTPase KRas"
    assert "Ras-MAPK signaling pathway" in res["function"]
    assert "Carcinoma of the pancreas" in res["diseases"]
    assert "Cell membrane" in res["subcellular_locations"]


def test_molecular_agent_uniprot_integration():
    """MolecularAnalystAgent enhances validation summary and confidence when UniProt data is available."""
    from unittest.mock import MagicMock

    mock_uniprot = MagicMock()
    mock_uniprot.fetch_target_details.return_value = {
        "accession": "P00533",
        "gene_name": "EGFR",
        "protein_name": "Epidermal growth factor receptor",
        "function": "Receptor tyrosine kinase binding ligands of the EGF family.",
        "diseases": ["Lung cancer"],
        "subcellular_locations": ["Cell membrane"],
        "is_reviewed": True
    }

    agent = MolecularAnalystAgent(uniprot_client=mock_uniprot)
    trial = ClinicalTrial(
        nct_id="NCT0005",
        title="Osimertinib in Advanced NSCLC",
        sponsor_name="AstraZeneca",
        conditions=["Non-Small Cell Lung Cancer"],
        interventions=[Intervention(name="Osimertinib", description="EGFR kinase inhibitor")]
    )

    audit = agent._heuristic_analysis(trial, None)

    mock_uniprot.fetch_target_details.assert_called_with("EGFR")
    assert "Epidermal growth factor receptor" in audit.target_name
    assert "P00533" in audit.target_name
    assert audit.biological_plausibility == "HIGH"
    assert audit.preclinical_evidence_strength == "STRONG"
    assert "Swiss-Prot (P00533)" in audit.target_validation_summary
    assert "Lung cancer" in audit.target_validation_summary
    assert audit.confidence_score >= 0.88


def test_molecular_agent_drug_mapping():
    """Extracts candidate target gene from known drug names like Trastuzumab and Semaglutide."""
    agent = MolecularAnalystAgent()
    trial_trast = ClinicalTrial(
        nct_id="NCT0006",
        title="Trastuzumab Deruxtecan in Breast Cancer",
        sponsor_name="Daiichi Sankyo",
        conditions=["HER2+ Breast Cancer"],
        interventions=[Intervention(name="Trastuzumab deruxtecan", description="ADC targeting ERBB2")]
    )
    candidate = agent._extract_target_candidate(trial_trast)
    assert candidate == "ERBB2"
