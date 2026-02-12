"""Stage 2 — Entity extraction, co-reference resolution, and mention logging.

Scans transcripts for MP references using pattern matching and NER,
resolves via the Golden Record, and handles anaphoric references.
See SRD §8.3 (BR-9 through BR-15).
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from graphhansard.golden_record.resolver import AliasResolver


class ResolutionMethod(str, Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    COREFERENCE = "coreference"
    LLM = "llm"
    UNRESOLVED = "unresolved"


class MentionRecord(BaseModel):
    """A single MP-to-MP mention extracted from a transcript."""

    session_id: str
    source_node_id: str = Field(description="MP who made the mention (the speaker)")
    target_node_id: str | None = Field(
        description="MP who was mentioned (resolved)"
    )
    raw_mention: str = Field(description="Exact text as spoken/transcribed")
    resolution_method: ResolutionMethod
    resolution_score: float = Field(description="Confidence 0.0-1.0")
    timestamp_start: float
    timestamp_end: float
    context_window: str = Field(description="Surrounding text for verification")
    segment_index: int


class EntityExtractor:
    """Extracts and resolves MP mentions from diarized transcripts.

    Implements BR-9 through BR-13:
    - Pattern matching for parliamentary references
    - spaCy NER for PERSON entities
    - Golden Record resolution
    - Context window extraction (±1 sentence)
    - Precision ≥80% and Recall ≥85% target

    See SRD §8.3 for specification.
    """

    # Parliamentary reference patterns (BR-9)
    PATTERNS = {
        "member_for": re.compile(
            r"(?:The\s+)?Member\s+for\s+[A-Z][A-Za-z\s,]+",
            re.IGNORECASE,
        ),
        "minister_of": re.compile(
            r"(?:The\s+)?Minister\s+(?:of|for)\s+[A-Z][A-Za-z\s,&]+",
            re.IGNORECASE,
        ),
        "honourable": re.compile(
            r"(?:The\s+)?Hon(?:ourable|\.)?\s+[A-Z][A-Za-z\s\.]+",
            re.IGNORECASE,
        ),
        "prime_minister": re.compile(
            r"(?:The\s+)?Prime\s+Minister",
            re.IGNORECASE,
        ),
        "deputy_pm": re.compile(
            r"(?:The\s+)?Deputy\s+Prime\s+Minister",
            re.IGNORECASE,
        ),
        "attorney_general": re.compile(
            r"(?:The\s+)?Attorney\s+General",
            re.IGNORECASE,
        ),
    }

    def __init__(self, golden_record_path: str, use_spacy: bool = False):
        """Initialize the EntityExtractor.

        Args:
            golden_record_path: Path to mps.json Golden Record file
            use_spacy: Whether to use spaCy NER (requires model installation)
        """
        self.golden_record_path = Path(golden_record_path)
        self.resolver = AliasResolver(str(golden_record_path))
        self.use_spacy = use_spacy
        self.nlp = None

        # Initialize spaCy if requested
        if use_spacy:
            try:
                import spacy
                from spacy.lang.en import English

                # Try to load transformer model, fallback to base model
                try:
                    self.nlp = spacy.load("en_core_web_trf")
                except OSError:
                    try:
                        self.nlp = spacy.load("en_core_web_sm")
                    except OSError:
                        # If no model available, create blank and add entity ruler
                        self.nlp = English()
                        self.nlp.add_pipe("sentencizer")

                # Add custom entity ruler for parliamentary titles
                if "entity_ruler" not in self.nlp.pipe_names:
                    ruler = self.nlp.add_pipe("entity_ruler", before="ner" if self.nlp.has_pipe("ner") else "sentencizer")
                    self._add_parliamentary_patterns(ruler)

            except ImportError:
                print("Warning: spaCy not installed. Using pattern matching only.")
                self.use_spacy = False
                self.nlp = None

    def _add_parliamentary_patterns(self, ruler):
        """Add custom entity patterns for parliamentary titles to spaCy ruler."""
        patterns = [
            {"label": "TITLE", "pattern": [{"LOWER": "prime"}, {"LOWER": "minister"}]},
            {"label": "TITLE", "pattern": [{"LOWER": "deputy"}, {"LOWER": "prime"}, {"LOWER": "minister"}]},
            {"label": "TITLE", "pattern": [{"LOWER": "attorney"}, {"LOWER": "general"}]},
            {"label": "TITLE", "pattern": [{"LOWER": "minister"}, {"LOWER": {"IN": ["of", "for"]}}]},
            {"label": "TITLE", "pattern": [{"LOWER": "member"}, {"LOWER": "for"}]},
            {"label": "TITLE", "pattern": [{"LOWER": {"IN": ["hon", "hon.", "honourable", "the"]}}, {"LOWER": {"IN": ["honourable", "hon", "hon."]}}]},
        ]
        ruler.add_patterns(patterns)

    def extract_mentions(self, transcript: dict, debate_date: str | None = None) -> list[MentionRecord]:
        """Extract all MP mentions from a diarized transcript.

        Args:
            transcript: DiarizedTranscript dict with session_id and segments
            debate_date: ISO date string for temporal resolution (e.g., "2023-11-15")

        Returns:
            List of MentionRecord objects with resolved MP mentions
        """
        session_id = transcript.get("session_id", "unknown")
        segments = transcript.get("segments", [])
        
        all_mentions = []
        
        for idx, segment in enumerate(segments):
            # Extract mentions from this segment
            segment_mentions = self._extract_from_segment(
                segment, idx, session_id, segments, debate_date
            )
            all_mentions.extend(segment_mentions)
        
        return all_mentions

    def _extract_from_segment(
        self, segment: dict, segment_index: int, session_id: str, 
        all_segments: list[dict], debate_date: str | None
    ) -> list[MentionRecord]:
        """Extract mentions from a single transcript segment.

        Args:
            segment: TranscriptSegment dict with text, timestamps, speaker info
            segment_index: Index of this segment in the transcript
            session_id: Session identifier
            all_segments: All segments for context window extraction
            debate_date: Optional date for temporal resolution

        Returns:
            List of MentionRecord objects found in this segment
        """
        text = segment.get("text", "")
        source_node_id = segment.get("speaker_node_id")
        start_time = segment.get("start_time", 0.0)
        end_time = segment.get("end_time", 0.0)
        
        # Skip if no speaker identified or empty text
        if not source_node_id or not text.strip():
            return []
        
        mentions = []
        
        # Phase 1: Pattern matching (BR-9)
        pattern_mentions = self._extract_pattern_mentions(text)
        
        # Phase 2: spaCy NER (if enabled)
        ner_mentions = []
        if self.use_spacy and self.nlp:
            ner_mentions = self._extract_ner_mentions(text)
        
        # Combine and deduplicate mentions
        all_raw_mentions = self._deduplicate_mentions(pattern_mentions + ner_mentions)
        
        # Resolve each mention and create MentionRecord
        for raw_mention, char_start, char_end in all_raw_mentions:
            # Resolve via Golden Record (BR-10)
            resolution = self.resolver.resolve(raw_mention, debate_date)
            
            # Determine resolution method based on resolver output
            if resolution.method == "exact":
                res_method = ResolutionMethod.EXACT
            elif resolution.method == "fuzzy":
                res_method = ResolutionMethod.FUZZY
            else:
                res_method = ResolutionMethod.UNRESOLVED
            
            # Extract context window (±1 sentence) (BR-12)
            context = self._extract_context_window(
                segment_index, all_segments, char_start, char_end
            )
            
            # Estimate mention timestamps (proportional to character position)
            mention_start, mention_end = self._estimate_mention_timestamps(
                text, char_start, char_end, start_time, end_time
            )
            
            mention_record = MentionRecord(
                session_id=session_id,
                source_node_id=source_node_id,
                target_node_id=resolution.node_id,
                raw_mention=raw_mention,
                resolution_method=res_method,
                resolution_score=resolution.confidence,
                timestamp_start=mention_start,
                timestamp_end=mention_end,
                context_window=context,
                segment_index=segment_index,
            )
            
            mentions.append(mention_record)
        
        return mentions

    def _extract_pattern_mentions(self, text: str) -> list[tuple[str, int, int]]:
        """Extract mentions using regex patterns.

        Returns:
            List of (mention_text, char_start, char_end) tuples
        """
        mentions = []
        
        # Common words that typically follow mentions (not part of the title)
        stop_words = [
            'said', 'spoke', 'mentioned', 'stated', 'asked', 'replied',
            'announced', 'presented', 'addressed', 'raised', 'discussed',
            'opened', 'responded', 'and', 'or', 'but'
        ]
        
        for pattern_name, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                # Get the full match as the mention
                mention_text = match.group(0).strip()
                char_start = match.start()
                
                # Clean up the mention - stop at stop words
                words = mention_text.split()
                cleaned_words = []
                for word in words:
                    word_lower = word.lower().strip('.,!?;:')
                    if word_lower in stop_words:
                        break
                    cleaned_words.append(word)
                
                mention_text = ' '.join(cleaned_words).strip()
                char_end = char_start + len(mention_text)
                
                # Only add if mention is substantial (at least 5 chars)
                if len(mention_text) >= 5:
                    mentions.append((mention_text, char_start, char_end))
        
        return mentions

    def _extract_ner_mentions(self, text: str) -> list[tuple[str, int, int]]:
        """Extract PERSON entities using spaCy NER.

        Returns:
            List of (mention_text, char_start, char_end) tuples
        """
        if not self.nlp:
            return []
        
        mentions = []
        doc = self.nlp(text)
        
        for ent in doc.ents:
            # Extract PERSON entities and parliamentary TITLE entities
            if ent.label_ in ("PERSON", "TITLE"):
                mention_text = ent.text.strip()
                char_start = ent.start_char
                char_end = ent.end_char
                
                # Filter out very short mentions (likely false positives)
                if len(mention_text) >= 3:
                    mentions.append((mention_text, char_start, char_end))
        
        return mentions

    def _deduplicate_mentions(
        self, mentions: list[tuple[str, int, int]]
    ) -> list[tuple[str, int, int]]:
        """Remove duplicate and overlapping mentions.

        Keeps the longest mention when overlaps occur.
        """
        if not mentions:
            return []
        
        # Sort by start position, then by length (descending)
        sorted_mentions = sorted(mentions, key=lambda x: (x[1], -(x[2] - x[1])))
        
        deduplicated = []
        last_end = -1
        
        for mention, start, end in sorted_mentions:
            # Skip if this mention overlaps with the previous one
            if start < last_end:
                continue
            
            deduplicated.append((mention, start, end))
            last_end = end
        
        return deduplicated

    def _extract_context_window(
        self, segment_index: int, all_segments: list[dict], 
        char_start: int, char_end: int
    ) -> str:
        """Extract ±1 sentence context around mention (BR-12).

        Args:
            segment_index: Current segment index
            all_segments: All transcript segments
            char_start: Character position of mention start
            char_end: Character position of mention end

        Returns:
            Context string with surrounding sentences
        """
        current_segment = all_segments[segment_index]
        text = current_segment.get("text", "")
        
        # Simple sentence splitting (can be improved with spaCy)
        sentences = self._split_sentences(text)
        
        # Find which sentence contains the mention
        char_pos = 0
        mention_sentence_idx = 0
        
        for idx, sentence in enumerate(sentences):
            sentence_end = char_pos + len(sentence)
            if char_pos <= char_start < sentence_end:
                mention_sentence_idx = idx
                break
            char_pos = sentence_end
        
        # Extract ±1 sentence
        start_idx = max(0, mention_sentence_idx - 1)
        end_idx = min(len(sentences), mention_sentence_idx + 2)
        
        context_sentences = sentences[start_idx:end_idx]
        return " ".join(context_sentences).strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Simple sentence splitter.

        Can be enhanced with spaCy's sentencizer for better accuracy.
        """
        # Simple split on .!? followed by space and capital letter
        sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        sentences = sentence_pattern.split(text)
        
        # If no sentences found, return the whole text
        if not sentences or len(sentences) == 1:
            return [text]
        
        return [s.strip() for s in sentences if s.strip()]

    def _estimate_mention_timestamps(
        self, text: str, char_start: int, char_end: int, 
        segment_start: float, segment_end: float
    ) -> tuple[float, float]:
        """Estimate timestamps for a mention within a segment.

        Uses proportional mapping based on character positions.
        """
        text_length = len(text)
        if text_length == 0:
            return segment_start, segment_end
        
        segment_duration = segment_end - segment_start
        
        # Calculate proportional timestamps
        start_ratio = char_start / text_length
        end_ratio = char_end / text_length
        
        mention_start = segment_start + (start_ratio * segment_duration)
        mention_end = segment_start + (end_ratio * segment_duration)
        
        return mention_start, mention_end

    def resolve_coreference(
        self, mention: str, speaker_history: list[dict]
    ) -> str | None:
        """Resolve anaphoric/deictic references using speaker turn context.

        This is a placeholder for future coreference resolution (BR-11).
        For v1.0, anaphoric references will be logged as unresolved.

        Args:
            mention: The anaphoric mention (e.g., "the gentleman who just spoke")
            speaker_history: Recent speaker turns for context

        Returns:
            Resolved node_id or None if unresolvable
        """
        # TODO: Implement coreference resolution in future version
        # For now, return None (will be logged as unresolved)
        return None
