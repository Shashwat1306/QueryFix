---
title: QueryFix
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
  - openenv
---



# SQL Query Debugger — OpenEnv Environment

SQL debugging accounts for a significant portion of developer time, yet no standardized RL environment exists for it. QueryFix fills this gap — a fully deterministic OpenEnv environment where AI agents learn to identify and fix broken SQL queries across syntax, semantic, and logical error categories. Built on SQLite with 20 hand-crafted queries spanning 6 bug types, QueryFix provides immediate value for benchmarking LLM code reasoning capabilities.

**Live Demo:** [QueryFix on Hugging Face](https://huggingface.co/spaces/Shashwat1306/queryfix-env)

---

## 1. Environment Description

**What is SQL Query Debugger?**

SQL Query Debugger simulates a real-world scenario where developers and data analysts must identify and fix errors in SQL queries. The environment provides three difficulty levels, each containing queries with different types of bugs:

- **Easy:** Syntax errors, typos, missing clauses
- **Medium:** JOIN issues, HAVING vs WHERE confusion, subquery problems
- **Hard:** NULL aggregation in LEFT JOINs, silent INNER JOIN exclusions, self-join inversions, subquery scope errors, and percentage calculation bugs

**Why is this useful?**

- **Real-world relevance:** Debugging SQL is a daily task for backend developers and data analysts
- **Diverse error types:** Covers syntax, semantic, and logical errors
- **Immediate feedback:** Agents learn from execution results and detailed reward signals
- **Scalable difficulty:** Three progressive difficulty levels for curriculum learning

---

## Why QueryFix?

| Problem | QueryFix Solution |
|---|---|
| SQL debugging is time-consuming for developers | Trains agents to debug automatically |
| No SQL-specific RL benchmark exists | Fills a real gap in OpenEnv ecosystem |
| LLM code reasoning is hard to evaluate | Deterministic SQLite graders remove ambiguity |
| Difficulty calibration is often arbitrary | 3 tiers validated against gpt-4o-mini baseline |

**Database Schema:**

The environment uses an in-memory SQLite database with 4 tables:
- `employees` (8 rows): Employee data with department, salary, hire date, manager relationships
- `departments` (4 rows): Department information with budgets and locations  
- `orders` (8 rows): Customer orders with products, amounts, dates, and status
- `products` (6 rows): Product catalog with categories, prices, and stock

---

## 2. Observation Space

The observation space gives the agent all information a human developer would have when debugging: the broken query, the database schema, the error message, and a high-level description of the expected output. Crucially, the agent is NOT given the correct answer — it must reason about the bug from context alone.

After calling `/reset` or `/step`, the agent receives an **Observation** object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Current task: "easy", "medium", or "hard" |
| `current_query` | `QueryInfo` | Details about the current query to fix |
| `queries_remaining` | `int` | Number of queries left in this episode (not counting current) |
| `queries_total` | `int` | Total queries in this task (5 for easy, 7 for medium, 8 for hard) |
| `queries_solved` | `int` | Number of queries solved perfectly so far |
| `episode_score_so_far` | `float` | Current cumulative score for this episode |
| `done` | `bool` | True if episode is complete |

**QueryInfo object:**

| Field | Type | Description |
|-------|------|-------------|
| `query_id` | `int` | Unique identifier for this query |
| `broken_query` | `str` | The broken SQL query to fix |
| `schema_description` | `str` | Human-readable database schema documentation |
| `error_message` | `str` | SQLite error or "No error but wrong result" |
| `expected_output_hint` | `str` | Hint about what the query should return |
| `attempts_used` | `int` | How many attempts have been used on this query |
| `max_attempts` | `int` | Maximum attempts allowed (3 for easy/medium, 2 for hard) |

---

## 3. Action Space

The action space is intentionally minimal — the agent submits a single fixed SQL query per step. This mirrors how a developer actually debugs: read the error, think about the fix, submit a new query. No intermediate steps, no partial edits.

The agent submits an **Action** object:

| Field | Type | Description |
|-------|------|-------------|
| `query_id` | `int` | Must match the `query_id` from current observation |
| `fixed_query` | `str` | The corrected SQL query string |

**Constraints:**
- `query_id` must match the current query being worked on
- `fixed_query` should be valid SQL (errors result in negative reward)
- Whitespace and formatting are ignored when comparing to original

---

## 4. Reward Function

The reward system encourages correct solutions while penalizing errors and excessive attempts:

| Scenario | Base Reward | Description |
|----------|-------------|-------------|
| Perfect match | **+1.0** | Query results exactly match expected output |
| Partial match | **+0.6** | Correct structure, some rows match (≥50% overlap) |
| Runs but wrong | **+0.1** | Query executes but results are mostly incorrect |
| Execution error | **-0.2** | Query throws SQLite error |
| No changes made | **-0.5** | Submitted query identical to broken query |
| Empty query | **-0.3** | Submitted query is empty |

**Attempt Penalty:** `-0.05 * (attempts_used - 1)` to encourage solving in fewer attempts

**Final reward is clamped to [-1.0, 1.0]**

**Example:**
- Query solved on first attempt: +1.0
- Query solved on second attempt: +0.95 (1.0 - 0.05)
- Query solved on third attempt: +0.90 (1.0 - 0.10)
- Query with execution error on first attempt: -0.2

---

## 5. Task Descriptions

### Easy Task
- **Queries:** 5
- **Max attempts per query:** 3
- **Bug types:** 
  - Missing commas in SELECT lists
  - Typos (FORM instead of FROM, ORDERED instead of ORDER BY)
  - Missing quotes around string literals
  - Missing GROUP BY clause
  - Missing DESC in ORDER BY

**Example:**
```sql
-- Broken:
SELECT name salary FROM employees

-- Fixed:
SELECT name, salary FROM employees
```

### Medium Task
- **Queries:** 7
- **Max attempts per query:** 3
- **Bug types:**
  - INNER JOIN when LEFT JOIN is needed
  - Using aggregate in WHERE instead of HAVING
  - ORDER BY without DESC returning wrong extremum
  - Subquery returning multiple rows when scalar expected
  - Column alias used in HAVING (not allowed in SQLite)

**Example:**
```sql
-- Broken:
SELECT department, AVG(salary) as avg_salary
FROM employees
WHERE AVG(salary) > 70000  -- Error: aggregate in WHERE
GROUP BY department

-- Fixed:
SELECT department, AVG(salary) as avg_salary
FROM employees
GROUP BY department
HAVING AVG(salary) > 70000
```

### Hard Task
- **Queries:** 8
- **Max attempts per query:** 2
- **Bug types:**
  - NULL aggregation errors in LEFT JOINs
  - Nested subquery filtering wrong dataset
  - Self-join condition inverted
  - Percentage calculation using wrong denominator
  - SELECT alias used in WHERE clause
  - INNER JOIN silently excluding NULL rows

**Example:**
```sql
-- Broken:
SELECT d.name as department, COUNT(e.id) as headcount,
       SUM(e.salary) as total_salary
FROM departments d
LEFT JOIN employees e ON e.department = d.name
GROUP BY d.name

-- Bug: SUM(e.salary) returns NULL for Finance (no employees)
-- instead of 0. Must use COALESCE.

-- Fixed:
SELECT d.name as department, COUNT(e.id) as headcount,
       COALESCE(SUM(e.salary), 0) as total_salary
FROM departments d
LEFT JOIN employees e ON e.department = d.name
GROUP BY d.name
```

---

## Bug Categories

| Category | Examples | Difficulty |
|---|---|---|
| Syntax | Missing commas, typos, unquoted strings | Easy |
| Clause | Missing GROUP BY, WHERE vs HAVING | Easy, Medium |
| JOIN | INNER vs LEFT JOIN, self-join inversion | Medium, Hard |
| Aggregate | Wrong aggregate function, missing alias | Medium |
| Subquery | Scalar vs multi-row, scope errors | Medium, Hard |
| NULL Handling | COALESCE, LEFT JOIN aggregation | Hard |

---

## 6. Setup Instructions

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)

**Note on Ports:** Local setup uses port 8000, Docker uses port 7860 (required by HF Spaces)

### Local Setup (without Docker)

1. **Clone the repository:**
```bash
git clone https://huggingface.co/spaces/Shashwat1306/queryfix-env
cd queryfix-env
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the server:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. **Test the server:**
```bash
curl http://localhost:8000/health
```

### Docker Setup

1. **Build the image:**
```bash
docker build -t sql-query-debugger .
```

2. **Run the container:**
```bash
docker run -p 7860:7860 sql-query-debugger
```

3. **Test the server:**
```bash
curl http://localhost:7860/health
```

---

## API Keys & Authentication

This environment uses the OpenAI API for the `/baseline` endpoint only.

### Standard OpenAI / HF Router (for judges / evaluators)
Set your API key as an environment variable:
```bash
export OPENAI_API_KEY=your-hf-token
export OPENAI_BASE_URL=https://router.huggingface.co/v1
python baseline.py
```

### AIPipe (alternative)
```bash
export OPENAI_API_KEY=your-aipipe-token
export OPENAI_BASE_URL=https://aipipe.org/openai/v1
python baseline.py
```

The client automatically falls back to standard OpenAI 
(https://api.openai.com/v1) if OPENAI_BASE_URL is not set.
Both setups work identically.

### Running the Baseline Agent

```bash
export HF_TOKEN=your-api-key
export BASE_URL=http://localhost:8000
python baseline.py
```

Optional environment variables:
- `OPENAI_MODEL` (default: Qwen/Qwen2.5-72B-Instruct)
- `OPENAI_BASE_URL` (default: https://router.huggingface.co/v1)
- `BASE_URL` (default: http://localhost:8000)

---

## Inference Script

The `inference.py` script runs the LLM agent against all 3 tasks and emits structured logs.

### Required Environment Variables
| Variable | Description |
|---|---|
| `HF_TOKEN` | Your HF token or API key |
| `API_BASE_URL` | LLM endpoint (default: https://router.huggingface.co/v1) |
| `MODEL_NAME` | Model identifier (default: Qwen/Qwen2.5-72B-Instruct) |
| `BASE_URL` | Environment server URL (default: http://localhost:7860) |

### Run Locally
```bash
export HF_TOKEN=your-api-key
export API_BASE_URL=https://aipipe.org/openai/v1
export MODEL_NAME=gpt-4o-mini
export BASE_URL=http://localhost:7860
python inference.py
```

### Output Format
```
[START] task=easy env=queryfix-sql-debugger model=gpt-4o-mini
[STEP] step=1 action=SELECT name, salary FROM employees reward=1.00 done=false error=null
[END] success=true steps=5 score=0.990 rewards=1.00,1.00,1.00,1.00,1.00
```

### Inference Results
| Task | Score | Steps |
|---|---|---|
| Easy | 0.990 | 5 |
| Medium | 0.868 | 11 |
| Hard | 0.650 | 12 |

---

## 7. Baseline Scores

Baseline agent using **gpt-4o-mini** via AIPipe (temperature=0.0):

| Task | Score | Queries Solved |
|------|-------|----------------|
| Easy | 0.990 | 5/5 queries solved |
| Medium | 0.868 | 5/7 queries solved |
| Hard | 0.650 | 5/8 queries solved |
| **Average** | **0.836** | **15/20 total** |

**Performance breakdown:**

**Easy Task (0.990):**
- ✅ Solved: All 5 queries perfectly on first attempt

**Medium Task (0.868):**
- ✅ Perfect: Queries 101, 103, 105, 106, 107
- ⚠️ Partial: Queries 102, 104 (HAVING threshold, subquery logic)

**Hard Task (0.650):**
- ✅ Perfect: Queries 202, 203, 206, 207, 208
- ⚠️ Partial/Failed: Queries 201, 204, 205
  - Query 201: NULL aggregation in LEFT JOIN (COALESCE pattern)
  - Query 204: Percentage calculation with wrong denominator scope
  - Query 205: INNER JOIN silently excluding NULL manager_id rows

---

## 8. API Reference

### POST /reset

Initialize a new episode.

**Request:**
```json
{
  "task_id": "easy"
}
```

**Response:** `Observation` object

**Example:**
```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy"}'
```

---

### POST /step

Submit a fixed query.

**Request:**
```json
{
  "query_id": 1,
  "fixed_query": "SELECT name, salary FROM employees"
}
```

**Response:**
```json
{
  "observation": { ... },
  "reward": {
    "value": 1.0,
    "reason": "Perfect match! Query returns correct results"
  },
  "done": false,
  "info": {
    "execution_error": null,
    "result_match_score": 1.0,
    "query_solved": true,
    "attempts_used": 1,
    "attempts_remaining": 2
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "fixed_query": "SELECT name, salary FROM employees"}'
```

---

### GET /state

Get current episode state.

**Response:** `EpisodeState` object

**Example:**
```bash
curl http://localhost:8000/state
```

---

### GET /tasks

Get metadata for all tasks.

**Response:** Array of `TaskInfo` objects

**Example:**
```bash
curl http://localhost:8000/tasks
```

---

### POST /grader

Get final episode score (call after `done=true`).

**Response:**
```json
{
  "task_id": "easy",
  "score": 0.95,
  "details": {
    "num_queries": 5,
    "grading_method": "simple mean",
    "query_scores": [1.0, 1.0, 0.95, 0.85, 1.0]
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/grader
```

---

### POST /baseline

Run baseline agent on all tasks (requires `OPENAI_API_KEY`).

**Response:**
```json
{
  "easy": 0.990,
  "medium": 0.868,
  "hard": 0.650,
  "model_used": "gpt-4o-mini"
}
```
---

### GET /health

Health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Development

### Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI routes
├── environment.py       # Core environment logic
├── models.py            # Pydantic models
├── database.py          # SQLite setup and execution
├── rewards.py           # Reward calculation
├── graders.py           # Episode grading
└── tasks/
    ├── __init__.py
    ├── task_easy.py     # Easy task queries
    ├── task_medium.py   # Medium task queries
    └── task_hard.py     # Hard task queries
server/
└── app.py               # Server entry point
baseline.py              # Baseline agent script
inference.py             # Inference script for evaluation
requirements.txt         # Python dependencies
pyproject.toml           # Project metadata and dependencies
uv.lock                  # Lockfile for reproducible builds
Dockerfile               # Docker configuration
openenv.yaml             # OpenEnv metadata
README.md                # Documentation
.env.example             # Environment variables template
.gitignore               # Git ignore rules
```

### Adding New Tasks

1. Create a new task file in `app/tasks/`
2. Define `TASK_INFO` and query list
3. Import in `app/environment.py`
4. Add to `/tasks` endpoint in `app/main.py`

### Testing

```bash
# Start server
uvicorn app.main:app --reload

# In another terminal, test endpoints
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{"task_id":"easy"}'
```

---

## Known Limitations

- Fixed dataset of 20 queries — future work could add dynamic query generation
- Single SQLite schema — real-world environments have diverse schemas  
- No multi-turn context — agent sees each query independently without conversation history
- LLM baseline shows minor variance across runs due to non-deterministic sampling

---

## Citation

If you use this environment in your research, please cite:

```bibtex
@software{sql_query_debugger,
  title = {QueryFix: SQL Query Debugger OpenEnv Environment},
  author = {Shashwat},
  year = {2026},
  url = {https://huggingface.co/spaces/Shashwat1306/queryfix-env}
}
```

---

## License

MIT License - See LICENSE file for details

---

**Built with ❤️ for the OpenEnv ecosystem**
