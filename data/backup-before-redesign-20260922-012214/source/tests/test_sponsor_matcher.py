"""Unit tests for SponsorMatcher."""

import pytest
from clients.sponsor_matcher import SponsorMatcher


def test_exact_sponsor_matching():
    matcher = SponsorMatcher()
    ticker, name = matcher.match_sponsor("Moderna")
    assert ticker == "MRNA"
    assert "Moderna" in name


def test_suffix_cleaning_and_normalization():
    matcher = SponsorMatcher()

    # Corporate variations
    ticker, _ = matcher.match_sponsor("ModernaTX, Inc.")
    assert ticker == "MRNA"

    ticker, _ = matcher.match_sponsor("Viking Therapeutics, Inc.")
    assert ticker == "VKTX"

    ticker, _ = matcher.match_sponsor("BioNTech SE")
    assert ticker == "BNTX"

    ticker, _ = matcher.match_sponsor("Alnylam Pharmaceuticals, Inc.")
    assert ticker == "ALNY"


def test_unknown_sponsor():
    matcher = SponsorMatcher()
    ticker, name = matcher.match_sponsor("Fictional Nonexistent Lab LLC")
    assert ticker is None
    assert name is None
