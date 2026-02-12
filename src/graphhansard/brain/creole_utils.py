"""Bahamian Creole normalization utilities.

Provides text normalization functions to handle Bahamian Creole phonological
patterns, TH-stopping, vowel shifts, and code-switching scenarios.

See SRD §11.1 (BC-1, BC-2, BC-3) for requirements.
"""

from __future__ import annotations


# TH-stopping mappings: Bahamian Creole → Standard English (BC-1)
TH_STOPPING_MAP = {
    "da": "the",
    "dat": "that",
    "dem": "them",
    "dey": "they",
    "dis": "this",
    "dere": "there",
    "den": "then",
    "dese": "these",
    "dose": "those",
    "memba": "member",  # Also common in Bahamian Creole
    "memba's": "member's",
    "membas": "members",
}


# Common vowel shift patterns in Bahamian place names (BC-2)
VOWEL_SHIFT_PATTERNS = {
    # e → a patterns
    "englaston": "englerston",
    "carmikle": "carmichael",
    "killarny": "killarney",
}


def normalize_th_stopping(text: str) -> str:
    """Normalize TH-stopped Bahamian Creole words to Standard English.
    
    Implements BC-1 requirement: Handle TH-stopping without hallucination.
    
    Args:
        text: Input text that may contain TH-stopped words
        
    Returns:
        Text with TH-stopped words normalized to Standard English
        
    Examples:
        >>> normalize_th_stopping("da Memba for Cat Island")
        'the Member for Cat Island'
        >>> normalize_th_stopping("I wan' tell dat honourable gentleman")
        'I wan' tell that honourable gentleman'
    """
    if not text or not text.strip():
        return text
    
    # Split into words, preserving case
    words = text.split()
    normalized_words = []
    
    for word in words:
        # Check if word (lowercased) is in TH-stopping map
        lower_word = word.lower()
        if lower_word in TH_STOPPING_MAP:
            # Replace while preserving capitalization pattern
            replacement = TH_STOPPING_MAP[lower_word]
            # Handle all-uppercase words
            if word.isupper():
                replacement = replacement.upper()
            elif word[0].isupper():
                replacement = replacement.capitalize()
            normalized_words.append(replacement)
        else:
            normalized_words.append(word)
    
    return " ".join(normalized_words)


def normalize_vowel_shifts(text: str) -> str:
    """Normalize vowel shifts in Bahamian place names and surnames.
    
    Implements BC-2 requirement: Tolerate vowel shifts in constituency names.
    
    Args:
        text: Input text that may contain vowel-shifted place names
        
    Returns:
        Text with vowel shifts normalized to standard spellings
        
    Examples:
        >>> normalize_vowel_shifts("Member for Englaston")
        'Member for Englerston'
        >>> normalize_vowel_shifts("the hon. member for Killarny")
        'the hon. member for Killarney'
    """
    if not text:
        return text
    
    # Case-insensitive replacement using word boundaries
    normalized = text
    for variant, standard in VOWEL_SHIFT_PATTERNS.items():
        # Match whole words or parts of constituency names
        # Use case-insensitive search and preserve original case
        import re
        pattern = re.compile(re.escape(variant), re.IGNORECASE)
        
        def replace_preserving_case(match):
            matched_text = match.group(0)
            if matched_text[0].isupper():
                return standard.capitalize()
            return standard
        
        normalized = pattern.sub(replace_preserving_case, normalized)
    
    return normalized


def normalize_bahamian_creole(text: str, apply_th_stopping: bool = True, 
                              apply_vowel_shifts: bool = True) -> str:
    """Full Bahamian Creole normalization pipeline.
    
    Combines TH-stopping normalization and vowel shift handling to support
    BC-1, BC-2, and BC-3 (code-switching) requirements.
    
    Args:
        text: Input text in Bahamian Creole or mixed register
        apply_th_stopping: Whether to normalize TH-stopped words (default: True)
        apply_vowel_shifts: Whether to normalize vowel shifts (default: True)
        
    Returns:
        Normalized text suitable for entity resolution
        
    Examples:
        >>> normalize_bahamian_creole("da Memba for Englaston")
        'the Member for Englerston'
        >>> normalize_bahamian_creole("Mr. Speaker, I wan' tell dat honourable gentleman")
        'Mr. Speaker, I wan' tell that honourable gentleman'
    """
    if not text:
        return text
    
    normalized = text
    
    if apply_th_stopping:
        normalized = normalize_th_stopping(normalized)
    
    if apply_vowel_shifts:
        normalized = normalize_vowel_shifts(normalized)
    
    return normalized


def get_th_stopped_variants(text: str) -> list[str]:
    """Generate TH-stopped variants of a phrase for fuzzy matching.
    
    Useful for creating test data or expanding alias lists.
    
    Args:
        text: Standard English text
        
    Returns:
        List of possible TH-stopped variants
        
    Examples:
        >>> get_th_stopped_variants("the Member")
        ['da Member', 'the Member']
    """
    variants = [text]
    
    # Reverse mapping: Standard English → Bahamian Creole
    reverse_map = {v: k for k, v in TH_STOPPING_MAP.items()}
    
    words = text.split()
    for i, word in enumerate(words):
        lower_word = word.lower()
        if lower_word in reverse_map:
            variant_words = words.copy()
            replacement = reverse_map[lower_word]
            if word[0].isupper():
                replacement = replacement.capitalize()
            variant_words[i] = replacement
            variants.append(" ".join(variant_words))
    
    return list(set(variants))  # Remove duplicates
