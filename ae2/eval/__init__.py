"""
AE v2 Evaluation Harness

This module provides evaluation tools for measuring AE v2 performance
against expert-level standards with deterministic, offline evaluation.
"""

from .metrics import (
    citation_validity,
    faithfulness,
    intent_accuracy,
    latency_stats,
    ndcg_at_k,
    precision_at_k,
    target_accuracy,
)
from .run import main as run_evaluation

__all__ = [
    "run_evaluation",
    "precision_at_k",
    "ndcg_at_k",
    "intent_accuracy",
    "target_accuracy",
    "latency_stats",
    "citation_validity",
    "faithfulness",
]
