"""Sponsor Matcher: Resolves clinical trial sponsor organizations to public stock tickers.

Employs canonical dictionary mapping, legal entity normalization, and token matching.
"""

import re
from typing import Optional, Tuple
from core.config import KNOWN_BIOTECH_REGISTRY


class SponsorMatcher:
    def __init__(self, custom_registry: Optional[dict] = None):
        self.registry = {k.lower(): v for k, v in KNOWN_BIOTECH_REGISTRY.items()}
        if custom_registry:
            for k, v in custom_registry.items():
                self.registry[k.lower()] = v

    @staticmethod
    def clean_name(name: str) -> str:
        """Removes corporate entity suffixes, punctuation, and extraneous noise."""
        if not name:
            return ""
        s = name.lower()
        # Remove parenthetical notes e.g. "ModernaTX, Inc. (formerly ModeRNA)"
        s = re.sub(r"\(.*?\)", "", s)
        # Remove common corporate legal extensions
        legal_suffixes = [
            r"\binc\b\.?", r"\bcorp\b\.?", r"\bcorporation\b", r"\bllc\b\.?",
            r"\bltd\b\.?", r"\bplc\b\.?", r"\bco\b\.?", r"\bcompany\b",
            r"\bse\b", r"\bag\b", r"\bgmbh\b", r"\bs\.a\.\b", r"\bn\.v\.\b",
            r"\bpharmaceuticals?\b", r"\btherapeutics?\b", r"\bbiosciences?\b",
            r"\bpharma\b", r"\bholdings?\b", r"\btechnologies\b", r"\bhealth\b"
        ]
        for pattern in legal_suffixes:
            s = re.sub(pattern, " ", s)
        # Clean punctuation and extra whitespace
        s = re.sub(r"[,\.\-\/\\_]+", " ", s)
        return " ".join(s.split())

    def match_sponsor(self, sponsor_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Attempts to resolve sponsor name to (ticker, canonical_name).
        Returns (None, None) if no confident match is found.
        """
        if not sponsor_name:
            return None, None

        raw_lower = sponsor_name.lower().strip()

        # 1. Exact match against known dictionary keys
        if raw_lower in self.registry:
            entry = self.registry[raw_lower]
            return entry["ticker"], entry["name"]

        # 2. Check substring containment against dictionary keys
        for key, entry in self.registry.items():
            if key in raw_lower or raw_lower in key:
                return entry["ticker"], entry["name"]

        # 3. Normalized stripped name matching
        cleaned_input = self.clean_name(sponsor_name)
        if not cleaned_input:
            return None, None

        for key, entry in self.registry.items():
            cleaned_key = self.clean_name(key)
            if cleaned_key and (cleaned_key == cleaned_input or cleaned_key in cleaned_input or cleaned_input in cleaned_key):
                return entry["ticker"], entry["name"]

        # 4. Token overlap matching (require at least one significant unique token match)
        input_tokens = set(cleaned_input.split())
        for key, entry in self.registry.items():
            key_tokens = set(self.clean_name(key).split())
            if not key_tokens:
                continue
            common = input_tokens.intersection(key_tokens)
            # If all key tokens are in input tokens or vice versa and token length > 3
            if common and any(len(t) >= 4 for t in common):
                if len(common) == len(key_tokens) or len(common) == len(input_tokens):
                    return entry["ticker"], entry["name"]

        return None, None
