"""Speaker Resolution — Maps diarization labels (SPEAKER_XX) to MP node IDs.

Implements heuristic-based speaker identity resolution to bridge the gap between
speaker diarization labels and actual MP identities in the Golden Record.

This addresses the issue where all edges have source_node_id as raw diarization
labels (SPEAKER_00, SPEAKER_02, etc.) instead of actual MP node IDs.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SpeakerResolution(BaseModel):
    """A single speaker identity resolution."""

    speaker_label: str = Field(description="Diarization label (e.g., SPEAKER_00)")
    resolved_node_id: str | None = Field(description="Resolved MP node_id")
    confidence: float = Field(description="Confidence score 0.0-1.0")
    method: str = Field(description="Resolution method used")
    evidence: list[str] = Field(
        default_factory=list,
        description="Supporting evidence for the resolution"
    )


class SpeakerResolver:
    """Resolves speaker diarization labels to MP node IDs using heuristics.
    
    Implements four heuristics:
    1. Chair Detection: Identifies Speaker/Deputy Speaker by procedural language
    2. Recognition Chaining: Links recognized MPs to their subsequent speech
    3. Self-Reference Detection: Identifies speakers from self-referential language
    4. Portfolio Fingerprinting: Matches topics to MP portfolios
    """

    # Patterns for chair detection
    # Both American ("recognize") and British ("recognise") spellings are
    # handled via recogni[sz]e to match Whisper transcription variation.
    # "Honorable" (American) and "Honourable" (British) are both accepted.
    CHAIR_PATTERNS = [
        re.compile(r"The\s+Chair\s+recogni[sz]es?", re.IGNORECASE),
        re.compile(r"I\s+recogni[sz]e\s+the\s+(?:Honou?rable|Hon\.?|Member)", re.IGNORECASE),
        re.compile(r"(?:Madam|Mr\.?)\s+Speaker\s+(?:yields|recogni[sz]es)", re.IGNORECASE),
        re.compile(r"The\s+(?:Member|Minister)\s+(?:has|will\s+have)\s+the\s+floor", re.IGNORECASE),
        re.compile(r"Order,?\s+order", re.IGNORECASE),
        re.compile(r"The\s+House\s+(?:will\s+(?:come\s+to\s+)?order|is\s+now\s+in\s+session)", re.IGNORECASE),
    ]

    # Patterns for recognition statements
    # Capture group is non-greedy and stops at sentence-ending punctuation
    # to avoid capturing trailing clause text (e.g. "to speak on this matter").
    RECOGNITION_PATTERNS = [
        # "The Chair recognizes the Member for [constituency]"
        re.compile(
            r"(?:The\s+Chair|I)\s+recogni[sz]es?\s+(?:the\s+)?(?:Honou?rable|Hon\.?|Member)\s+(?:for\s+)?([A-Z][A-Za-z\s,&]+?)(?:\s+(?:to|who|on|for\s+(?:his|her|their))|\.|,\s+(?:who|the)|$)",
            re.IGNORECASE
        ),
        # "The Honourable [Name] has the floor"
        re.compile(
            r"(?:The\s+)?(?:Honou?rable|Hon\.?)\s+([A-Z][A-Za-z\s\.]+)\s+(?:has|will\s+have)\s+the\s+floor",
            re.IGNORECASE
        ),
        # "I recognize the [Title]" - for ministerial/portfolio titles
        # Captures titles like "Deputy Prime Minister", "Minister of Foreign Affairs", etc.
        re.compile(
            r"(?:The\s+Chair|I)\s+recogni[sz]es?\s+(?:the\s+)?((?:Deputy\s+)?Prime\s+Minister|Minister(?:\s+of\s+[A-Z][A-Za-z\s,&]+?)?|Attorney\s+General|Leader\s+of\s+the\s+(?:Official\s+)?Opposition)(?:\s+(?:to|who|on)|\.|,|$)",
            re.IGNORECASE
        ),
    ]

    # Self-reference indicators (reserved for future enhancement)
    # TODO: Integrate with entity_extractor's is_self_reference detection
    # when full implementation is ready
    SELF_REFERENCE_INDICATORS = [
        "I", "my", "me", "myself", "we", "our", "us"
    ]

    def __init__(self, mp_registry: dict[str, dict[str, Any]] | None = None):
        """Initialize the speaker resolver.
        
        Args:
            mp_registry: Dictionary mapping node_id to MP data including:
                - common_name: MP's common name
                - constituency: MP's constituency
                - portfolios: List of portfolio dictionaries
                - special_roles: List of special roles (e.g., "Speaker of the House")
        """
        self.mp_registry = mp_registry or {}
        self._build_lookup_indices()

    def _build_lookup_indices(self):
        """Build reverse lookup indices for fast resolution."""
        self.constituency_to_mp = {}
        self.name_to_mp = {}
        self.title_to_mp = {}
        self.speaker_node_id = None
        self.deputy_speaker_node_id = None

        for node_id, mp_data in self.mp_registry.items():
            # Constituency index
            constituency = mp_data.get("constituency")
            if constituency:
                self.constituency_to_mp[constituency.lower()] = node_id

            # Name index
            common_name = mp_data.get("common_name", "")
            if common_name:
                self.name_to_mp[common_name.lower()] = node_id

            # Portfolio/title index - map current portfolio titles to MPs
            portfolios = mp_data.get("portfolios", [])
            for portfolio in portfolios:
                # Only index current portfolios (end_date is None)
                if portfolio.get("end_date") is None:
                    title = portfolio.get("title", "").lower()
                    short_title = portfolio.get("short_title", "").lower()

                    if title:
                        self.title_to_mp[title] = node_id
                    if short_title and short_title != title:
                        self.title_to_mp[short_title] = node_id

            # Speaker identification
            special_roles = mp_data.get("special_roles", [])
            if "Speaker of the House" in special_roles:
                self.speaker_node_id = node_id
            elif "Deputy Speaker" in special_roles:
                self.deputy_speaker_node_id = node_id

    def resolve_speakers(
        self,
        transcript: dict,
        confidence_threshold: float = 0.5
    ) -> dict[str, SpeakerResolution]:
        """Resolve all SPEAKER_XX labels in a transcript to MP node IDs.
        
        Args:
            transcript: DiarizedTranscript dict with segments
            confidence_threshold: Minimum confidence to accept a resolution
            
        Returns:
            Dictionary mapping speaker_label -> SpeakerResolution
        """
        segments = transcript.get("segments", [])
        resolutions = {}

        # Collect all unique speaker labels
        speaker_labels = set()
        for segment in segments:
            label = segment.get("speaker_label", "")
            if label.startswith("SPEAKER_"):
                speaker_labels.add(label)

        logger.info(f"Resolving {len(speaker_labels)} unique speaker labels")

        # Apply heuristics to identify speakers
        # Heuristic 1: Chair Detection
        chair_candidates = self._detect_chair_speakers(segments)

        # Heuristic 2: Recognition Chaining
        recognition_resolutions = self._resolve_by_recognition(segments)

        # Heuristic 3: Self-Reference Detection
        self_reference_resolutions = self._resolve_by_self_reference(segments)

        # Heuristic 4: Portfolio Fingerprinting (basic implementation)
        portfolio_resolutions = self._resolve_by_portfolio(segments)

        # Detect conflicts before merging
        self._log_resolution_conflicts(
            portfolio_resolutions,
            self_reference_resolutions,
            recognition_resolutions,
            chair_candidates
        )

        # Merge resolutions with confidence-based prioritization
        all_resolutions = {
            **portfolio_resolutions,
            **self_reference_resolutions,
            **recognition_resolutions,
            **chair_candidates,
        }

        # Filter by confidence threshold
        for speaker_label, resolution in all_resolutions.items():
            if resolution.confidence >= confidence_threshold:
                resolutions[speaker_label] = resolution
                logger.info(
                    f"Resolved {speaker_label} -> {resolution.resolved_node_id} "
                    f"(confidence: {resolution.confidence:.2f}, method: {resolution.method})"
                )
            else:
                logger.debug(
                    f"Low confidence resolution for {speaker_label}: "
                    f"{resolution.resolved_node_id} ({resolution.confidence:.2f})"
                )

        return resolutions

    def _detect_chair_speakers(
        self,
        segments: list[dict]
    ) -> dict[str, SpeakerResolution]:
        """Detect Speaker/Deputy Speaker by procedural language patterns.
        
        Returns:
            Dictionary mapping speaker_label -> SpeakerResolution
        """
        speaker_chair_scores = defaultdict(int)
        speaker_evidence = defaultdict(list)

        for segment in segments:
            text = segment.get("text", "")
            speaker_label = segment.get("speaker_label", "")

            if not speaker_label.startswith("SPEAKER_"):
                continue

            # Check for chair patterns
            for pattern in self.CHAIR_PATTERNS:
                matches = pattern.findall(text)
                if matches:
                    speaker_chair_scores[speaker_label] += len(matches)
                    speaker_evidence[speaker_label].append(
                        f"Chair pattern: '{pattern.pattern[:50]}...' matched {len(matches)} times"
                    )

        # Identify the speaker with highest chair score
        resolutions = {}
        if speaker_chair_scores:
            # Sort by score
            sorted_speakers = sorted(
                speaker_chair_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )

            # The speaker with most chair language is likely the Speaker
            primary_chair, primary_score = sorted_speakers[0]

            # Determine if this is Speaker or Deputy Speaker
            # Simple heuristic: highest score is Speaker
            if self.speaker_node_id:
                confidence = min(0.9, 0.6 + (primary_score / 10.0))
                resolutions[primary_chair] = SpeakerResolution(
                    speaker_label=primary_chair,
                    resolved_node_id=self.speaker_node_id,
                    confidence=confidence,
                    method="chair_detection",
                    evidence=speaker_evidence[primary_chair][:5]  # Limit evidence
                )

            # If there's a second speaker with significant chair language,
            # they might be Deputy Speaker
            if len(sorted_speakers) > 1 and self.deputy_speaker_node_id:
                secondary_chair, secondary_score = sorted_speakers[1]
                if secondary_score >= 2:  # At least 2 chair patterns
                    confidence = min(0.8, 0.5 + (secondary_score / 15.0))
                    resolutions[secondary_chair] = SpeakerResolution(
                        speaker_label=secondary_chair,
                        resolved_node_id=self.deputy_speaker_node_id,
                        confidence=confidence,
                        method="chair_detection",
                        evidence=speaker_evidence[secondary_chair][:5]
                    )

        return resolutions

    def _resolve_by_recognition(
        self,
        segments: list[dict]
    ) -> dict[str, SpeakerResolution]:
        """Resolve speakers by recognition-to-speech chaining.
        
        When the Chair recognizes someone, the next speaker is likely that person.
        Looks ahead up to 3 segments to skip brief interjections and Chair's own
        segments, with declining confidence for each distance.
        
        Returns:
            Dictionary mapping speaker_label -> SpeakerResolution
        """
        resolutions = {}

        for i, segment in enumerate(segments):
            text = segment.get("text", "")
            chair_speaker = segment.get("speaker_label", "")

            # Look for recognition patterns
            for pattern in self.RECOGNITION_PATTERNS:
                match = pattern.search(text)
                if match:
                    # Extract the recognized entity (constituency or name)
                    recognized_text = match.group(1).strip()

                    # Try to resolve to an MP
                    resolved_node_id = self._resolve_recognized_entity(recognized_text)

                    if resolved_node_id:
                        # Look ahead up to 3 segments (i+1, i+2, i+3)
                        # with declining confidence: 0.75, 0.65, 0.55
                        confidences = [0.75, 0.65, 0.55]

                        for offset in range(1, 4):
                            if i + offset >= len(segments):
                                break

                            next_segment = segments[i + offset]
                            next_speaker = next_segment.get("speaker_label", "")
                            next_text = next_segment.get("text", "")

                            # Skip if not a valid speaker label
                            if not next_speaker.startswith("SPEAKER_"):
                                continue

                            # Skip if it's the Chair speaking again
                            if next_speaker == chair_speaker:
                                continue

                            # Check if this is a substantial speech (>10 words)
                            word_count = len(next_text.split())
                            if word_count > 10:
                                # Found a substantial speech from a different speaker
                                resolutions[next_speaker] = SpeakerResolution(
                                    speaker_label=next_speaker,
                                    resolved_node_id=resolved_node_id,
                                    confidence=confidences[offset - 1],
                                    method="recognition_chaining",
                                    evidence=[
                                        f"Recognized as '{recognized_text}' in segment {i}",
                                        f"Began speaking in segment {i + offset} with {word_count} words"
                                    ]
                                )
                                # Stop looking after finding the first substantial speech
                                break

        return resolutions

    def _resolve_recognized_entity(self, text: str) -> str | None:
        """Resolve a recognized entity (name, constituency, or title) to node_id.
        
        Args:
            text: The recognized text (e.g., "Cat Island", "Fred Mitchell", "Deputy Prime Minister")
            
        Returns:
            MP node_id if resolved, None otherwise
        """
        text_lower = text.lower().strip()

        # Try exact title match first (for ministerial titles)
        if text_lower in self.title_to_mp:
            return self.title_to_mp[text_lower]

        # Try constituency match
        if text_lower in self.constituency_to_mp:
            return self.constituency_to_mp[text_lower]

        # Try name match
        if text_lower in self.name_to_mp:
            return self.name_to_mp[text_lower]

        # Try partial constituency match — require the query to be a
        # meaningful substring (>=5 chars) to avoid false positives like
        # "Nassau" matching "nassau village".
        if len(text_lower) >= 5:
            for constituency, node_id in self.constituency_to_mp.items():
                if text_lower in constituency or constituency in text_lower:
                    return node_id

        # Try partial name match (same minimum length guard)
        if len(text_lower) >= 5:
            for name, node_id in self.name_to_mp.items():
                if text_lower in name or name in text_lower:
                    return node_id

        return None

    def _resolve_by_self_reference(
        self,
        segments: list[dict]
    ) -> dict[str, SpeakerResolution]:
        """Resolve speakers using self-reference patterns.
        
        This is a simplified version - full implementation would integrate
        with entity_extractor's is_self_reference detection.
        
        Returns:
            Dictionary mapping speaker_label -> SpeakerResolution
        """
        # This heuristic requires deeper integration with entity extraction
        # For now, return empty dict - can be enhanced in future iterations
        return {}

    def _resolve_by_portfolio(
        self,
        segments: list[dict]
    ) -> dict[str, SpeakerResolution]:
        """Resolve speakers by matching discussion topics to MP portfolios.
        
        Expanded implementation covering 15+ portfolio categories with
        bigram/trigram keywords for precise matching.
        
        Returns:
            Dictionary mapping speaker_label -> SpeakerResolution
        """
        # Build portfolio keyword index with expanded coverage
        portfolio_keywords = defaultdict(list)
        for node_id, mp_data in self.mp_registry.items():
            portfolios = mp_data.get("portfolios", [])
            for portfolio in portfolios:
                title = portfolio.get("title", "").lower()
                
                # Finance (existing)
                if "finance" in title:
                    portfolio_keywords[node_id].extend([
                        "budget", "finance", "financial", "tax", "taxation", "revenue",
                        "fiscal", "treasury", "economy", "economic"
                    ])
                
                # Tourism (existing)
                if "tourism" in title:
                    portfolio_keywords[node_id].extend([
                        "tourism", "tourist", "tourists", "visitors", "hotels",
                        "resorts", "attractions", "travel"
                    ])
                
                # Foreign Affairs (existing)
                if "foreign affairs" in title or "foreign" in title:
                    portfolio_keywords[node_id].extend([
                        "foreign", "international", "diplomatic", "diplomacy",
                        "embassy", "ambassador", "treaty", "bilateral"
                    ])
                
                # Health (existing)
                if "health" in title:
                    portfolio_keywords[node_id].extend([
                        "health", "healthcare", "hospital", "hospitals", "medical",
                        "doctor", "doctors", "nurses", "clinic", "clinics",
                        "wellness", "medicine", "patient", "patients"
                    ])
                
                # Education (existing)
                if "education" in title:
                    portfolio_keywords[node_id].extend([
                        "education", "school", "schools", "students", "teachers",
                        "university", "college", "curriculum", "training",
                        "vocational", "technical"
                    ])

                # Transport & Aviation (new)
                if "transport" in title or "aviation" in title:
                    portfolio_keywords[node_id].extend([
                        "transport", "transportation", "aviation", "airport",
                        "airports", "airline", "airlines", "flight", "flights",
                        "roads", "highways", "infrastructure", "traffic"
                    ])

                # Agriculture & Marine Resources (new)
                if "agriculture" in title or "marine" in title:
                    portfolio_keywords[node_id].extend([
                        "agriculture", "agricultural", "farming", "farmers",
                        "crops", "livestock", "marine", "fisheries", "fishing",
                        "aquaculture", "seafood", "maritime"
                    ])

                # Works & Utilities (new)
                if "works" in title or "utilities" in title:
                    portfolio_keywords[node_id].extend([
                        "works", "utilities", "infrastructure", "water",
                        "sewerage", "electricity", "power", "construction",
                        "public works", "maintenance"
                    ])

                # Housing (new)
                if "housing" in title:
                    portfolio_keywords[node_id].extend([
                        "housing", "homes", "affordable housing", "residential",
                        "apartments", "mortgage", "mortgages", "property",
                        "urban renewal", "subdivision", "subdivisions"
                    ])

                # Immigration (new)
                if "immigration" in title:
                    portfolio_keywords[node_id].extend([
                        "immigration", "immigrants", "visa", "visas",
                        "work permit", "work permits", "citizenship",
                        "deportation", "border", "migration"
                    ])

                # National Security (new) - bigram for precision
                if "national security" in title or "security" in title:
                    portfolio_keywords[node_id].extend([
                        "national security", "security", "police", "crime",
                        "law enforcement", "prison", "prisons", "defense",
                        "defence", "correctional", "officer", "officers"
                    ])

                # Youth, Sports & Culture (new)
                if "youth" in title or "sports" in title or "culture" in title:
                    portfolio_keywords[node_id].extend([
                        "youth", "young people", "sports", "athletics",
                        "athletes", "culture", "cultural", "arts",
                        "recreation", "junkanoo", "festivals"
                    ])

                # Labour (new)
                if "labour" in title or "labor" in title:
                    portfolio_keywords[node_id].extend([
                        "labour", "labor", "workers", "employment",
                        "unemployment", "jobs", "workplace", "unions",
                        "trade unions", "minimum wage", "public service"
                    ])

                # Social Services (new)
                if "social services" in title or "social" in title:
                    portfolio_keywords[node_id].extend([
                        "social services", "social", "welfare", "assistance",
                        "poverty", "elderly", "disabled", "vulnerable",
                        "community", "family", "children"
                    ])

                # Environment (new)
                if "environment" in title:
                    portfolio_keywords[node_id].extend([
                        "environment", "environmental", "climate", "pollution",
                        "conservation", "recycling", "waste", "renewable",
                        "green", "sustainability", "sustainable"
                    ])

                # Energy (new)
                if "energy" in title:
                    portfolio_keywords[node_id].extend([
                        "energy", "electricity", "power", "renewable energy",
                        "solar", "fuel", "gas", "oil", "petroleum"
                    ])

                # Grand Bahama (new)
                if "grand bahama" in title:
                    portfolio_keywords[node_id].extend([
                        "grand bahama", "freeport", "lucaya", "gb"
                    ])

                # Disaster Risk Management (new)
                if "disaster" in title:
                    portfolio_keywords[node_id].extend([
                        "disaster", "emergency", "hurricane", "hurricanes",
                        "relief", "recovery", "nema", "preparedness"
                    ])

                # Investments (new)
                if "investments" in title or "investment" in title:
                    portfolio_keywords[node_id].extend([
                        "investment", "investments", "investor", "investors",
                        "fdi", "foreign investment", "business"
                    ])

        # Count portfolio keyword mentions per speaker
        speaker_portfolio_scores = defaultdict(lambda: defaultdict(int))

        for segment in segments:
            text = segment.get("text", "").lower()
            speaker_label = segment.get("speaker_label", "")

            if not speaker_label.startswith("SPEAKER_"):
                continue

            for node_id, keywords in portfolio_keywords.items():
                for keyword in keywords:
                    # Use word boundary matching for single words to avoid partial matches
                    # For multi-word keywords (bigrams/trigrams), use simple count
                    if " " in keyword:
                        # Multi-word keyword - use simple count
                        count = text.count(keyword)
                    else:
                        # Single word - use word boundary matching
                        # Count occurrences as whole words only
                        import re
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        count = len(re.findall(pattern, text))
                    
                    if count > 0:
                        speaker_portfolio_scores[speaker_label][node_id] += count

        # Create resolutions for speakers with strong portfolio signals
        resolutions = {}
        for speaker_label, portfolio_scores in speaker_portfolio_scores.items():
            if portfolio_scores:
                # Get the MP with highest portfolio match
                best_mp = max(portfolio_scores.items(), key=lambda x: x[1])
                node_id, score = best_mp

                # Only create resolution if score is significant
                if score >= 3:  # At least 3 keyword matches
                    confidence = min(0.6, 0.3 + (score / 20.0))
                    resolutions[speaker_label] = SpeakerResolution(
                        speaker_label=speaker_label,
                        resolved_node_id=node_id,
                        confidence=confidence,
                        method="portfolio_fingerprinting",
                        evidence=[f"Portfolio keywords matched {score} times"]
                    )

        return resolutions

    def _log_resolution_conflicts(
        self,
        portfolio_resolutions: dict[str, SpeakerResolution],
        self_reference_resolutions: dict[str, SpeakerResolution],
        recognition_resolutions: dict[str, SpeakerResolution],
        chair_candidates: dict[str, SpeakerResolution]
    ) -> None:
        """Log conflicts when different heuristics resolve the same speaker to different MPs.

        Args:
            portfolio_resolutions: Resolutions from portfolio fingerprinting
            self_reference_resolutions: Resolutions from self-reference detection
            recognition_resolutions: Resolutions from recognition chaining
            chair_candidates: Resolutions from chair detection
        """
        # Group all resolutions by speaker_label
        # Priority order: chair > recognition > self_ref > portfolio
        heuristics = [
            ("portfolio_fingerprinting", portfolio_resolutions),
            ("self_reference", self_reference_resolutions),
            ("recognition_chaining", recognition_resolutions),
            ("chair_detection", chair_candidates),
        ]

        # Collect all speakers that appear in multiple heuristics
        speaker_to_resolutions: dict[str, list] = defaultdict(list)
        for method_name, resolutions in heuristics:
            for speaker_label, resolution in resolutions.items():
                speaker_to_resolutions[speaker_label].append((method_name, resolution))

        # Log conflicts for speakers with multiple resolutions
        for speaker_label, resolution_list in speaker_to_resolutions.items():
            if len(resolution_list) > 1:
                # Check if they resolve to different node_ids
                resolved_ids = set(res.resolved_node_id for _, res in resolution_list)
                if len(resolved_ids) > 1:
                    # We have a conflict - different heuristics disagree
                    logger.warning(
                        f"Conflict for {speaker_label}: multiple heuristics resolved to different MPs"
                    )
                    for method_name, resolution in resolution_list:
                        logger.warning(
                            f"  {method_name}: {resolution.resolved_node_id} "
                            f"(confidence: {resolution.confidence:.2f})"
                        )
                    # Indicate which one will win based on priority
                    winner = resolution_list[-1]  # Last one in priority order wins
                    logger.warning(
                        f"  Resolution: {winner[1].resolved_node_id} from {winner[0]} "
                        f"(priority: chair > recognition > self_ref > portfolio)"
                    )

    def apply_resolutions(
        self,
        transcript: dict,
        resolutions: dict[str, SpeakerResolution]
    ) -> dict:
        """Apply speaker resolutions to transcript segments.
        
        Updates speaker_node_id field for resolved speakers.
        
        Args:
            transcript: DiarizedTranscript dict
            resolutions: Dictionary of speaker resolutions
            
        Returns:
            Updated transcript dict
        """
        segments = transcript.get("segments", [])

        for segment in segments:
            speaker_label = segment.get("speaker_label", "")
            if speaker_label in resolutions:
                resolution = resolutions[speaker_label]
                segment["speaker_node_id"] = resolution.resolved_node_id

        return transcript


def load_mp_registry_from_golden_record(golden_record_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load MP registry from golden record JSON file.
    
    Args:
        golden_record_path: Path to mps.json file
        
    Returns:
        Dictionary mapping node_id to MP data
    """
    import json

    with open(golden_record_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    registry = {}
    for mp in data.get("mps", []):
        registry[mp["node_id"]] = {
            "common_name": mp.get("common_name", ""),
            "constituency": mp.get("constituency"),
            "portfolios": mp.get("portfolios", []),
            "special_roles": mp.get("special_roles", []),
        }

    return registry
