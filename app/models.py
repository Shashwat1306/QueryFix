from pydantic import BaseModel, Field
from typing import Optional, Any

# --- Action ---
class Action(BaseModel):
    query_id: int = Field(..., description="ID of the query being fixed")
    fixed_query: str = Field(..., description="The agent's corrected SQL query string")

# --- Observation ---
class QueryInfo(BaseModel):
    query_id: int
    broken_query: str
    schema_description: str       # Human-readable table definitions
    error_message: str            # SQLite error or "No error but wrong result"
    expected_output_hint: str     # e.g. "Should return 3 rows with total_salary > 50000"
    attempts_used: int
    max_attempts: int

class Observation(BaseModel):
    task_id: str                  # "easy" | "medium" | "hard"
    current_query: QueryInfo
    queries_remaining: int
    queries_total: int
    queries_solved: int
    episode_score_so_far: float
    done: bool

# --- Reward ---
class Reward(BaseModel):
    value: float = Field(..., description="Reward for this step, range -1.0 to 1.0")
    reason: str = Field(..., description="Human-readable explanation of the reward")

# --- State ---
class EpisodeState(BaseModel):
    task_id: str
    current_query_index: int
    queries_total: int
    queries_solved: int
    queries_attempted: list[int]
    episode_score_so_far: float
    done: bool
    step_count: int

# --- Grader Response ---
class GraderResponse(BaseModel):
    task_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    details: dict[str, Any]

# --- Task Info (for /tasks endpoint) ---
class TaskInfo(BaseModel):
    task_id: str
    description: str
    difficulty: str
    num_queries: int
    max_attempts_per_query: int
    action_schema: dict[str, Any]

# --- Reset Request ---
class ResetRequest(BaseModel):
    task_id: str = Field("easy", description="One of: 'easy', 'medium', 'hard'")

# --- Baseline Response ---
class BaselineResponse(BaseModel):
    easy: float
    medium: float
    hard: float
    model_used: str
