import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from confidence_scorer import (
    extract_domain,
    domain_matches_supplier,
    is_directory,
    score_url,
    pick_best_url,
)


class TestExtractDomain:
    def test_strips_www(self):
        assert extract_domain("https://www.ancare.com/") == "ancare.com"

    def test_handles_no_www(self):
        assert extract_domain("https://ancare.com/path") == "ancare.com"

    def test_empty_url_returns_empty(self):
        assert extract_domain("") == ""

    def test_invalid_url_returns_empty(self):
        assert extract_domain("not_a_url") == ""


class TestDomainMatchesSupplier:
    def test_exact_word_match(self):
        assert domain_matches_supplier("ancare.com", "ANCARE CORP") is True

    def test_partial_word_no_match(self):
        # "ab" is 2 chars, filtered out — should not match
        assert domain_matches_supplier("somesite.com", "AB INC") is False

    def test_strips_common_suffixes(self):
        # "ANCARE CORP" → strip " corp" → "ancare" → matches "ancare.com"
        assert domain_matches_supplier("ancare.com", "ANCARE CORP") is True

    def test_no_match_unrelated_domain(self):
        assert domain_matches_supplier("randomsite.com", "ZEISS CORPORATION") is False

    def test_case_insensitive(self):
        assert domain_matches_supplier("zeiss.com", "ZEISS") is True


class TestIsDirectory:
    def test_amazon_is_directory(self):
        assert is_directory("amazon.com") is True

    def test_linkedin_is_directory(self):
        assert is_directory("linkedin.com") is True

    def test_official_site_not_directory(self):
        assert is_directory("ancare.com") is False

    def test_thomasnet_is_directory(self):
        assert is_directory("thomasnet.com") is True


class TestScoreUrl:
    def test_both_engines_agree_high_score(self):
        score = score_url(
            "https://www.ancare.com/",
            "ANCARE CORP",
            ["https://www.ancare.com/"],
            ["https://www.ancare.com/"],
        )
        assert score >= 70

    def test_only_one_engine_lower_than_agreement(self):
        score_both = score_url(
            "https://www.ancare.com/",
            "ANCARE CORP",
            ["https://www.ancare.com/"],
            ["https://www.ancare.com/"],
        )
        score_one = score_url(
            "https://www.ancare.com/",
            "ANCARE CORP",
            ["https://www.ancare.com/"],
            [],
        )
        assert score_both > score_one

    def test_directory_domain_penalized(self):
        score = score_url(
            "https://www.amazon.com/",
            "ANCARE CORP",
            ["https://www.amazon.com/"],
            ["https://www.amazon.com/"],
        )
        # Missing the +20 not-a-directory bonus
        score_legit = score_url(
            "https://www.ancare.com/",
            "ANCARE CORP",
            ["https://www.ancare.com/"],
            ["https://www.ancare.com/"],
        )
        assert score < score_legit

    def test_https_bonus(self):
        score_https = score_url(
            "https://ancare.com/",
            "ANCARE CORP",
            ["https://ancare.com/"],
            ["https://ancare.com/"],
        )
        score_http = score_url(
            "http://ancare.com/",
            "ANCARE CORP",
            ["http://ancare.com/"],
            ["http://ancare.com/"],
        )
        assert score_https > score_http

    def test_empty_url_returns_zero(self):
        assert score_url("", "ANCARE CORP", [], []) == 0

    def test_no_engine_results_still_scores_other_signals(self):
        # Empty engine lists give 0 for engine agreement,
        # but domain/https/TLD/not-directory bonuses still apply
        score = score_url("https://ancare.com/", "ANCARE CORP", [], [])
        assert score > 0
        assert score < score_url("https://ancare.com/", "ANCARE CORP",
                                 ["https://ancare.com/"], ["https://ancare.com/"])


class TestPickBestUrl:
    def test_both_engines_agree_high_confidence(self):
        url, score = pick_best_url(
            ["https://www.ancare.com/"],
            ["https://www.ancare.com/"],
            "ANCARE CORP",
        )
        assert url == "https://www.ancare.com/"
        assert score >= 70

    def test_empty_lists_returns_empty(self):
        url, score = pick_best_url([], [], "ANCARE CORP")
        assert url == ""
        assert score == 0

    def test_deduplicates_same_domain(self):
        url, score = pick_best_url(
            ["https://www.ancare.com/page1"],
            ["https://www.ancare.com/page2"],
            "ANCARE CORP",
        )
        assert url.startswith("https://www.ancare.com")

    def test_picks_highest_scoring(self):
        url, score = pick_best_url(
            ["https://www.ancare.com/"],
            ["https://www.amazon.com/"],
            "ANCARE CORP",
        )
        assert "ancare" in url
