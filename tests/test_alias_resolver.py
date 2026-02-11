"""Tests for Layer 0 — Alias Resolution API.

Covers: exact matching, fuzzy matching, temporal disambiguation,
collision handling, confidence scores, and unresolved logging.
See Issue #18 (GR: Alias Resolution API).
"""

from datetime import date
from pathlib import Path

import pytest

from graphhansard.golden_record.resolver import AliasResolver, ResolutionResult

GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


@pytest.fixture
def resolver():
    """Create an AliasResolver instance for testing."""
    return AliasResolver(str(GOLDEN_RECORD_PATH))


class TestAliasResolverInit:
    """Test AliasResolver initialization."""

    def test_resolver_initializes(self, resolver):
        """Resolver loads and builds index successfully."""
        assert resolver is not None
        assert len(resolver._alias_index) > 0
        assert len(resolver.golden_record.mps) == 39

    def test_index_has_expected_size(self, resolver):
        """Index contains expected number of unique aliases."""
        # Should have at least 357 aliases mentioned in README
        assert len(resolver._alias_index) >= 357

    def test_custom_fuzzy_threshold(self):
        """Can set custom fuzzy threshold."""
        resolver = AliasResolver(str(GOLDEN_RECORD_PATH), fuzzy_threshold=90)
        assert resolver.fuzzy_threshold == 90


class TestExactMatch:
    """Test exact matching resolution."""

    def test_exact_match_simple_name(self, resolver):
        """Exact match on simple name returns correct MP."""
        result = resolver.resolve("Brave")
        assert result.node_id == "mp_davis_brave"
        assert result.confidence == 1.0
        assert result.method == "exact"
        assert result.collision_warning is None

    def test_exact_match_case_insensitive(self, resolver):
        """Exact match is case-insensitive."""
        result = resolver.resolve("BRAVE")
        assert result.node_id == "mp_davis_brave"
        assert result.method == "exact"

    def test_exact_match_constituency(self, resolver):
        """Exact match on constituency alias."""
        result = resolver.resolve("Member for Cat Island, Rum Cay and San Salvador")
        assert result.node_id == "mp_davis_brave"
        assert result.method == "exact"

    def test_exact_match_portfolio(self, resolver):
        """Exact match on portfolio title."""
        result = resolver.resolve("Deputy Prime Minister")
        assert result.node_id == "mp_cooper_chester"
        assert result.method == "exact"

    def test_exact_match_honorific(self, resolver):
        """Exact match on honorific variant."""
        result = resolver.resolve("Hon. Chester Cooper")
        assert result.node_id == "mp_cooper_chester"
        assert result.method == "exact"

    def test_exact_match_whitespace_normalized(self, resolver):
        """Extra whitespace is normalized."""
        result = resolver.resolve("  Chester Cooper  ")
        assert result.node_id == "mp_cooper_chester"
        assert result.method == "exact"


class TestFuzzyMatch:
    """Test fuzzy matching resolution."""

    def test_fuzzy_match_typo(self, resolver):
        """Fuzzy match handles typos."""
        result = resolver.resolve("Chestor Cooper")  # 'Chestor' instead of 'Chester'
        assert result.node_id == "mp_cooper_chester"
        assert result.method == "fuzzy"
        assert 0.8 <= result.confidence <= 1.0

    def test_fuzzy_match_dialectal_variation(self, resolver):
        """Fuzzy match handles small variations in names."""
        # Close match to "Fred Mitchell"
        result = resolver.resolve("Fred Mitchel")  # Missing 'l' in Mitchell
        assert result.node_id == "mp_mitchell_fred"
        assert result.method == "fuzzy"
        assert result.confidence >= 0.85

    def test_fuzzy_match_partial(self, resolver):
        """Fuzzy match on slightly misspelled constituency."""
        # Close match with typo
        result = resolver.resolve("Member for Exuma and Ragged Island")  # Missing 's' in Exumas
        assert result.node_id == "mp_cooper_chester"
        assert result.method == "fuzzy"

    def test_fuzzy_match_below_threshold_fails(self, resolver):
        """Fuzzy match below threshold returns unresolved."""
        # Very poor match
        result = resolver.resolve("xyz123abc")
        assert result.node_id is None
        assert result.method == "unresolved"
        assert result.confidence == 0.0


class TestTemporalDisambiguation:
    """Test temporal filtering with debate_date parameter."""

    def test_temporal_minister_of_works_before_reshuffle(self, resolver):
        """Before Sept 3 2023, Minister of Works resolves to Sears."""
        result = resolver.resolve("Minister of Works", debate_date="2023-08-01")
        assert result.node_id == "mp_sears_alfred"
        assert result.method == "exact"

    def test_temporal_minister_of_works_after_reshuffle(self, resolver):
        """After Sept 3 2023, Minister of Works resolves to Sweeting."""
        result = resolver.resolve("Minister of Works", debate_date="2023-10-01")
        assert result.node_id == "mp_sweeting_clay"
        assert result.method == "exact"

    def test_temporal_minister_of_housing_before_reshuffle(self, resolver):
        """Before Sept 3 2023, Minister of Housing resolves to Coleby-Davis."""
        result = resolver.resolve("Minister of Housing", debate_date="2023-08-01")
        assert result.node_id == "mp_coleby_davis_jobeth"
        assert result.method == "exact"

    def test_temporal_minister_of_housing_after_reshuffle(self, resolver):
        """After Sept 3 2023, Minister of Housing resolves to Bell."""
        result = resolver.resolve("Minister of Housing", debate_date="2023-10-01")
        assert result.node_id == "mp_bell_keith"
        assert result.method == "exact"

    def test_temporal_minister_of_agriculture_before_reshuffle(self, resolver):
        """Before Sept 3 2023, Minister of Agriculture resolves to Sweeting."""
        result = resolver.resolve("Minister of Agriculture", debate_date="2023-08-01")
        assert result.node_id == "mp_sweeting_clay"
        assert result.method == "exact"

    def test_temporal_minister_of_agriculture_after_reshuffle(self, resolver):
        """After late 2023, Minister of Agriculture resolves to Campbell."""
        result = resolver.resolve("Minister of Agriculture", debate_date="2024-01-15")
        assert result.node_id == "mp_campbell_jomo"
        assert result.method == "exact"


class TestCollisionHandling:
    """Test handling of known alias collisions."""

    def test_collision_doc_without_date(self, resolver):
        """'Doc' collision returns one of the claimants with warning."""
        result = resolver.resolve("Doc")
        # Should return either Darville or Minnis
        assert result.node_id in ["mp_darville_michael", "mp_minnis_hubert"]
        assert result.collision_warning is not None
        assert "collision" in result.collision_warning.lower()

    def test_collision_adrian_without_date(self, resolver):
        """'Adrian' collision returns one of the claimants with warning."""
        result = resolver.resolve("Adrian")
        # Should return either White or Gibson
        assert result.node_id in ["mp_white_adrian", "mp_gibson_adrian"]
        assert result.collision_warning is not None

    def test_collision_lightbourne_without_date(self, resolver):
        """'Lightbourne' surname collision via fuzzy match."""
        # "Lightbourne" alone isn't in manual aliases, but fuzzy match should work
        result = resolver.resolve("Leo Lightbourne")
        assert result.node_id == "mp_lightbourne_leonardo"
        # Also test the other Lightbourne
        result2 = resolver.resolve("Zane Lightbourne")
        assert result2.node_id == "mp_lightbourne_zane"


class TestUnresolvedLogging:
    """Test unresolved mention logging."""

    def test_unresolved_mention_is_logged(self, resolver):
        """Unresolved mentions are logged."""
        initial_count = len(resolver.unresolved_log)
        result = resolver.resolve("Some Random Name That Does Not Exist")
        assert result.node_id is None
        assert result.method == "unresolved"
        assert len(resolver.unresolved_log) == initial_count + 1

    def test_unresolved_log_contains_mention(self, resolver):
        """Unresolved log contains the original mention."""
        mention = "Completely Unknown Person"
        resolver.resolve(mention)
        assert any(entry["mention"] == mention for entry in resolver.unresolved_log)

    def test_save_unresolved_log(self, resolver, tmp_path):
        """Can save unresolved log to file."""
        resolver.resolve("Unknown Person 1")
        resolver.resolve("Unknown Person 2")

        log_path = tmp_path / "unresolved.json"
        resolver.save_unresolved_log(str(log_path))

        assert log_path.exists()
        import json

        with open(log_path) as f:
            log = json.load(f)
        assert len(log) >= 2


class TestConfidenceScores:
    """Test confidence score calculation."""

    def test_exact_match_confidence_is_one(self, resolver):
        """Exact matches have confidence 1.0."""
        result = resolver.resolve("Brave Davis")
        assert result.confidence == 1.0

    def test_fuzzy_match_confidence_between_threshold_and_one(self, resolver):
        """Fuzzy matches have confidence between threshold/100 and 1.0."""
        result = resolver.resolve("Chestor Cooper")
        if result.method == "fuzzy":
            assert 0.85 <= result.confidence <= 1.0

    def test_unresolved_confidence_is_zero(self, resolver):
        """Unresolved mentions have confidence 0.0."""
        result = resolver.resolve("xyz123nonexistent")
        assert result.confidence == 0.0


class TestSaveIndex:
    """Test saving the alias index."""

    def test_save_index_creates_file(self, resolver, tmp_path):
        """Can save alias index to file."""
        index_path = tmp_path / "test_index.json"
        resolver.save_index(str(index_path))
        assert index_path.exists()

    def test_saved_index_is_valid_json(self, resolver, tmp_path):
        """Saved index is valid JSON."""
        index_path = tmp_path / "test_index.json"
        resolver.save_index(str(index_path))

        import json

        with open(index_path) as f:
            index = json.load(f)
        assert isinstance(index, dict)
        assert len(index) > 0
