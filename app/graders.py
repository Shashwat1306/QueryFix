"""
Grader logic for SQL Query Debugger environment.
Calculates final episode scores based on per-query performance.
"""

from typing import Any
from app.models import GraderResponse


def clamp_score(score: float) -> float:
    """Clamp score to strictly between 0 and 1 (not including 0.0 or 1.0)."""
    return max(0.01, min(0.99, score))


def grade_episode(
    task_id: str,
    query_scores: list[float]   # one score per query, in order
) -> GraderResponse:
    """
    Calculate final episode score based on task difficulty and performance.
    
    Easy task: simple mean of all query scores
    Medium task: weighted mean (later queries weighted slightly higher)
    Hard task: weighted mean, bonus +0.1 if all queries scored >= 0.5
    
    All final scores clamped to [0.0, 1.0].
    Returns GraderResponse with task_id, score, and details dict.
    """
    
    if not query_scores:
        return GraderResponse(
            task_id=task_id,
            score=0.0,
            details={
                "num_queries": 0,
                "grading_method": "no queries",
                "error": "No query scores available"
            }
        )
    
    num_queries = len(query_scores)
    
    if task_id == "easy":
        # Simple mean for easy task
        final_score = sum(query_scores) / num_queries
        grading_method = "simple mean"
        details = {
            "num_queries": num_queries,
            "grading_method": grading_method,
            "query_scores": query_scores,
            "mean_score": final_score,
        }
    
    elif task_id == "medium":
        # Weighted mean - later queries weighted slightly higher
        # Weights: 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6 for 7 queries
        weights = [1.0 + (i * 0.1) for i in range(num_queries)]
        weighted_sum = sum(score * weight for score, weight in zip(query_scores, weights))
        total_weight = sum(weights)
        final_score = weighted_sum / total_weight
        grading_method = "weighted mean (progressive)"
        details = {
            "num_queries": num_queries,
            "grading_method": grading_method,
            "query_scores": query_scores,
            "weights": weights,
            "weighted_score": final_score,
        }
    
    elif task_id == "hard":
        # Weighted mean with bonus for consistent performance
        weights = [1.0 + (i * 0.15) for i in range(num_queries)]
        weighted_sum = sum(score * weight for score, weight in zip(query_scores, weights))
        total_weight = sum(weights)
        base_score = weighted_sum / total_weight
        
        # Bonus: +0.1 if ALL queries scored >= 0.5
        all_passing = all(score >= 0.5 for score in query_scores)
        bonus = 0.1 if all_passing else 0.0
        
        final_score = base_score + bonus
        grading_method = "weighted mean with consistency bonus"
        details = {
            "num_queries": num_queries,
            "grading_method": grading_method,
            "query_scores": query_scores,
            "weights": weights,
            "base_score": base_score,
            "consistency_bonus": bonus,
            "all_queries_passing": all_passing,
            "final_score": final_score,
        }
    
    else:
        # Unknown task - fallback to simple mean
        final_score = sum(query_scores) / num_queries
        grading_method = "simple mean (fallback)"
        details = {
            "num_queries": num_queries,
            "grading_method": grading_method,
            "query_scores": query_scores,
            "warning": f"Unknown task_id: {task_id}",
        }
    
    # Clamp final score to strictly between 0 and 1 (0.01 to 0.99)
    final_score = clamp_score(final_score)
    
    return GraderResponse(
        task_id=task_id,
        score=final_score,
        details=details
    )
