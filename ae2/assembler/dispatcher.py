"""
Unified assembler dispatcher.

This module coordinates the three assemblers (definition, concept, playbook)
and enforces timeouts and determinism for the unified router system.
"""

import time
from typing import Dict, Any
from ..router.router import RouteDecision
from .definition import assemble_definition
from .concept import assemble_concept
from .playbook import assemble_playbook


def assemble(
    decision: RouteDecision, query: str, params: Dict[str, Any], stores: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Assemble response based on routing decision.

    Args:
        decision: RouteDecision from router
        query: Original user query
        params: Additional parameters (vendor, iface, etc.)
        stores: Dictionary containing IndexStore and ConceptStore

    Returns:
        Dictionary with assembled response and metadata
    """
    start_time = time.time()

    # Get timeout from environment or use default
    import os

    timeout_ms = int(os.getenv("ASSEMBLER_TIMEOUT_MS", "150"))
    _ = timeout_ms / 1000.0  # timeout_seconds not used in current implementation

    # Record metrics if enabled
    metrics_enabled = os.getenv("AE_ENABLE_METRICS", "1").lower() in (
        "1",
        "true",
        "yes",
    )
    if metrics_enabled:
        try:
            from ae2.obs.metrics import record_query_latency
        except ImportError:
            record_query_latency = None
    else:
        record_query_latency = None

    try:
        if decision.intent == "DEFINE":
            result = assemble_definition(
                target_rfc=decision.target,
                query=query,
                store=stores["index_store"],
                mode=decision.mode_used,
            )

            return {
                "intent": "DEFINE",
                "route": {
                    "target": decision.target,
                    "evidence": {
                        "matched_terms": decision.matches,
                        "confidence": decision.confidence,
                        "notes": decision.notes,
                    },
                },
                "answer": result.get("answer", "No answer available"),
                "citations": result.get("citations", []),
                "confidence": result.get("confidence", 0.0),
                "processing_time_ms": (time.time() - start_time) * 1000,
            }

        elif decision.intent == "CONCEPT":
            result = assemble_concept(
                target_slug=decision.target,
                query=query,
                concept_store=stores["concept_store"],
                pull=params.get("pull", False),
            )

            if "error" in result:
                return {
                    "intent": "CONCEPT",
                    "route": {
                        "target": decision.target,
                        "evidence": {
                            "matched_terms": decision.matches,
                            "confidence": decision.confidence,
                            "notes": decision.notes,
                        },
                    },
                    "error": result["error"],
                    "citations": result.get("citations", []),
                    "confidence": result.get("confidence", 0.0),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                }

            return {
                "intent": "CONCEPT",
                "route": {
                    "target": decision.target,
                    "evidence": {
                        "matched_terms": decision.matches,
                        "confidence": decision.confidence,
                        "notes": decision.notes,
                    },
                },
                "card": result.get("card", {}),
                "citations": result.get("citations", []),
                "confidence": result.get("confidence", 0.0),
                "processing_time_ms": (time.time() - start_time) * 1000,
            }

        elif decision.intent == "TROUBLESHOOT":
            result = assemble_playbook(
                target_slug=decision.target,
                query=query,
                store=stores["index_store"],
                context=params,
            )

            if "error" in result:
                # Handle insufficient steps error
                if result["error"] == "insufficient_steps":
                    return {
                        "intent": "TROUBLESHOOT",
                        "route": {
                            "target": decision.target,
                            "evidence": {
                                "matched_terms": decision.matches,
                                "confidence": decision.confidence,
                                "notes": decision.notes,
                            },
                        },
                        "error": "insufficient_steps",
                        "steps_count": result.get("steps_count", 0),
                        "citations": [],
                        "confidence": 0.0,
                        "processing_time_ms": (time.time() - start_time) * 1000,
                    }

                return {
                    "intent": "TROUBLESHOOT",
                    "route": {
                        "target": decision.target,
                        "evidence": {
                            "matched_terms": decision.matches,
                            "confidence": decision.confidence,
                            "notes": decision.notes,
                        },
                    },
                    "error": result["error"],
                    "citations": result.get("citations", []),
                    "confidence": result.get("confidence", 0.0),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                }

            # Ensure minimum steps requirement
            steps = result.get("steps", [])
            if len(steps) < 8:
                return {
                    "intent": "TROUBLESHOOT",
                    "route": {
                        "target": decision.target,
                        "evidence": {
                            "matched_terms": decision.matches,
                            "confidence": decision.confidence,
                            "notes": decision.notes,
                        },
                    },
                    "error": "insufficient_steps",
                    "steps_count": len(steps),
                    "citations": result.get("citations", []),
                    "confidence": result.get("confidence", 0.0),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                }

            return {
                "intent": "TROUBLESHOOT",
                "route": {
                    "target": decision.target,
                    "evidence": {
                        "matched_terms": decision.matches,
                        "confidence": decision.confidence,
                        "notes": decision.notes,
                    },
                },
                "steps": steps,
                "step_hash": result.get("step_hash", ""),
                "citations": result.get("citations", []),
                "confidence": result.get("confidence", 0.0),
                "deterministic": result.get("deterministic", True),
                "provenance": result.get("provenance", {}),
                "processing_time_ms": (time.time() - start_time) * 1000,
            }

        else:
            return {
                "error": f"Unknown intent: {decision.intent}",
                "processing_time_ms": (time.time() - start_time) * 1000,
            }

    except Exception as e:
        return {
            "error": f"Assembly failed: {str(e)}",
            "processing_time_ms": (time.time() - start_time) * 1000,
        }

    finally:
        # Record metrics
        elapsed = (time.time() - start_time) * 1000
        if record_query_latency:
            record_query_latency(decision.intent, decision.mode_used, elapsed)

        # Check timeout
        if elapsed > timeout_ms:
            return {
                "error": f"Assembly timeout after {elapsed:.1f}ms (limit: {timeout_ms}ms)",
                "processing_time_ms": elapsed,
            }
