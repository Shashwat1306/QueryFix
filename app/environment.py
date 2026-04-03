"""
Core environment logic for SQL Query Debugger.
Manages episode state, query execution, and scoring.
"""

import sqlite3
from typing import Any

from app.models import Action, Observation, Reward, QueryInfo, EpisodeState, GraderResponse
from app.database import init_db, execute_query, compare_results, get_schema_description
from app.rewards import calculate_reward
from app.graders import grade_episode
from app.tasks import task_easy, task_medium, task_hard


class SQLDebuggerEnvironment:
    """
    Main environment class for SQL Query Debugger.
    Implements OpenEnv interface: reset(), step(), state().
    """
    
    def __init__(self):
        self.conn: sqlite3.Connection | None = None
        self.task_id: str | None = None
        self.queries: list[dict] = []
        self.current_index: int = 0
        self.step_count: int = 0
        self.query_scores: list[float] = []  # Final score for each query
        self.queries_solved: int = 0
        self.queries_attempted: list[int] = []  # Query IDs that have been attempted
        self.attempts_remaining: dict[int, int] = {}  # query_id -> attempts left
        self.done: bool = False
        self.episode_score_so_far: float = 0.0
        
    def reset(self, task_id: str) -> Observation:
        """
        Reset environment for a new episode.
        
        Args:
            task_id: One of 'easy', 'medium', 'hard'
            
        Returns:
            Initial Observation
        """
        # Validate task_id
        if task_id not in ["easy", "medium", "hard"]:
            raise ValueError(f"Invalid task_id: {task_id}. Must be 'easy', 'medium', or 'hard'")
        
        # Load task queries
        if task_id == "easy":
            self.queries = task_easy.EASY_QUERIES
            max_attempts = task_easy.TASK_INFO["max_attempts_per_query"]
        elif task_id == "medium":
            self.queries = task_medium.MEDIUM_QUERIES
            max_attempts = task_medium.TASK_INFO["max_attempts_per_query"]
        else:  # hard
            self.queries = task_hard.HARD_QUERIES
            max_attempts = task_hard.TASK_INFO["max_attempts_per_query"]
        
        # Initialize database
        if self.conn:
            self.conn.close()
        self.conn = init_db()
        
        # Reset state
        self.task_id = task_id
        self.current_index = 0
        self.step_count = 0
        self.query_scores = []
        self.queries_solved = 0
        self.queries_attempted = []
        self.done = False
        self.episode_score_so_far = 0.0
        
        # Initialize attempts for each query
        self.attempts_remaining = {
            query["query_id"]: max_attempts 
            for query in self.queries
        }
        
        # Return initial observation
        return self._get_observation()
    
    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """
        Execute one step: agent submits a fixed query.
        
        Args:
            action: Action containing query_id and fixed_query
            
        Returns:
            (observation, reward, done, info)
        """
        if self.done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")
        
        if self.task_id is None:
            raise RuntimeError("No active episode. Call reset() first.")
        
        # Get current query
        current_query = self.queries[self.current_index]
        
        # Validate query_id matches
        if action.query_id != current_query["query_id"]:
            raise ValueError(
                f"Query ID mismatch. Expected {current_query['query_id']}, got {action.query_id}"
            )
        
        # Track attempts
        self.step_count += 1
        max_attempts = self._get_max_attempts()
        attempts_used = max_attempts - self.attempts_remaining[action.query_id] + 1
        self.attempts_remaining[action.query_id] -= 1
        
        if action.query_id not in self.queries_attempted:
            self.queries_attempted.append(action.query_id)
        
        # Execute the fixed query
        actual_result, execution_error = execute_query(self.conn, action.fixed_query)
        
        # Compare with expected result
        expected_result = current_query["expected_result"]
        if execution_error is None:
            result_match_score = compare_results(actual_result, expected_result)
        else:
            result_match_score = 0.0
        
        # Calculate reward
        reward_value, reward_reason = calculate_reward(
            fixed_query=action.fixed_query,
            execution_error=execution_error,
            result_match_score=result_match_score,
            attempts_used=attempts_used,
            max_attempts=max_attempts,
            original_broken_query=current_query["broken_query"]
        )
        
        reward = Reward(value=reward_value, reason=reward_reason)
        
        # Check if query is solved (perfect match)
        query_solved = result_match_score == 1.0
        
        # Check if we should advance to next query
        should_advance = False
        if query_solved:
            # Query solved perfectly - advance
            self.queries_solved += 1
            self.query_scores.append(1.0)
            should_advance = True
        elif self.attempts_remaining[action.query_id] <= 0:
            # Out of attempts - record score and advance
            # Score is based on best result achieved (use result_match_score)
            self.query_scores.append(max(0.0, result_match_score))
            should_advance = True
        
        # Update episode score
        if should_advance:
            self.episode_score_so_far = sum(self.query_scores) / len(self.query_scores)
        
        # Advance to next query or end episode
        if should_advance:
            self.current_index += 1
            if self.current_index >= len(self.queries):
                self.done = True
        
        # Build observation
        observation = self._get_observation()
        
        # Build info dict
        info = {
            "execution_error": execution_error,
            "result_match_score": result_match_score,
            "query_solved": query_solved,
            "attempts_used": attempts_used,
            "attempts_remaining": self.attempts_remaining[action.query_id],
        }
        
        return observation, reward, self.done, info
    
    def state(self) -> EpisodeState:
        """
        Return current episode state snapshot.
        """
        if self.task_id is None:
            raise RuntimeError("No active episode. Call reset() first.")
        
        return EpisodeState(
            task_id=self.task_id,
            current_query_index=self.current_index,
            queries_total=len(self.queries),
            queries_solved=self.queries_solved,
            queries_attempted=self.queries_attempted,
            episode_score_so_far=self.episode_score_so_far,
            done=self.done,
            step_count=self.step_count
        )
    
    def get_grader_score(self) -> GraderResponse:
        """
        Calculate final episode score. Must be called after episode is done.
        """
        if not self.done:
            raise RuntimeError("Episode not complete. Cannot grade yet.")
        
        if self.task_id is None:
            raise RuntimeError("No active episode.")
        
        return grade_episode(self.task_id, self.query_scores)
    
    def _get_observation(self) -> Observation:
        """
        Build current observation.
        """
        if self.task_id is None:
            raise RuntimeError("No active episode.")
        
        # If episode is done, return minimal observation
        if self.done:
            # Use last query info
            last_query = self.queries[self.current_index - 1]
            query_info = QueryInfo(
                query_id=last_query["query_id"],
                broken_query=last_query["broken_query"],
                schema_description=get_schema_description(),
                error_message="Episode complete",
                expected_output_hint=last_query["expected_output_hint"],
                attempts_used=self._get_max_attempts(),
                max_attempts=self._get_max_attempts()
            )
            
            return Observation(
                task_id=self.task_id,
                current_query=query_info,
                queries_remaining=0,
                queries_total=len(self.queries),
                queries_solved=self.queries_solved,
                episode_score_so_far=self.episode_score_so_far,
                done=True
            )
        
        # Get current query
        current_query = self.queries[self.current_index]
        max_attempts = self._get_max_attempts()
        attempts_used = max_attempts - self.attempts_remaining[current_query["query_id"]]
        
        query_info = QueryInfo(
            query_id=current_query["query_id"],
            broken_query=current_query["broken_query"],
            schema_description=get_schema_description(),
            error_message=current_query["error_message"],
            expected_output_hint=current_query["expected_output_hint"],
            attempts_used=attempts_used,
            max_attempts=max_attempts
        )
        
        return Observation(
            task_id=self.task_id,
            current_query=query_info,
            queries_remaining=len(self.queries) - self.current_index - 1,
            queries_total=len(self.queries),
            queries_solved=self.queries_solved,
            episode_score_so_far=self.episode_score_so_far,
            done=False
        )
    
    def _get_max_attempts(self) -> int:
        """Get max attempts for current task."""
        if self.task_id == "easy":
            return task_easy.TASK_INFO["max_attempts_per_query"]
        elif self.task_id == "medium":
            return task_medium.TASK_INFO["max_attempts_per_query"]
        else:  # hard
            return task_hard.TASK_INFO["max_attempts_per_query"]
