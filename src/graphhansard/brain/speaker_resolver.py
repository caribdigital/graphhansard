"""Speaker Resolution — Maps diarization labels (SPEAKER_XX) to MP node IDs.

Implements heuristic-based speaker identity resolution to bridge the gap between
speaker diarization labels and actual MP identities in the Golden Record.

This addresses the issue where all edges have source_node_id as raw diarization
labels (SPEAKER_00, SPEAKER_02, etc.) instead of actual MP node IDs.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
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
    CHAIR_PATTERNS = [
        re.compile(r"The\s+Chair\s+recognizes?", re.IGNORECASE),
        re.compile(r"I\s+recognize\s+the\s+(?:Honourable|Hon\.?|Member)", re.IGNORECASE),
        re.compile(r"(?:Madam|Mr\.?)\s+Speaker\s+(?:yields|recognizes)", re.IGNORECASE),
        re.compile(r"The\s+(?:Member|Minister)\s+(?:has|will\s+have)\s+the\s+floor", re.IGNORECASE),
        re.compile(r"Order,?\s+order", re.IGNORECASE),
        re.compile(r"The\s+House\s+(?:will\s+(?:come\s+to\s+)?order|is\s+now\s+in\s+session)", re.IGNORECASE),
    ]
    
    # Patterns for recognition statements
    RECOGNITION_PATTERNS = [
        # "The Chair recognizes the Member for [constituency]"
        re.compile(
            r"(?:The\s+Chair|I)\s+recognizes?\s+(?:the\s+)?(?:Honourable|Hon\.?|Member)\s+(?:for\s+)?([A-Z][A-Za-z\s,&]+)",
            re.IGNORECASE
        ),
        # "The Honourable [Name] has the floor"
        re.compile(
            r"(?:The\s+)?(?:Honourable|Hon\.?)\s+([A-Z][A-Za-z\s\.]+)\s+(?:has|will\s+have)\s+the\s+floor",
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
        
        Returns:
            Dictionary mapping speaker_label -> SpeakerResolution
        """
        resolutions = {}
        
        for i, segment in enumerate(segments):
            text = segment.get("text", "")
            
            # Look for recognition patterns
            for pattern in self.RECOGNITION_PATTERNS:
                match = pattern.search(text)
                if match:
                    # Extract the recognized entity (constituency or name)
                    recognized_text = match.group(1).strip()
                    
                    # Try to resolve to an MP
                    resolved_node_id = self._resolve_recognized_entity(recognized_text)
                    
                    if resolved_node_id and i + 1 < len(segments):
                        # The next speaker is likely this MP
                        next_segment = segments[i + 1]
                        next_speaker = next_segment.get("speaker_label", "")
                        
                        if next_speaker.startswith("SPEAKER_"):
                            # Check if this is a substantial speech (not just acknowledgment)
                            next_text = next_segment.get("text", "")
                            if len(next_text.split()) > 10:  # At least 10 words
                                resolutions[next_speaker] = SpeakerResolution(
                                    speaker_label=next_speaker,
                                    resolved_node_id=resolved_node_id,
                                    confidence=0.75,
                                    method="recognition_chaining",
                                    evidence=[
                                        f"Recognized as '{recognized_text}' in segment {i}",
                                        f"Began speaking in next segment with {len(next_text.split())} words"
                                    ]
                                )
        
        return resolutions
    
    def _resolve_recognized_entity(self, text: str) -> str | None:
        """Resolve a recognized entity (name or constituency) to node_id.
        
        Args:
            text: The recognized text (e.g., "Cat Island" or "Fred Mitchell")
            
        Returns:
            MP node_id if resolved, None otherwise
        """
        text_lower = text.lower().strip()
        
        # Try constituency match
        if text_lower in self.constituency_to_mp:
            return self.constituency_to_mp[text_lower]
        
        # Try name match
        if text_lower in self.name_to_mp:
            return self.name_to_mp[text_lower]
        
        # Try partial constituency match
        for constituency, node_id in self.constituency_to_mp.items():
            if text_lower in constituency or constituency in text_lower:
                return node_id
        
        # Try partial name match
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
        
        This is a basic implementation that looks for portfolio keywords.
        
        Returns:
            Dictionary mapping speaker_label -> SpeakerResolution
        """
        # Build portfolio keyword index
        portfolio_keywords = defaultdict(list)
        for node_id, mp_data in self.mp_registry.items():
            portfolios = mp_data.get("portfolios", [])
            for portfolio in portfolios:
                title = portfolio.get("title", "").lower()
                # Extract key topics from portfolio title
                if "finance" in title:
                    portfolio_keywords[node_id].extend(["budget", "finance", "tax", "revenue"])
                if "tourism" in title:
                    portfolio_keywords[node_id].extend(["tourism", "tourist", "visitors"])
                if "foreign affairs" in title:
                    portfolio_keywords[node_id].extend(["foreign", "international", "diplomatic"])
                if "health" in title:
                    portfolio_keywords[node_id].extend(["health", "hospital", "medical"])
                if "education" in title:
                    portfolio_keywords[node_id].extend(["education", "school", "students"])
        
        # Count portfolio keyword mentions per speaker
        speaker_portfolio_scores = defaultdict(lambda: defaultdict(int))
        
        for segment in segments:
            text = segment.get("text", "").lower()
            speaker_label = segment.get("speaker_label", "")
            
            if not speaker_label.startswith("SPEAKER_"):
                continue
            
            for node_id, keywords in portfolio_keywords.items():
                for keyword in keywords:
                    count = text.count(keyword)
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
