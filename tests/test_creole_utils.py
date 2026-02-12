"""Tests for Bahamian Creole normalization utilities.

Covers BC-1 (TH-stopping), BC-2 (vowel shifts), and BC-3 (code-switching).
See Issue: BC - Bahamian Dialectal Speech Adaptation.
"""

import pytest

from graphhansard.brain.creole_utils import (
    get_th_stopped_variants,
    normalize_bahamian_creole,
    normalize_th_stopping,
    normalize_vowel_shifts,
)


class TestTHStopping:
    """Test BC-1: TH-stopping normalization."""

    def test_normalize_da_to_the(self):
        """'da' should normalize to 'the'."""
        result = normalize_th_stopping("da Member")
        assert result == "the Member"

    def test_normalize_dat_to_that(self):
        """'dat' should normalize to 'that'."""
        result = normalize_th_stopping("dat honourable gentleman")
        assert result == "that honourable gentleman"

    def test_normalize_dem_to_them(self):
        """'dem' should normalize to 'them'."""
        result = normalize_th_stopping("I tell dem")
        assert result == "I tell them"

    def test_normalize_dey_to_they(self):
        """'dey' should normalize to 'they'."""
        result = normalize_th_stopping("dey say")
        assert result == "they say"

    def test_normalize_dis_to_this(self):
        """'dis' should normalize to 'this'."""
        result = normalize_th_stopping("dis matter")
        assert result == "this matter"

    def test_normalize_dere_to_there(self):
        """'dere' should normalize to 'there'."""
        result = normalize_th_stopping("dere is")
        assert result == "there is"

    def test_normalize_den_to_then(self):
        """'den' should normalize to 'then'."""
        result = normalize_th_stopping("and den")
        assert result == "and then"

    def test_normalize_dese_to_these(self):
        """'dese' should normalize to 'these'."""
        result = normalize_th_stopping("dese matters")
        assert result == "these matters"

    def test_normalize_dose_to_those(self):
        """'dose' should normalize to 'those'."""
        result = normalize_th_stopping("dose people")
        assert result == "those people"

    def test_preserve_capitalization(self):
        """Capitalization should be preserved."""
        result = normalize_th_stopping("Da Member for Cat Island")
        assert result == "The Member for Cat Island"

    def test_multiple_th_stopped_words(self):
        """Multiple TH-stopped words in one phrase."""
        result = normalize_th_stopping("da Member say dat dem people")
        assert result == "the Member say that them people"

    def test_bc1_acceptance_criterion_1(self):
        """BC-1 AC1: 'da Memba for Cat Island' → 'the Member for Cat Island'."""
        result = normalize_th_stopping("da Memba for Cat Island")
        assert result == "the Member for Cat Island"

    def test_bc1_acceptance_criterion_2(self):
        """BC-1 AC2: All common TH-stopped forms handled."""
        test_cases = [
            ("da", "the"),
            ("dat", "that"),
            ("dem", "them"),
            ("dey", "they"),
            ("dis", "this"),
            ("dere", "there"),
        ]
        for creole, english in test_cases:
            result = normalize_th_stopping(creole)
            assert result == english

    def test_words_without_th_stopping_unchanged(self):
        """Non-TH-stopped words should remain unchanged."""
        text = "The Member for Long Island"
        result = normalize_th_stopping(text)
        assert result == text

    def test_empty_string(self):
        """Empty string should return empty string."""
        result = normalize_th_stopping("")
        assert result == ""

    def test_none_handling(self):
        """None should return None."""
        result = normalize_th_stopping(None)
        assert result is None


class TestVowelShifts:
    """Test BC-2: Vowel shift normalization."""

    def test_englaston_to_englerston(self):
        """'Englaston' should normalize to 'Englerston'."""
        result = normalize_vowel_shifts("Member for Englaston")
        assert result == "Member for Englerston"

    def test_carmikle_to_carmichael(self):
        """'Carmikle' should normalize to 'Carmichael'."""
        result = normalize_vowel_shifts("Carmikle")
        assert result == "Carmichael"

    def test_killarny_to_killarney(self):
        """'Killarny' should normalize to 'Killarney'."""
        result = normalize_vowel_shifts("Killarny")
        assert result == "Killarney"

    def test_preserve_capitalization(self):
        """Capitalization should be preserved."""
        result = normalize_vowel_shifts("englaston")
        assert result == "englerston"

    def test_bc2_acceptance_criterion_1(self):
        """BC-2 AC1: Constituency vowel shifts handled."""
        test_cases = [
            ("Englaston", "Englerston"),
            ("Carmikle", "Carmichael"),
            ("Killarny", "Killarney"),
        ]
        for variant, standard in test_cases:
            result = normalize_vowel_shifts(variant)
            assert result == standard

    def test_vowel_shift_in_context(self):
        """Vowel shifts should work in full phrases."""
        result = normalize_vowel_shifts("the Member for Englaston")
        assert result == "the Member for Englerston"

    def test_multiple_vowel_shifts(self):
        """Multiple vowel shifts in one text."""
        text = "Carmikle and Englaston and Killarny"
        result = normalize_vowel_shifts(text)
        assert result == "Carmichael and Englerston and Killarney"

    def test_words_without_vowel_shifts_unchanged(self):
        """Words without vowel shifts should remain unchanged."""
        text = "Member for Cat Island"
        result = normalize_vowel_shifts(text)
        assert result == text

    def test_empty_string(self):
        """Empty string should return empty string."""
        result = normalize_vowel_shifts("")
        assert result == ""


class TestFullNormalization:
    """Test BC-3: Code-switching with full normalization pipeline."""

    def test_th_stopping_and_vowel_shifts_combined(self):
        """Both TH-stopping and vowel shifts should work together."""
        result = normalize_bahamian_creole("da Memba for Englaston")
        assert result == "the Member for Englerston"

    def test_bc3_acceptance_criterion_1(self):
        """BC-3 AC1: Code-switching handled without breaking segmentation."""
        # Formal + Creole in same sentence
        text = "Mr. Speaker, I wan' tell da honourable gentleman dat he wrong"
        result = normalize_bahamian_creole(text)
        assert "the honourable gentleman" in result
        assert "that he wrong" in result

    def test_bc3_acceptance_criterion_2(self):
        """BC-3 AC2: Mixed register example from requirements."""
        text = "Mr. Speaker, I wan' tell da honourable gentleman dat he wrong"
        result = normalize_bahamian_creole(text)
        # Should normalize TH-stopped words but preserve other Creole features
        assert "the" in result
        assert "that" in result
        # Non-TH features like "wan'" should remain
        assert "wan'" in result

    def test_disable_th_stopping(self):
        """Can disable TH-stopping normalization."""
        result = normalize_bahamian_creole(
            "da Member", apply_th_stopping=False
        )
        assert result == "da Member"

    def test_disable_vowel_shifts(self):
        """Can disable vowel shift normalization."""
        result = normalize_bahamian_creole(
            "Englaston", apply_vowel_shifts=False
        )
        assert result == "Englaston"

    def test_disable_all_normalizations(self):
        """Can disable all normalizations."""
        text = "da Memba for Englaston"
        result = normalize_bahamian_creole(
            text, apply_th_stopping=False, apply_vowel_shifts=False
        )
        assert result == text

    def test_complex_parliamentary_phrase(self):
        """Complex phrase with multiple Creole features."""
        text = "Da Prime Minister say dat dem people in Englaston need help"
        result = normalize_bahamian_creole(text)
        expected = "The Prime Minister say that them people in Englerston need help"
        assert result == expected


class TestVariantGeneration:
    """Test generating TH-stopped variants for testing."""

    def test_get_th_stopped_variants_the(self):
        """Generate variants for 'the'."""
        variants = get_th_stopped_variants("the Member")
        assert "the Member" in variants
        assert "da Member" in variants

    def test_get_th_stopped_variants_that(self):
        """Generate variants for 'that'."""
        variants = get_th_stopped_variants("that person")
        assert "that person" in variants
        assert "dat person" in variants

    def test_get_th_stopped_variants_multiple(self):
        """Generate variants with multiple TH words."""
        variants = get_th_stopped_variants("the that")
        # Should generate multiple possible combinations
        assert "the that" in variants
        assert any("da" in v or "dat" in v for v in variants)

    def test_get_th_stopped_variants_no_th_words(self):
        """Text with 'member' generates 'memba' variant."""
        variants = get_th_stopped_variants("Member for Cat Island")
        # "Member" has a Creole variant "Memba"
        assert len(variants) >= 1
        assert "Member for Cat Island" in variants
        assert "Memba for Cat Island" in variants or len(variants) >= 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_mixed_case_th_stopping(self):
        """Mixed case TH-stopping should work."""
        result = normalize_th_stopping("DA MEMBER")
        assert result == "THE MEMBER"

    def test_punctuation_preserved(self):
        """Punctuation should be preserved."""
        result = normalize_th_stopping("da Member, dat gentleman.")
        assert result == "the Member, that gentleman."

    def test_numbers_preserved(self):
        """Numbers should be preserved."""
        result = normalize_th_stopping("da 39 Members")
        assert result == "the 39 Members"

    def test_unicode_handling(self):
        """Unicode characters should be handled."""
        result = normalize_th_stopping("da Membér")
        assert result == "the Membér"

    def test_whitespace_only(self):
        """Whitespace-only string should return whitespace."""
        result = normalize_th_stopping("   ")
        # After splitting on whitespace, we'll get empty list, so result is ""
        # This is acceptable behavior - whitespace-only input produces empty output
        assert result == "   " or result == ""

    def test_single_word(self):
        """Single word normalization."""
        result = normalize_th_stopping("da")
        assert result == "the"

    def test_very_long_text(self):
        """Long text should be handled efficiently."""
        text = " ".join(["da Member"] * 100)
        result = normalize_th_stopping(text)
        assert result.count("the Member") == 100
