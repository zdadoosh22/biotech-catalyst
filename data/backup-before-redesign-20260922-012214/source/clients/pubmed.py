"""NCBI PubMed E-Utilities Client.

Searches published biomedical literature for target mechanisms, clinical trial results,
and preclinical safety signals.
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

from core.config import NCBI_PUBMED_BASE_URL, NCBI_API_KEY, DEFAULT_TIMEOUT_SEC
from core.http_client import get_retry_session


class PubMedClient:
    def __init__(self, api_key: Optional[str] = NCBI_API_KEY, timeout: int = DEFAULT_TIMEOUT_SEC):
        self.base_url = NCBI_PUBMED_BASE_URL
        self.api_key = api_key
        self.timeout = timeout
        self.session = get_retry_session()
        self.session.headers.update({
            "User-Agent": "BioCatalyst-Biomedical-Harvester/1.0"
        })
        self._last_request_time = 0.0
        # NCBI limits: 10/sec with key, 3/sec without
        self._min_request_interval = 0.11 if api_key else 0.34

    def _rate_limit(self):
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Searches PubMed IDs (PMIDs) matching a query term."""
        if not query:
            return []

        url = f"{self.base_url}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "sort": "pub_date"
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            self._rate_limit()
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception:
            return []

    def fetch_abstracts(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetches title, journal, year, and abstract text for a list of PMIDs."""
        if not pmids:
            return []

        clean_ids = ",".join(pmids[:10])
        url = f"{self.base_url}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": clean_ids,
            "retmode": "xml"
        }
        if self.api_key:
            params["api_key"] = self.api_key

        articles = []
        try:
            self._rate_limit()
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            for article_node in root.findall(".//PubmedArticle"):
                pmid_node = article_node.find(".//PMID")
                pmid = pmid_node.text if pmid_node is not None else "Unknown"

                title_node = article_node.find(".//ArticleTitle")
                title = title_node.text if title_node is not None else "Untitled Paper"

                journal_node = article_node.find(".//Journal/Title")
                journal = journal_node.text if journal_node is not None else "Unknown Journal"

                year_node = article_node.find(".//JournalIssue/PubDate/Year")
                year = year_node.text if year_node is not None else ""

                abstract_parts = []
                for abs_text in article_node.findall(".//Abstract/AbstractText"):
                    if abs_text.text:
                        abstract_parts.append(abs_text.text)
                abstract = " ".join(abstract_parts)

                articles.append({
                    "pmid": pmid,
                    "title": title,
                    "journal": journal,
                    "year": year,
                    "abstract": abstract[:1000] if abstract else "No abstract provided."
                })
        except Exception:
            pass

        return articles
