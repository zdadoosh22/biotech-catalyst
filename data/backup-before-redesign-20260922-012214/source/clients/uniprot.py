"""UniProt Client for fetching validated biochemical target mechanisms.

Queries the UniProtKB REST API for reviewed (Swiss-Prot) human protein targets,
extracting canonical function, cellular localization, and pathological disease links.
"""

import re
import structlog
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import quote

from core.config import UNIPROT_BASE_URL, DEFAULT_TIMEOUT_SEC
from core.http_client import get_retry_session

logger = structlog.get_logger(__name__)

# Canonical gene symbol aliases for standard oncology and metabolic drug targets
TARGET_GENE_ALIASES = {
    "her2": "ERBB2",
    "her-2": "ERBB2",
    "neu": "ERBB2",
    "pd-1": "PDCD1",
    "pd1": "PDCD1",
    "pd-l1": "CD274",
    "pdl1": "CD274",
    "ctla-4": "CTLA4",
    "ctla4": "CTLA4",
    "cd20": "MS4A1",
    "bcma": "TNFRSF17",
    "vegfr2": "KDR",
    "vegfr-2": "KDR",
    "glp-1r": "GLP1R",
    "glp-1": "GLP1R",
    "glp1": "GLP1R",
    "gip": "GIPR",
    "gipr": "GIPR",
    "glucagon": "GCGR",
    "kras": "KRAS",
    "nras": "NRAS",
    "hras": "HRAS",
    "braf": "BRAF",
    "egfr": "EGFR",
    "btk": "BTK",
    "cdk4": "CDK4",
    "cdk6": "CDK6",
    "parp1": "PARP1",
    "parp": "PARP1",
    "jak1": "JAK1",
    "jak2": "JAK2",
    "jak3": "JAK3",
    "tyk2": "TYK2",
    "bcl2": "BCL2",
    "mcl1": "MCL1",
    "pcsk9": "PCSK9",
    "cftr": "CFTR",
}


class UniProtClient:
    def __init__(self, session: Optional[requests.Session] = None, timeout: int = DEFAULT_TIMEOUT_SEC):
        self.session = session or get_retry_session()
        self.timeout = timeout
        self._cache: Dict[str, Optional[Dict[str, Any]]] = {}

    def fetch_target_details(self, target_query: str) -> Optional[Dict[str, Any]]:
        """Searches UniProtKB for a reviewed human protein target matching target_query."""
        if not target_query:
            return None

        clean_query = target_query.strip()
        cache_key = clean_query.lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check aliases
        symbol = TARGET_GENE_ALIASES.get(cache_key, clean_query.upper())

        # Attempt 1: Exact reviewed gene symbol search
        result = self._query_uniprot(f"reviewed:true AND gene_exact:{symbol} AND organism_id:9606")

        # Attempt 2: General reviewed text search if exact gene query had no results
        if not result:
            sanitized = re.sub(r"[^\w\s-]", "", clean_query)
            result = self._query_uniprot(f"reviewed:true AND ({sanitized}) AND organism_id:9606")

        self._cache[cache_key] = result
        return result

    def _query_uniprot(self, query_string: str) -> Optional[Dict[str, Any]]:
        url = f"{UNIPROT_BASE_URL}/search"
        params = {
            "query": query_string,
            "format": "json",
            "size": 1
        }

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.debug("UniProt search non-200 response", status=resp.status_code, query=query_string)
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            entry = results[0]
            accession = entry.get("primaryAccession", "Unknown")

            # Extract Gene
            genes = entry.get("genes", [])
            gene_name = symbol = "Unknown"
            if genes:
                gene_name = genes[0].get("geneName", {}).get("value", "Unknown")

            # Extract Protein Name
            protein_desc = entry.get("proteinDescription", {})
            rec_name = protein_desc.get("recommendedName", {}).get("fullName", {}).get("value")
            if not rec_name:
                sub_names = protein_desc.get("submissionNames", [])
                if sub_names:
                    rec_name = sub_names[0].get("fullName", {}).get("value")
            protein_name = rec_name or gene_name

            # Extract Function
            comments = entry.get("comments", [])
            function_texts = []
            diseases = []
            subcellular = []

            for comm in comments:
                ctype = comm.get("commentType")
                if ctype == "FUNCTION":
                    for txt in comm.get("texts", []):
                        val = txt.get("value")
                        if val:
                            function_texts.append(val)
                elif ctype == "DISEASE":
                    d_obj = comm.get("disease", {})
                    d_id = d_obj.get("diseaseId")
                    if d_id:
                        diseases.append(d_id)
                elif ctype == "SUBCELLULAR LOCATION":
                    for loc in comm.get("subcellularLocations", []):
                        l_val = loc.get("location", {}).get("value")
                        if l_val and l_val not in subcellular:
                            subcellular.append(l_val)

            function_summary = " ".join(function_texts) if function_texts else "Canonical human protein target."

            return {
                "accession": accession,
                "gene_name": gene_name,
                "protein_name": protein_name,
                "function": function_summary,
                "diseases": diseases,
                "subcellular_locations": subcellular,
                "is_reviewed": entry.get("entryType") == "UniProtKB reviewed (Swiss-Prot)"
            }

        except Exception as e:
            logger.debug("UniProt API fetch failed", error=str(e), query=query_string)
            return None
