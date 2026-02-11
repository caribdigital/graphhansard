"""Tests for Layer 0 — Golden Record.

Covers: data model validation, alias resolution, collision detection.
See Issues #1 through #5.
"""

from datetime import date
from pathlib import Path

from graphhansard.golden_record.models import GoldenRecord, MPNode


GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


def _load_record() -> GoldenRecord:
    """Load and validate the Golden Record from mps.json."""
    data = GOLDEN_RECORD_PATH.read_text(encoding="utf-8")
    return GoldenRecord.model_validate_json(data)


class TestGoldenRecordSchema:
    """Validate mps.json against Pydantic schemas."""

    def test_golden_record_loads(self):
        """mps.json loads and validates against the GoldenRecord schema."""
        assert GOLDEN_RECORD_PATH.exists(), f"mps.json not found at {GOLDEN_RECORD_PATH}"
        record = _load_record()
        assert len(record.mps) == 39, f"Expected 39 MPs, got {len(record.mps)}"

    def test_all_mps_have_node_ids(self):
        """Every MP has a unique, non-empty node_id."""
        record = _load_record()
        node_ids = [mp.node_id for mp in record.mps]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node_ids found"
        assert all(nid for nid in node_ids), "Empty node_id found"

    def test_all_mps_have_aliases(self):
        """Every MP has at least one alias."""
        record = _load_record()
        for mp in record.mps:
            assert len(mp.aliases) > 0, f"{mp.node_id} has no aliases"

    def test_speaker_is_control_node(self):
        """The Speaker of the House has node_type 'control'."""
        record = _load_record()
        speaker = next((mp for mp in record.mps if mp.node_id == "mp_deveaux_patricia"), None)
        assert speaker is not None, "Speaker not found"
        assert speaker.node_type == "control"

    def test_party_composition(self):
        """Party composition matches expected: 32 PLP, 6 FNM, 1 COI."""
        record = _load_record()
        parties = {}
        for mp in record.mps:
            parties[mp.party] = parties.get(mp.party, 0) + 1
        assert parties.get("PLP", 0) == 32
        assert parties.get("FNM", 0) == 6
        assert parties.get("COI", 0) == 1


class TestDateParsing:
    """Validate that portfolio dates are parsed to datetime.date objects."""

    def test_portfolio_dates_are_date_objects(self):
        """After loading, portfolio start_date/end_date are datetime.date, not strings."""
        record = _load_record()
        for mp in record.mps:
            for p in mp.portfolios:
                assert isinstance(p.start_date, date), (
                    f"{mp.node_id}: start_date is {type(p.start_date)}, expected date"
                )
                if p.end_date is not None:
                    assert isinstance(p.end_date, date), (
                        f"{mp.node_id}: end_date is {type(p.end_date)}, expected date"
                    )

    def test_active_portfolios_have_null_end_date(self):
        """Current portfolios have end_date=None."""
        record = _load_record()
        pm = next(mp for mp in record.mps if mp.node_id == "mp_davis_brave")
        assert pm.portfolios[0].end_date is None


class TestComputedAliases:
    """Validate computed alias generation (GR-2)."""

    def test_all_aliases_exceeds_manual(self):
        """Every MP with portfolios has more all_aliases than manual aliases."""
        record = _load_record()
        for mp in record.mps:
            if mp.portfolios:
                assert len(mp.all_aliases) > len(mp.aliases), (
                    f"{mp.node_id}: all_aliases ({len(mp.all_aliases)}) "
                    f"should exceed manual ({len(mp.aliases)})"
                )

    def test_total_aliases_at_least_357(self):
        """Total unique aliases across all MPs >= 357."""
        record = _load_record()
        total = sum(len(mp.all_aliases) for mp in record.mps)
        assert total >= 357, f"Total aliases {total} < 357"

    def test_constituency_aliases_generated(self):
        """Each MP has 'Member for X' and 'The Member for X' in all_aliases."""
        record = _load_record()
        for mp in record.mps:
            assert f"Member for {mp.constituency}" in mp.all_aliases, (
                f"{mp.node_id}: missing 'Member for {mp.constituency}'"
            )
            assert f"The Member for {mp.constituency}" in mp.all_aliases, (
                f"{mp.node_id}: missing 'The Member for {mp.constituency}'"
            )

    def test_honorific_aliases_generated(self):
        """Each MP has 'Hon. X' and 'The Honourable X' in all_aliases."""
        record = _load_record()
        for mp in record.mps:
            assert f"Hon. {mp.common_name}" in mp.all_aliases, (
                f"{mp.node_id}: missing 'Hon. {mp.common_name}'"
            )
            assert f"The Honourable {mp.common_name}" in mp.all_aliases, (
                f"{mp.node_id}: missing 'The Honourable {mp.common_name}'"
            )

    def test_portfolio_short_title_in_aliases(self):
        """Portfolio short_title appears in all_aliases for MPs with portfolios."""
        record = _load_record()
        pm = next(mp for mp in record.mps if mp.node_id == "mp_davis_brave")
        assert "Prime Minister" in pm.all_aliases
        assert "The Prime Minister" in pm.all_aliases

    def test_full_name_in_aliases(self):
        """Full legal name appears in all_aliases."""
        record = _load_record()
        pm = next(mp for mp in record.mps if mp.node_id == "mp_davis_brave")
        assert "Philip Edward Davis, K.C." in pm.all_aliases

    def test_all_aliases_are_deduplicated(self):
        """all_aliases contains no duplicates."""
        record = _load_record()
        for mp in record.mps:
            assert len(mp.all_aliases) == len(set(mp.all_aliases)), (
                f"{mp.node_id} has duplicate aliases"
            )


class TestTemporalQueries:
    """Validate temporal portfolio queries (GR-3)."""

    def test_portfolio_is_active_on(self):
        """PortfolioTenure.is_active_on works correctly."""
        record = _load_record()
        sears = next(mp for mp in record.mps if mp.node_id == "mp_sears_alfred")
        works = sears.portfolios[0]  # Minister of Works, 2021-09-17 to 2023-09-03
        assert works.is_active_on(date(2023, 8, 1))
        assert not works.is_active_on(date(2023, 10, 1))

    def test_who_held_minister_of_works_before_reshuffle(self):
        """Before Sept 3 2023, Sears held Minister of Works."""
        record = _load_record()
        holders = record.who_held_portfolio("Minister of Works", date(2023, 8, 1))
        node_ids = [mp.node_id for mp in holders]
        assert "mp_sears_alfred" in node_ids
        assert "mp_sweeting_clay" not in node_ids

    def test_who_held_minister_of_works_after_reshuffle(self):
        """After Sept 3 2023, Sweeting holds Minister of Works."""
        record = _load_record()
        holders = record.who_held_portfolio("Minister of Works", date(2023, 10, 1))
        node_ids = [mp.node_id for mp in holders]
        assert "mp_sweeting_clay" in node_ids
        assert "mp_sears_alfred" not in node_ids

    def test_aliases_on_date_filters_portfolios(self):
        """aliases_on() includes only temporally valid portfolio aliases."""
        record = _load_record()
        sears = next(mp for mp in record.mps if mp.node_id == "mp_sears_alfred")
        aliases_aug = sears.aliases_on(date(2023, 8, 1))
        aliases_oct = sears.aliases_on(date(2023, 10, 1))
        assert "Minister of Works" in aliases_aug
        assert "Minister of Works" not in aliases_oct
        assert "Minister of Immigration" not in aliases_aug
        assert "Minister of Immigration" in aliases_oct

    def test_resolve_alias_candidates_temporal(self):
        """resolve_alias_candidates with date returns temporally valid matches."""
        record = _load_record()
        candidates = record.resolve_alias_candidates("Minister of Works", date(2023, 8, 1))
        assert len(candidates) == 1
        assert candidates[0].node_id == "mp_sears_alfred"
        candidates = record.resolve_alias_candidates("Minister of Works", date(2023, 10, 1))
        assert len(candidates) == 1
        assert candidates[0].node_id == "mp_sweeting_clay"

    def test_resolve_alias_candidates_no_date_returns_all(self):
        """resolve_alias_candidates without date returns all MPs who ever held that alias."""
        record = _load_record()
        candidates = record.resolve_alias_candidates("Minister of Works")
        node_ids = [mp.node_id for mp in candidates]
        assert "mp_sears_alfred" in node_ids
        assert "mp_sweeting_clay" in node_ids

    def test_current_portfolio_active_on_today(self):
        """Portfolios with null end_date are active today."""
        record = _load_record()
        pm = next(mp for mp in record.mps if mp.node_id == "mp_davis_brave")
        assert pm.portfolios[0].is_active_on(date.today())
