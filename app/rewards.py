"""
Reward calculation logic for SQL Query Debugger environment.
"""


def calculate_reward(
    fixed_query: str,
    execution_error: str | None,
    result_match_score: float,
    attempts_used: int,
    max_attempts: int,
    original_broken_query: str
) -> tuple[float, str]:
    """
    Calculate reward for a step based on query execution and correctness.
    
    Returns:
        (reward_value, reason_string)
    
    Reward table:
    +1.0  → result_match_score == 1.0 (exact match)
    +0.6  → result_match_score >= 0.5 (partial match, right structure)
    +0.1  → execution_error is None but result_match_score < 0.5 (runs but wrong)
    -0.2  → execution_error is not None (query throws error)
    -0.5  → fixed_query.strip() == original_broken_query.strip() (no change made)
    -0.3  → fixed_query is empty string
    
    Attempt penalty:
    Subtract 0.05 * (attempts_used - 1) to encourage solving in fewer attempts.
    Clamp final reward to [-1.0, 1.0].
    """
    
    # Normalize queries for comparison
    fixed_normalized = fixed_query.strip()
    original_normalized = original_broken_query.strip()
    
    # Check for empty query
    if not fixed_normalized:
        return (-0.3, "Empty query submitted")
    
    # Check for no changes made
    if fixed_normalized == original_normalized:
        return (-0.5, "No changes made to the query")
    
    # Base reward calculation
    base_reward = 0.0
    reason = ""
    
    if execution_error is not None:
        # Query threw an error
        base_reward = -0.2
        reason = f"Query error: {execution_error}"
    elif result_match_score == 1.0:
        # Perfect match
        base_reward = 1.0
        reason = "Perfect match! Query returns correct results"
    elif result_match_score >= 0.5:
        # Partial match
        base_reward = 0.6
        reason = "Partial match - correct structure but some rows differ"
    elif result_match_score > 0.0:
        # Some match but less than 0.5
        base_reward = 0.1
        reason = "Query runs but results are mostly incorrect"
    else:
        # No match at all
        base_reward = 0.1
        reason = "Query runs but results are completely wrong"
    
    # Apply attempt penalty
    attempt_penalty = 0.05 * (attempts_used - 1)
    final_reward = base_reward - attempt_penalty
    
    # Clamp to [-1.0, 1.0]
    final_reward = max(-1.0, min(1.0, final_reward))
    
    # Add attempt info to reason if penalty was applied
    if attempt_penalty > 0:
        reason += f" (attempt {attempts_used}/{max_attempts}, penalty: -{attempt_penalty:.2f})"
    
    return (final_reward, reason)
