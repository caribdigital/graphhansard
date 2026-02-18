"""Output validation gate for session graphs.

Validates session graph quality after graph building to catch data
quality regressions immediately. Implements checks for enrichment,
name resolution, procedural edges, sentiment distribution, and
minimum graph size.

See issue #63 for specification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of a single validation check."""

    check_name: str
    status: str  # "PASS", "WARN", or "FAIL"
    message: str
    details: dict[str, Any] | None = None


class ValidationReport(BaseModel):
    """Complete validation report for a session graph."""

    session_id: str
    timestamp: str
    checks: list[ValidationResult]
    overall_status: str  # "PASS", "WARN", or "FAIL"


def validate_output(
    session_graph: dict,
    session_id: str,
    output_dir: str | Path | None = None,
) -> ValidationReport:
    """Validate session graph output quality.

    Performs 6 validation checks:
    1. Enrichment: At least 1 node has party != "Unknown"
    2. Common names: No node with common_name == node_id when node_id starts with mp_
    3. Procedural edges: At least 1 edge has is_procedural == True
    4. Sentiment distribution: Not >80% positive across all edges
    5. Node count: At least 5 nodes per session
    6. Edge count: At least 3 edges per session

    Args:
        session_graph: SessionGraph dict or object with .model_dump()
        session_id: Session identifier
        output_dir: Optional directory to save validation report

    Returns:
        ValidationReport with all check results
    """
    from datetime import datetime, timezone

    # Convert to dict if pydantic model
    if hasattr(session_graph, "model_dump"):
        graph_data = session_graph.model_dump()
    else:
        graph_data = session_graph

    checks = []

    # Check 1: Enrichment - At least 1 node has party != "Unknown"
    nodes = graph_data.get("nodes", [])
    enriched_nodes = [n for n in nodes if n.get("party") != "Unknown"]

    if enriched_nodes:
        checks.append(ValidationResult(
            check_name="enrichment",
            status="PASS",
            message=f"{len(enriched_nodes)}/{len(nodes)} nodes have party information",
            details={
                "enriched_count": len(enriched_nodes),
                "total_count": len(nodes),
            },
        ))
    else:
        checks.append(ValidationResult(
            check_name="enrichment",
            status="FAIL",
            message=f"No nodes have party information (all {len(nodes)} nodes have party='Unknown')",
            details={
                "enriched_count": 0,
                "total_count": len(nodes),
            },
        ))

    # Check 2: Common names - No node with common_name == node_id when node_id starts with mp_
    invalid_names = [
        n for n in nodes
        if n.get("node_id", "").startswith("mp_") and n.get("common_name") == n.get("node_id")
    ]

    if not invalid_names:
        checks.append(ValidationResult(
            check_name="common_names",
            status="PASS",
            message="All MP nodes have resolved common names",
            details={"unresolved_count": 0},
        ))
    else:
        checks.append(ValidationResult(
            check_name="common_names",
            status="FAIL",
            message=f"{len(invalid_names)} nodes have unresolved names (common_name == node_id)",
            details={
                "unresolved_count": len(invalid_names),
                "examples": [n.get("node_id") for n in invalid_names[:5]],
            },
        ))

    # Check 3: Procedural edges - At least 1 edge has is_procedural == True
    edges = graph_data.get("edges", [])
    procedural_edges = [e for e in edges if e.get("is_procedural") is True]

    if procedural_edges:
        checks.append(ValidationResult(
            check_name="procedural_edges",
            status="PASS",
            message=f"{len(procedural_edges)}/{len(edges)} edges are procedural",
            details={
                "procedural_count": len(procedural_edges),
                "total_count": len(edges),
            },
        ))
    elif len(edges) > 0:
        checks.append(ValidationResult(
            check_name="procedural_edges",
            status="WARN",
            message=f"No procedural edges found among {len(edges)} edges (may indicate Speaker not identified)",
            details={
                "procedural_count": 0,
                "total_count": len(edges),
            },
        ))
    else:
        checks.append(ValidationResult(
            check_name="procedural_edges",
            status="FAIL",
            message="No edges found in graph",
            details={
                "procedural_count": 0,
                "total_count": 0,
            },
        ))

    # Check 4: Sentiment distribution - Not >80% positive across all edges
    if edges:
        total_sentiment_edges = sum(
            e.get("positive_count", 0) + e.get("neutral_count", 0) + e.get("negative_count", 0)
            for e in edges
        )
        total_positive = sum(e.get("positive_count", 0) for e in edges)

        if total_sentiment_edges > 0:
            positive_pct = (total_positive / total_sentiment_edges) * 100

            if positive_pct <= 80:
                checks.append(ValidationResult(
                    check_name="sentiment_distribution",
                    status="PASS",
                    message=f"Sentiment distribution acceptable ({positive_pct:.1f}% positive)",
                    details={
                        "positive_percentage": round(positive_pct, 2),
                        "positive_count": total_positive,
                        "total_count": total_sentiment_edges,
                    },
                ))
            else:
                checks.append(ValidationResult(
                    check_name="sentiment_distribution",
                    status="WARN",
                    message=f"Sentiment may be biased ({positive_pct:.1f}% positive, threshold: 80%)",
                    details={
                        "positive_percentage": round(positive_pct, 2),
                        "positive_count": total_positive,
                        "total_count": total_sentiment_edges,
                    },
                ))
        else:
            checks.append(ValidationResult(
                check_name="sentiment_distribution",
                status="WARN",
                message="No sentiment data available",
                details={
                    "positive_percentage": 0,
                    "positive_count": 0,
                    "total_count": 0,
                },
            ))
    else:
        checks.append(ValidationResult(
            check_name="sentiment_distribution",
            status="FAIL",
            message="No edges to analyze sentiment",
            details={
                "positive_percentage": 0,
                "positive_count": 0,
                "total_count": 0,
            },
        ))

    # Check 5: Node count - At least 5 nodes per session
    node_count = len(nodes)

    if node_count >= 5:
        checks.append(ValidationResult(
            check_name="node_count",
            status="PASS",
            message=f"Session has {node_count} nodes (minimum: 5)",
            details={"node_count": node_count, "minimum": 5},
        ))
    else:
        checks.append(ValidationResult(
            check_name="node_count",
            status="FAIL",
            message=f"Session has only {node_count} nodes (minimum: 5)",
            details={"node_count": node_count, "minimum": 5},
        ))

    # Check 6: Edge count - At least 3 edges per session
    edge_count = len(edges)
    edge_word = "edge" if edge_count == 1 else "edges"

    if edge_count >= 3:
        checks.append(ValidationResult(
            check_name="edge_count",
            status="PASS",
            message=f"Session has {edge_count} {edge_word} (minimum: 3)",
            details={"edge_count": edge_count, "minimum": 3},
        ))
    else:
        checks.append(ValidationResult(
            check_name="edge_count",
            status="FAIL",
            message=f"Session has only {edge_count} {edge_word} (minimum: 3)",
            details={"edge_count": edge_count, "minimum": 3},
        ))

    # Determine overall status
    has_fail = any(c.status == "FAIL" for c in checks)
    has_warn = any(c.status == "WARN" for c in checks)

    if has_fail:
        overall_status = "FAIL"
    elif has_warn:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    # Create validation report
    report = ValidationReport(
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        checks=checks,
        overall_status=overall_status,
    )

    # Print to console
    print("\n" + "=" * 70)
    print(f"VALIDATION REPORT: {session_id}")
    print("=" * 70)

    for check in checks:
        status_symbol = {
            "PASS": "[OK]",
            "WARN": "[!!]",
            "FAIL": "[XX]",
        }.get(check.status, "[??]")

        print(f"  [{check.status}] {status_symbol} {check.check_name}: {check.message}")

    print("-" * 70)
    print(f"  OVERALL: {overall_status}")
    print("=" * 70 + "\n")

    # Save validation report if output directory provided
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_file = output_path / f"validation_{session_id}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)

        print(f"Validation report saved: {report_file}\n")

    return report
