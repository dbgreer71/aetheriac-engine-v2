"""
Evaluation metrics for AE v2.

This module provides deterministic metrics for evaluating AE v2 performance
against expert-level standards.
"""

import hashlib
import math
from typing import Dict, List


def precision_at_k(pred_ids: List[str], gold_id: str, k: int) -> float:
    """Calculate precision at k for a single prediction."""
    if k == 0:
        return 0.0

    # Sort predictions for determinism
    pred_ids_sorted = sorted(pred_ids[:k])
    gold_id_sorted = sorted([gold_id])

    # Count relevant items in top k
    relevant = sum(1 for pred in pred_ids_sorted if pred in gold_id_sorted)
    return round(relevant / k, 3)


def ndcg_at_k(scores: List[float], ideal_scores: List[float], k: int) -> float:
    """Calculate normalized discounted cumulative gain at k."""
    if k == 0:
        return 0.0

    def dcg(scores_list: List[float], k_limit: int) -> float:
        """Calculate discounted cumulative gain."""
        dcg_score = 0.0
        for i in range(min(k_limit, len(scores_list))):
            dcg_score += scores_list[i] / math.log2(i + 2)  # log2(i+2) for 0-indexed
        return dcg_score

    # Sort scores for determinism
    scores_sorted = sorted(scores[:k], reverse=True)
    ideal_sorted = sorted(ideal_scores[:k], reverse=True)

    dcg_score = dcg(scores_sorted, k)
    idcg_score = dcg(ideal_sorted, k)

    if idcg_score == 0:
        return 0.0

    return round(dcg_score / idcg_score, 3)


def intent_accuracy(golds: List[str], preds: List[str]) -> float:
    """Calculate intent classification accuracy."""
    if not golds or not preds:
        return 0.0

    # Sort for determinism
    golds_sorted = sorted(golds)
    preds_sorted = sorted(preds)

    correct = sum(1 for g, p in zip(golds_sorted, preds_sorted) if g == p)
    return round(correct / len(golds), 3)


def target_accuracy(gold_rfcs: List[int], pred_rfcs: List[int]) -> float:
    """Calculate target RFC accuracy."""
    if not gold_rfcs or not pred_rfcs:
        return 0.0

    # Sort for determinism
    gold_sorted = sorted(gold_rfcs)
    pred_sorted = sorted(pred_rfcs)

    correct = sum(1 for g, p in zip(gold_sorted, pred_sorted) if g == p)
    return round(correct / len(gold_rfcs), 3)


def latency_stats(samples_ms: List[float]) -> Dict[str, float]:
    """Calculate latency statistics."""
    if not samples_ms:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0}

    # Sort for determinism
    sorted_samples = sorted(samples_ms)
    n = len(sorted_samples)

    # Calculate percentiles
    p50_idx = int(0.5 * n)
    p95_idx = int(0.95 * n)
    p99_idx = int(0.99 * n)

    p50 = sorted_samples[p50_idx] if p50_idx < n else sorted_samples[-1]
    p95 = sorted_samples[p95_idx] if p95_idx < n else sorted_samples[-1]
    p99 = sorted_samples[p99_idx] if p99_idx < n else sorted_samples[-1]
    avg = sum(sorted_samples) / n

    return {
        "p50": round(p50, 3),
        "p95": round(p95, 3),
        "p99": round(p99, 3),
        "avg": round(avg, 3),
    }


def citation_validity(answer: Dict) -> bool:
    """Check if citations are valid (RFC URL + section)."""
    if not answer or "citations" not in answer:
        return False

    citations = answer.get("citations", [])
    if not citations:
        return False

    for citation in citations:
        # Check for required fields
        if not isinstance(citation, dict):
            return False

        # For definitions: must have RFC URL and section
        if "url" not in citation or "section" not in citation:
            return False

        # URL should contain RFC number
        url = citation.get("url", "")
        if "rfc" not in url.lower():
            return False

        # Section should be present
        section = citation.get("section", "")
        if not section:
            return False

    return True


def faithfulness(answer: Dict) -> bool:
    """Check if all claims reference valid evidence."""
    if not answer:
        return False

    # For concept cards: check claims have evidence
    if "claims" in answer:
        claims = answer.get("claims", [])
        for claim in claims:
            if not isinstance(claim, dict):
                return False

            # Check evidence field exists
            if "evidence" not in claim:
                return False

            evidence = claim.get("evidence", [])
            if not evidence:
                return False

            # Check each evidence item has required fields
            for ev in evidence:
                if not isinstance(ev, dict):
                    return False

                # Must have sha256 and url
                if "sha256" not in ev or "url" not in ev:
                    return False

    # For definitions: check citations exist
    elif "citations" in answer:
        return citation_validity(answer)

    return True


def calculate_dataset_hash(file_path: str) -> str:
    """Calculate SHA256 hash of dataset file."""
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return ""


def get_git_revision() -> str:
    """Get git short hash of current revision."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
