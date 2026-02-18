"""Tests for GR-7: Procedural Edge Tagging.

Validates that edges involving Speaker/Chair control nodes are properly
tagged as procedural with appropriate semantic types.
"""

import pytest

from graphhansard.brain.graph_builder import (
    EdgeSemanticType,
    GraphBuilder,
)


class TestProceduralEdgeTagging:
    """Test procedural edge identification and tagging (GR-7)."""

    def test_control_node_extraction(self):
        """Extract control nodes from mp_registry."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_deveaux_patricia": {
                "common_name": "Patricia Deveaux",
                "party": "PLP",
                "node_type": "control",
            },
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
            "mp_cooper_chester": {
                "common_name": "Chester Cooper",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        control_nodes = builder._extract_control_nodes(mp_registry)
        
        assert "mp_deveaux_patricia" in control_nodes
        assert "mp_davis_brave" not in control_nodes
        assert "mp_cooper_chester" not in control_nodes
        assert len(control_nodes) == 1

    def test_edge_from_control_node_is_procedural(self):
        """Edges from Speaker to MP are tagged as procedural."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_deveaux_patricia": {
                "common_name": "Patricia Deveaux",
                "party": "PLP",
                "node_type": "control",
            },
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        mentions = [
            {
                "source_node_id": "mp_deveaux_patricia",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Chair recognizes the Prime Minister.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_procedural",
            date="2024-01-15",
            mp_registry=mp_registry,
        )
        
        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        
        assert edge.is_procedural is True
        assert edge.semantic_type == EdgeSemanticType.RECOGNIZING

    def test_edge_to_control_node_is_procedural(self):
        """Edges to Speaker are tagged as procedural."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_deveaux_patricia": {
                "common_name": "Patricia Deveaux",
                "party": "PLP",
                "node_type": "control",
            },
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        mentions = [
            {
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_deveaux_patricia",
                "context_window": "I thank the Speaker for allowing me to speak.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_procedural_to",
            date="2024-01-15",
            mp_registry=mp_registry,
        )
        
        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        
        assert edge.is_procedural is True
        # MP addressing Speaker is still a mention
        assert edge.semantic_type == EdgeSemanticType.MENTION

    def test_edge_between_debaters_is_not_procedural(self):
        """Edges between regular MPs are not procedural."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
            "mp_cooper_chester": {
                "common_name": "Chester Cooper",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        mentions = [
            {
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_cooper_chester",
                "context_window": "The Deputy Prime Minister has done excellent work.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_political",
            date="2024-01-15",
            mp_registry=mp_registry,
        )
        
        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        
        assert edge.is_procedural is False
        assert edge.semantic_type == EdgeSemanticType.MENTION

    def test_context_based_fallback_for_speaker_xx(self):
        """Unresolved SPEAKER_XX nodes with recognition pattern are procedural."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        mentions = [
            {
                "source_node_id": "SPEAKER_00",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Chair recognizes the Honourable Prime Minister.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_speaker_fallback",
            date="2024-01-15",
            mp_registry=mp_registry,
        )
        
        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        
        assert edge.is_procedural is True
        assert edge.semantic_type == EdgeSemanticType.RECOGNIZING

    def test_speaker_xx_without_recognition_pattern(self):
        """SPEAKER_XX without recognition pattern is not procedural."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        mentions = [
            {
                "source_node_id": "SPEAKER_00",
                "target_node_id": "mp_davis_brave",
                "context_window": "Some unrelated comment about the Prime Minister.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_speaker_no_pattern",
            date="2024-01-15",
            mp_registry=mp_registry,
        )
        
        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        
        assert edge.is_procedural is False
        assert edge.semantic_type == EdgeSemanticType.MENTION

    def test_political_edges_filter(self):
        """SessionGraph.political_edges() excludes procedural edges."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_deveaux_patricia": {
                "common_name": "Patricia Deveaux",
                "party": "PLP",
                "node_type": "control",
            },
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
            "mp_cooper_chester": {
                "common_name": "Chester Cooper",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        mentions = [
            # Procedural edge
            {
                "source_node_id": "mp_deveaux_patricia",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Chair recognizes the Prime Minister.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            },
            # Political edge
            {
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_cooper_chester",
                "context_window": "The Deputy PM has done excellent work.",
                "timestamp_start": 5.0,
                "timestamp_end": 10.0,
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_filter",
            date="2024-01-15",
            mp_registry=mp_registry,
        )
        
        assert len(session_graph.edges) == 2
        
        political = session_graph.political_edges()
        assert len(political) == 1
        assert political[0].source_node_id == "mp_davis_brave"
        assert political[0].target_node_id == "mp_cooper_chester"
        
        procedural = session_graph.procedural_edges()
        assert len(procedural) == 1
        assert procedural[0].source_node_id == "mp_deveaux_patricia"
        assert procedural[0].target_node_id == "mp_davis_brave"

    def test_multiple_control_nodes(self):
        """Multiple control nodes (Speaker and Deputy Speaker) are identified."""
        builder = GraphBuilder()

        mp_registry = {
            "mp_deveaux_patricia": {
                "common_name": "Patricia Deveaux",
                "party": "PLP",
                "node_type": "control",
            },
            "mp_bonaby_mckell": {
                "common_name": "McKell Bonaby",
                "party": "PLP",
                "node_type": "debater",
                "special_roles": ["Deputy Speaker"],
            },
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }

        control_nodes = builder._extract_control_nodes(mp_registry)

        assert "mp_deveaux_patricia" in control_nodes
        assert "mp_bonaby_mckell" in control_nodes
        assert "mp_davis_brave" not in control_nodes
        assert len(control_nodes) == 2

    def test_no_mp_registry_defaults_to_no_control_nodes(self):
        """Without mp_registry, no nodes are marked as control."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_deveaux_patricia",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Chair recognizes the Prime Minister.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_no_registry",
            date="2024-01-15",
            mp_registry=None,
        )
        
        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        
        # Without registry, cannot identify control nodes
        assert edge.is_procedural is False

    def test_recognition_pattern_variations(self):
        """Test various forms of recognition patterns."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }
        
        test_cases = [
            "The Chair recognizes the Prime Minister",
            "The Speaker recognises the Honourable Member",
            "Chair recognizes the Member for Cat Island",
            "Speaker recognises the Opposition Leader",
        ]
        
        for i, context in enumerate(test_cases):
            mentions = [
                {
                    "source_node_id": "SPEAKER_00",
                    "target_node_id": "mp_davis_brave",
                    "context_window": context,
                    "timestamp_start": 0.0,
                    "timestamp_end": 5.0,
                }
            ]
            
            session_graph = builder.build_session_graph(
                mentions=mentions,
                session_id=f"test_pattern_{i}",
                date="2024-01-15",
                mp_registry=mp_registry,
            )
            
            assert len(session_graph.edges) == 1
            edge = session_graph.edges[0]
            
            assert edge.is_procedural is True, f"Failed for: {context}"
            assert edge.semantic_type == EdgeSemanticType.RECOGNIZING

    def test_deputy_speaker_via_special_roles(self):
        """Deputy Speaker detected via special_roles even with node_type=debater."""
        builder = GraphBuilder()

        mp_registry = {
            "mp_bonaby_mckell": {
                "common_name": "McKell Bonaby",
                "party": "PLP",
                "node_type": "debater",
                "special_roles": ["Deputy Speaker", "Executive Chairman, Straw Market Authority"],
            },
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }

        mentions = [
            {
                "source_node_id": "mp_bonaby_mckell",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Chair recognizes the Prime Minister.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]

        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_deputy",
            date="2024-01-15",
            mp_registry=mp_registry,
        )

        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        assert edge.is_procedural is True
        assert edge.semantic_type == EdgeSemanticType.RECOGNIZING

    def test_mixed_contexts_not_tagged_procedural(self):
        """Edge with mixed political and procedural contexts stays political."""
        builder = GraphBuilder()

        mp_registry = {
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }

        mentions = [
            {
                "source_node_id": "SPEAKER_04",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Prime Minister was wrong about this.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            },
            {
                "source_node_id": "SPEAKER_04",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Chair recognizes the Prime Minister.",
                "timestamp_start": 10.0,
                "timestamp_end": 15.0,
            },
        ]

        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_mixed",
            date="2024-01-15",
            mp_registry=mp_registry,
        )

        assert len(session_graph.edges) == 1
        edge = session_graph.edges[0]
        # Mixed contexts: not all match recognition pattern, stays political
        assert edge.is_procedural is False
        assert edge.semantic_type == EdgeSemanticType.MENTION

    def test_cumulative_graph_promotes_procedural(self):
        """Cumulative graph uses OR-semantics: procedural wins regardless of order."""
        builder = GraphBuilder()

        mp_registry = {
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }

        # Session 1: political mention
        mentions1 = [
            {
                "source_node_id": "SPEAKER_00",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Prime Minister was wrong.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        sg1 = builder.build_session_graph(mentions1, "s1", "2026-01-01", mp_registry)
        assert sg1.edges[0].is_procedural is False

        # Session 2: procedural mention
        mentions2 = [
            {
                "source_node_id": "SPEAKER_00",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Chair recognizes the Prime Minister.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        sg2 = builder.build_session_graph(mentions2, "s2", "2026-01-02", mp_registry)
        assert sg2.edges[0].is_procedural is True

        # Non-procedural first: should still promote to procedural
        cumul = builder.build_cumulative_graph(
            [sg1, sg2], "cumul", ("2026-01-01", "2026-01-02"), mp_registry,
        )
        assert len(cumul.edges) == 1
        assert cumul.edges[0].is_procedural is True
        assert cumul.edges[0].semantic_type == EdgeSemanticType.RECOGNIZING

        # Procedural first: also procedural
        cumul2 = builder.build_cumulative_graph(
            [sg2, sg1], "cumul2", ("2026-01-01", "2026-01-02"), mp_registry,
        )
        assert len(cumul2.edges) == 1
        assert cumul2.edges[0].is_procedural is True

    def test_cumulative_graph_non_procedural_stays_non_procedural(self):
        """Cumulative graph with all-political sessions stays non-procedural."""
        builder = GraphBuilder()

        mp_registry = {
            "mp_davis_brave": {
                "common_name": "Brave Davis",
                "party": "PLP",
                "node_type": "debater",
            },
        }

        mentions1 = [
            {
                "source_node_id": "SPEAKER_04",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Prime Minister was wrong.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        sg1 = builder.build_session_graph(mentions1, "s1", "2026-01-01", mp_registry)

        mentions2 = [
            {
                "source_node_id": "SPEAKER_04",
                "target_node_id": "mp_davis_brave",
                "context_window": "The PM should resign.",
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
            }
        ]
        sg2 = builder.build_session_graph(mentions2, "s2", "2026-01-02", mp_registry)

        cumul = builder.build_cumulative_graph(
            [sg1, sg2], "cumul", ("2026-01-01", "2026-01-02"), mp_registry,
        )
        assert len(cumul.edges) == 1
        assert cumul.edges[0].is_procedural is False
        assert cumul.edges[0].semantic_type == EdgeSemanticType.MENTION
