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
    is_self_reference: bool = Field(
        default=False, 
        description="True if speaker refers to themselves (BR-15)"
    )
    
    def to_graph_dict(self, sentiment_label: str | None = None) -> dict:
        """Convert to dict format for GraphBuilder.
        
        Args:
            sentiment_label: Optional sentiment label ("positive", "neutral", "negative")
            
        Returns:
            Dictionary with fields needed by GraphBuilder
        """
        result = {
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "context_window": self.context_window,
            "is_self_reference": self.is_self_reference,
        }
        if sentiment_label is not None:
            result["sentiment_label"] = sentiment_label
        return result


class EntityExtractor:
    """Extracts and resolves MP mentions from diarized transcripts.

    Implements BR-9 through BR-13:
    - Pattern matching for parliamentary references
    - spaCy NER for PERSON entities
    - Golden Record resolution
    - Context window extraction (±1 sentence)
    - Precision ≥80% and Recall ≥85% target

    Respects audio quality flags per BC-9 and BC-10: segments flagged
    with exclude_from_extraction will not produce MentionRecords.

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
        # BC-5: Point of Order detection pattern
        "point_of_order": re.compile(
            r"(?:Mr\.|Madam|Mr|Mdm\.?)\s+Speaker,?\s+(?:I\s+)?(?:rise\s+(?:on\s+)?(?:a\s+)?)?point\s+of\s+order",
            re.IGNORECASE,
        ),
    }
    
    # Deictic/Anaphoric reference patterns (BR-11)
    DEICTIC_PATTERNS = {
        "member_who_spoke": re.compile(
            r"(?:the\s+)?(?:Member|gentleman|lady)\s+who\s+(?:just\s+)?(?:spoke|addressed|mentioned)",
            re.IGNORECASE,
        ),
        "member_opposite": re.compile(
            r"(?:the\s+)?(?:hon(?:ourable|\.)?\s+)?(?:Member|gentleman|lady)\s+opposite",
            re.IGNORECASE,
        ),
        "honourable_friend": re.compile(
            r"my\s+hon(?:ourable|\.)?(?:\s+friend)",
            re.IGNORECASE,
        ),
        "honourable_friend_opposite": re.compile(
            r"my\s+hon(?:ourable|\.)?(?:\s+friend)?\s+opposite",
            re.IGNORECASE,
        ),
        "honourable_colleague": re.compile(
            r"my\s+(?:hon(?:ourable|\.)?\s+)?colleague",
            re.IGNORECASE,
        ),
        "previous_speaker": re.compile(
            r"the\s+(?:previous|last)\s+speaker",
            re.IGNORECASE,
        ),
    }
    
    # Stop words that typically follow mentions (not part of the title)
    STOP_WORDS = [
        'said', 'spoke', 'mentioned', 'stated', 'asked', 'replied',
        'announced', 'presented', 'addressed', 'raised', 'discussed',
        'opened', 'responded', 'or', 'but', 'thanked'
    ]

    def __init__(self, golden_record_path: str, use_spacy: bool = False, context_window_size: int = 3, coreference_confidence: float = 0.8):
        """Initialize the EntityExtractor.

        Args:
            golden_record_path: Path to mps.json Golden Record file
            use_spacy: Whether to use spaCy NER (requires model installation)
            context_window_size: Number of previous speaker turns to consider for coreference (default: 3)
            coreference_confidence: Base confidence score for coreference resolution (default: 0.8)
        """
        self.golden_record_path = Path(golden_record_path)
        self.resolver = AliasResolver(str(golden_record_path))
        self.use_spacy = use_spacy
        self.nlp = None
        self.unresolved_mentions = []  # Track unresolved mentions
        self.context_window_size = context_window_size  # For anaphoric resolution
        self.coreference_confidence = coreference_confidence  # Base confidence for coreference
        
        # Build MP lookup for party/context information
        self._mp_lookup = {
            mp.node_id: mp for mp in self.resolver.golden_record.mps
        }

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
                    # Insert entity ruler before NER if NER exists, otherwise before sentencizer
                    insert_before = "ner" if self.nlp.has_pipe("ner") else "sentencizer"
                    ruler = self.nlp.add_pipe("entity_ruler", before=insert_before)
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

        Per BC-9 and BC-10, segments with exclude_from_extraction=True
        will be skipped and produce no MentionRecords.

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

    def detect_point_of_order(self, transcript: dict) -> list[dict]:
        """Detect Point of Order occurrences in a transcript (BC-5).

        Returns Point of Order events as special procedural markers that can be
        converted to PROCEDURAL_CONFLICT edge types by the graph builder.

        Args:
            transcript: DiarizedTranscript dict with session_id and segments

        Returns:
            List of Point of Order event dicts with:
            - session_id: Session identifier
            - source_node_id: MP who raised the point
            - timestamp_start: When the point was raised
            - timestamp_end: End of the point of order phrase
            - segment_index: Segment number
            - raw_text: Exact text matched
        """
        session_id = transcript.get("session_id", "unknown")
        segments = transcript.get("segments", [])
        point_of_order_events = []

        point_of_order_pattern = self.PATTERNS.get("point_of_order")
        if not point_of_order_pattern:
            return point_of_order_events

        for idx, segment in enumerate(segments):
            text = segment.get("text", "")
            source_node_id = segment.get("speaker_node_id") or segment.get("speaker_label", "UNKNOWN")
            start_time = segment.get("start_time", 0.0)
            end_time = segment.get("end_time", 0.0)

            # Search for "Point of Order" pattern
            for match in point_of_order_pattern.finditer(text):
                # Calculate approximate timestamps for the match
                char_start = match.start()
                char_end = match.end()
                mention_start, mention_end = self._estimate_mention_timestamps(
                    text, char_start, char_end, start_time, end_time
                )

                point_of_order_events.append({
                    "session_id": session_id,
                    "source_node_id": source_node_id,
                    "timestamp_start": mention_start,
                    "timestamp_end": mention_end,
                    "segment_index": idx,
                    "raw_text": match.group(0).strip(),
                })

        return point_of_order_events

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
        source_node_id = segment.get("speaker_node_id") or segment.get("speaker_label", "UNKNOWN")
        start_time = segment.get("start_time", 0.0)
        end_time = segment.get("end_time", 0.0)

        # Skip if empty text
        if not text.strip():
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
            # Check if this is a deictic/anaphoric reference (BR-11)
            is_deictic = self._is_deictic_reference(raw_mention)
            
            # Build speaker history for coreference resolution
            speaker_history = self._build_speaker_history(segment_index, all_segments)
            
            # Initialize resolution
            resolution = None
            target_node_id = None
            res_method = ResolutionMethod.UNRESOLVED
            confidence = 0.0
            
            if is_deictic:
                # Attempt coreference resolution (BR-11)
                target_node_id = self._resolve_coreference(
                    raw_mention, source_node_id, speaker_history, debate_date
                )
                if target_node_id:
                    res_method = ResolutionMethod.COREFERENCE
                    # Use configurable confidence, could be adjusted based on resolution quality
                    confidence = self.coreference_confidence
                else:
                    res_method = ResolutionMethod.UNRESOLVED
                    confidence = 0.0
            else:
                # Resolve via Golden Record (BR-10)
                resolution = self.resolver.resolve(raw_mention, debate_date)
                target_node_id = resolution.node_id
                confidence = resolution.confidence
                
                # Determine resolution method based on resolver output
                if resolution.method == "exact":
                    res_method = ResolutionMethod.EXACT
                elif resolution.method == "fuzzy":
                    res_method = ResolutionMethod.FUZZY
                else:
                    res_method = ResolutionMethod.UNRESOLVED
            
            # Check for self-reference (BR-15)
            is_self_reference = (target_node_id == source_node_id) if target_node_id else False

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
                target_node_id=target_node_id,
                raw_mention=raw_mention,
                resolution_method=res_method,
                resolution_score=confidence,
                timestamp_start=mention_start,
                timestamp_end=mention_end,
                context_window=context,
                segment_index=segment_index,
                is_self_reference=is_self_reference,
            )

            mentions.append(mention_record)

            # Log unresolved mentions for human review (BR-14)
            if target_node_id is None:
                mention_type = "deictic" if is_deictic else "standard"
                self._log_unresolved_mention(
                    raw_mention, session_id, segment_index, debate_date, context,
                    mention_type=mention_type, speaker_id=source_node_id
                )

        return mentions

    def _extract_pattern_mentions(self, text: str) -> list[tuple[str, int, int]]:
        """Extract mentions using regex patterns.

        Deictic patterns (BR-11) are processed first and take priority
        over standard patterns to prevent greedy capture pollution.

        Returns:
            List of (mention_text, char_start, char_end) tuples
        """
        mentions = []

        # Phase 1: Extract deictic/anaphoric patterns first (BR-11) — they take priority
        deictic_ranges = []
        for pattern_name, pattern in self.DEICTIC_PATTERNS.items():
            for match in pattern.finditer(text):
                mention_text = match.group(0).strip()
                char_start = match.start()
                char_end = match.end()

                if len(mention_text) >= 5:
                    mentions.append((mention_text, char_start, char_end))
                    deictic_ranges.append((char_start, char_end))

        # Phase 2: Extract standard parliamentary patterns, skipping deictic overlaps
        for pattern_name, pattern in self.PATTERNS.items():
            if pattern_name == "point_of_order":
                continue  # Handled by detect_point_of_order(), not as MP mention
            for match in pattern.finditer(text):
                mention_text = match.group(0).strip()
                char_start = match.start()

                # Clean up the mention - stop at stop words
                words = mention_text.split()
                cleaned_words = []
                for word in words:
                    word_lower = word.lower().strip('.,!?;:')
                    if word_lower in self.STOP_WORDS:
                        break
                    cleaned_words.append(word)

                mention_text = ' '.join(cleaned_words).strip()
                char_end = char_start + len(mention_text)

                # Skip if overlaps with a deictic match
                overlaps_deictic = any(
                    not (char_end <= d_start or char_start >= d_end)
                    for d_start, d_end in deictic_ranges
                )
                if overlaps_deictic:
                    continue

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

    def _is_deictic_reference(self, mention: str) -> bool:
        """Check if a mention is a deictic/anaphoric reference.
        
        Args:
            mention: The raw mention text
            
        Returns:
            True if the mention matches a deictic pattern
        """
        for pattern_name, pattern in self.DEICTIC_PATTERNS.items():
            if pattern.search(mention):
                return True
        return False

    def _build_speaker_history(
        self, current_segment_index: int, all_segments: list[dict]
    ) -> list[dict]:
        """Build a history of recent speakers for coreference resolution.
        
        Args:
            current_segment_index: Index of current segment
            all_segments: All transcript segments
            
        Returns:
            List of speaker information from previous N segments
        """
        history = []
        start_idx = max(0, current_segment_index - self.context_window_size)
        
        for idx in range(start_idx, current_segment_index):
            segment = all_segments[idx]
            speaker_id = segment.get("speaker_node_id") or segment.get("speaker_label")
            
            if speaker_id and speaker_id != "UNKNOWN":
                history.append({
                    "node_id": speaker_id,
                    "segment_index": idx,
                    "text": segment.get("text", ""),
                })
        
        return history

    def _resolve_coreference(
        self, mention: str, source_node_id: str, speaker_history: list[dict], 
        debate_date: str | None
    ) -> str | None:
        """Resolve deictic/anaphoric references using speaker turn context (BR-11).
        
        Implements context-window heuristic:
        - "the Member who just spoke" → examine previous N speaker turns, score by recency
        - "the honourable gentleman opposite" → use party/seating context to narrow candidates
        - "my honourable friend" → typically same-party; use party affiliation of speaker
        
        Args:
            mention: The anaphoric mention (e.g., "the gentleman who just spoke")
            source_node_id: The speaker making the reference
            speaker_history: Recent speaker turns for context
            debate_date: Optional debate date for temporal context
            
        Returns:
            Resolved node_id or None if unresolvable
        """
        if not speaker_history:
            return None
        
        mention_lower = mention.lower()
        
        # Get source MP info for party-based filtering
        source_mp = self._mp_lookup.get(source_node_id)
        source_party = source_mp.party if source_mp else None
        
        # Determine filtering criteria based on mention type
        # Handle "opposite" as the primary indicator since it overrides "friend"
        same_party_filter = None
        if "opposite" in mention_lower:
            # "opposite" always refers to different party, even if "friend" is present
            # (e.g., "my honourable friend opposite" is a polite way to refer to opposition)
            same_party_filter = False
        elif "my" in mention_lower and "friend" in mention_lower:
            # "my honourable friend" (without "opposite") refers to same party
            same_party_filter = True
        
        # Filter candidates based on party affiliation if applicable
        candidates = []
        for speaker in speaker_history:
            speaker_node_id = speaker["node_id"]
            
            # Skip if it's the source speaker (self-reference check)
            if speaker_node_id == source_node_id:
                continue
            
            # Apply party filter if applicable
            if same_party_filter is not None and source_party:
                speaker_mp = self._mp_lookup.get(speaker_node_id)
                if speaker_mp:
                    speaker_party = speaker_mp.party
                    if same_party_filter and speaker_party != source_party:
                        continue
                    elif not same_party_filter and speaker_party == source_party:
                        continue
            
            candidates.append(speaker)
        
        if not candidates:
            return None
        
        # Score candidates by recency (most recent speaker gets highest score)
        # For "who just spoke" or "previous speaker", strongly prefer most recent
        if "just spoke" in mention_lower or "who spoke" in mention_lower or "previous speaker" in mention_lower:
            # Return the most recent speaker (highest segment index)
            most_recent = max(candidates, key=lambda x: x["segment_index"])
            return most_recent["node_id"]
        
        # For other deictic references, return most recent candidate
        # Return the most recent candidate
        candidates.sort(key=lambda x: x["segment_index"], reverse=True)
        return candidates[0]["node_id"]

    def resolve_coreference(
        self, mention: str, speaker_history: list[dict]
    ) -> str | None:
        """Resolve anaphoric/deictic references using speaker turn context.
        
        DEPRECATED: Use _resolve_coreference instead.
        This method is kept for backwards compatibility.

        Args:
            mention: The anaphoric mention (e.g., "the gentleman who just spoke")
            speaker_history: Recent speaker turns for context

        Returns:
            Resolved node_id or None if unresolvable
        """
        # Delegate to the new implementation with minimal parameters
        return self._resolve_coreference(mention, "UNKNOWN", speaker_history, None)

    def _log_unresolved_mention(
        self, mention: str, session_id: str, segment_index: int,
        debate_date: str | None, context: str, mention_type: str = "standard",
        speaker_id: str | None = None
    ) -> None:
        """Log an unresolved mention for human review (BR-14).

        Args:
            mention: The raw mention that could not be resolved
            session_id: Session identifier
            segment_index: Segment number where mention occurred
            debate_date: Optional debate date
            context: Context window around the mention
            mention_type: Type of mention (e.g., "deictic", "standard")
            speaker_id: Node ID of the speaker making the mention
        """
        from datetime import datetime, timezone
        
        self.unresolved_mentions.append({
            "mention": mention,
            "session_id": session_id,
            "segment_index": segment_index,
            "debate_date": debate_date,
            "context": context,
            "mention_type": mention_type,
            "speaker_id": speaker_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save_unresolved_log(self, output_path: str) -> None:
        """Save the unresolved mentions log to a JSON file.

        Args:
            output_path: Path to save the log file
        """
        import json
        
        output = {
            "total_unresolved": len(self.unresolved_mentions),
            "mentions": self.unresolved_mentions,
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    def get_unresolved_count(self) -> int:
        """Get the count of unresolved mentions logged so far.

        Returns:
            Number of unresolved mentions
        """
        return len(self.unresolved_mentions)

    def clear_unresolved_log(self) -> None:
        """Clear the unresolved mentions log."""
        self.unresolved_mentions = []
