import pytest
import responses
from clients.clinical_trials import ClinicalTrialsClient
from clients.pubmed import PubMedClient
from core.config import CLINICAL_TRIALS_API_URL, NCBI_PUBMED_BASE_URL


@responses.activate
def test_ctgov_fetch_trial_by_nct():
    responses.add(
        responses.GET,
        f"{CLINICAL_TRIALS_API_URL}/NCT01234567",
        json={
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT01234567",
                    "briefTitle": "Mock HTTP Trial"
                },
                "statusModule": {
                    "overallStatus": "RECRUITING"
                }
            }
        },
        status=200
    )

    client = ClinicalTrialsClient(timeout=1)
    trial = client.fetch_trial_by_nct("NCT01234567")
    
    assert trial is not None
    assert trial.nct_id == "NCT01234567"
    assert trial.title == "Mock HTTP Trial"
    assert trial.status == "RECRUITING"


@responses.activate
def test_pubmed_search_and_fetch():
    # Mock esearch
    responses.add(
        responses.GET,
        f"{NCBI_PUBMED_BASE_URL}/esearch.fcgi",
        json={
            "esearchresult": {
                "idlist": ["111111", "222222"]
            }
        },
        status=200,
        match_querystring=False
    )
    
    # Mock efetch
    mock_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>111111</PMID>
                <Article>
                    <ArticleTitle>Mock Article 1</ArticleTitle>
                    <Abstract>
                        <AbstractText>This is a mock abstract.</AbstractText>
                    </Abstract>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """
    responses.add(
        responses.GET,
        f"{NCBI_PUBMED_BASE_URL}/efetch.fcgi",
        body=mock_xml,
        status=200,
        match_querystring=False
    )

    client = PubMedClient(api_key=None, timeout=1)
    
    # Test search
    pmids = client.search("KRAS G12C", max_results=2)
    assert pmids == ["111111", "222222"]
    
    # Test fetch
    articles = client.fetch_abstracts(pmids)
    assert len(articles) == 1
    assert articles[0]["pmid"] == "111111"
    assert articles[0]["title"] == "Mock Article 1"
    assert "mock abstract" in articles[0]["abstract"]
