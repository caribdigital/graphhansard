# Bahamian Creole Speech Adaptation (BC-1, BC-2, BC-3)

## Overview

GraphHansard includes specialized normalization to handle **Bahamian Creole** phonological patterns, vowel shifts, and code-switching between Standard English and Bahamian Creole. This ensures accurate transcription and entity resolution for Bahamian parliamentary speech.

See SRD §11.1 for detailed requirements.

---

## Features

### BC-1: TH-Stopping Normalization

**Problem:** Bahamian Creole replaces "th" sounds with "d" sounds (TH-stopping):
- "da" → "the"
- "dat" → "that"
- "dem" → "them"
- "dis" → "this"
- "memba" → "member"

**Solution:** Automatic normalization in both transcription and alias resolution pipelines.

**Example:**
```python
from graphhansard.brain import normalize_th_stopping

result = normalize_th_stopping("da Memba for Cat Island")
# Output: "the Member for Cat Island"
```

---

### BC-2: Vowel Shift Normalization

**Problem:** Common vowel shifts in Bahamian place names and surnames:
- "Englaston" → "Englerston"
- "Carmikle" → "Carmichael"
- "Killarny" → "Killarney"

**Solution:** Pattern-based normalization with case preservation.

**Example:**
```python
from graphhansard.brain import normalize_vowel_shifts

result = normalize_vowel_shifts("Member for Englaston")
# Output: "Member for Englerston"
```

---

### BC-3: Code-Switching Support

**Problem:** MPs frequently switch between Standard English and Bahamian Creole mid-sentence:
- "Mr. Speaker, I wan' tell da honourable gentleman dat he wrong"

**Solution:** Full normalization pipeline preserves non-TH Creole features while normalizing TH-stopping and vowel shifts for entity resolution.

**Example:**
```python
from graphhansard.brain import normalize_bahamian_creole

result = normalize_bahamian_creole("da Memba for Englaston")
# Output: "the Member for Englerston"
```

---

## API Reference

### `normalize_th_stopping(text: str) -> str`

Normalize TH-stopped Bahamian Creole words to Standard English.

**Parameters:**
- `text`: Input text that may contain TH-stopped words

**Returns:**
- Text with TH-stopped words normalized to Standard English

**Mappings:**
```python
{
    "da": "the",
    "dat": "that",
    "dem": "them",
    "dey": "they",
    "dis": "this",
    "dere": "there",
    "den": "then",
    "dese": "these",
    "dose": "those",
    "memba": "member",
}
```

---

### `normalize_vowel_shifts(text: str) -> str`

Normalize vowel shifts in Bahamian place names and surnames.

**Parameters:**
- `text`: Input text that may contain vowel-shifted place names

**Returns:**
- Text with vowel shifts normalized to standard spellings

**Patterns:**
```python
{
    "englaston": "englerston",
    "carmikle": "carmichael",
    "killarny": "killarney",
}
```

---

### `normalize_bahamian_creole(text: str, apply_th_stopping: bool = True, apply_vowel_shifts: bool = True) -> str`

Full Bahamian Creole normalization pipeline.

**Parameters:**
- `text`: Input text in Bahamian Creole or mixed register
- `apply_th_stopping`: Whether to normalize TH-stopped words (default: True)
- `apply_vowel_shifts`: Whether to normalize vowel shifts (default: True)

**Returns:**
- Normalized text suitable for entity resolution

---

## Usage in Transcription Pipeline

The `Transcriber` class automatically applies Creole normalization:

```python
from graphhansard.brain import Transcriber

# Creole normalization enabled by default
transcriber = Transcriber(
    model_size="large-v3",
    device="cuda",
    normalize_creole=True  # default
)

# To disable normalization:
transcriber_no_creole = Transcriber(
    model_size="large-v3",
    device="cuda",
    normalize_creole=False
)
```

---

## Usage in Alias Resolution

The `AliasResolver` class automatically applies Creole normalization:

```python
from graphhansard.golden_record.resolver import AliasResolver

# Creole normalization enabled by default
resolver = AliasResolver(
    golden_record_path="golden_record/mps.json",
    fuzzy_threshold=85,
    normalize_creole=True  # default
)

# Resolve Creole mention
result = resolver.resolve("da Memba for Cat Island")
# Returns: ResolutionResult(node_id='mp_davis_brave', confidence=1.0, method='exact')
```

---

## Testing

Comprehensive test coverage in `tests/test_creole_utils.py`:

```bash
# Run Creole normalization tests
pytest tests/test_creole_utils.py -v

# Run integration tests
pytest tests/test_alias_resolver.py::TestBahamianCreoleNormalization -v
pytest tests/test_brain.py::TestBahamianCreoleTranscription -v
```

---

## Acceptance Criteria

### BC-1: TH-Stopping
✅ Whisper transcription of "da Memba for Cat Island" → "the Member for Cat Island"  
✅ Common TH-stopped forms handled: da, dat, dem, dey, dis, dere, memba  
✅ No hallucinated words from TH-stopping

### BC-2: Vowel Shifts
✅ Fuzzy matching tolerates vowel shifts:
- "Englaston" → "Englerston" (≥85 fuzzy score)
- "Carmikle" → "Carmichael"
- "Killarny" → "Killarney"

### BC-3: Code-Switching
✅ System handles mid-sentence register shifts without breaking transcript segmentation  
✅ Entity extraction works across both registers in a single turn

---

## Future Enhancements

Potential improvements for future releases:

1. **Dynamic Learning:** Machine learning-based detection of new Creole patterns from community feedback
2. **Contextual Disambiguation:** Use surrounding context to disambiguate TH-stopped homophones
3. **Expanded Vocabulary:** Add more Bahamian Creole words beyond TH-stopping (e.g., "een" → "isn't")
4. **Confidence Scoring:** Provide confidence scores for Creole normalization decisions
5. **Audio-level Features:** Analyze acoustic features to detect Creole vs. Standard English speech directly

---

## References

- **SRD v1.0 §11.1:** Dialectal Speech Adaptation requirements
- **Issue:** BC - Bahamian Dialectal Speech Adaptation
- **Risk R-2:** Whisper WER on Bahamian speech may exceed 15% target

---

## License

MIT License — Copyright (c) 2026 Carib Digital Labs
