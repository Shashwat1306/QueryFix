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

An OpenEnv-compliant environment where AI agents learn to debug broken SQL queries. The agent receives broken SQL queries with contextual information (schema, error messages, expected output hints) and must submit corrected versions. Each query is executed against an in-memory SQLite database, and results are compared to ground truth to score the agent's performance.

**Live Demo:** [Hugging Face Space](https://huggingface.co/spaces/your-username/sql-query-debugger) *(Update after deployment)*

---

## 1. Environment Description

**What is SQL Query Debugger?**

SQL Query Debugger simulates a real-world scenario where developers and data analysts must identify and fix errors in SQL queries. The environment provides three difficulty levels, each containing queries with different types of bugs:

- **Easy:** Syntax errors, typos, missing clauses
- **Medium:** JOIN issues, HAVING vs WHERE confusion, subquery problems
- **Hard:** Complex logic errors in CTEs, self-joins, nested subqueries, and subtle percentage calculations

**Why is this useful?**

- **Real-world relevance:** Debugging SQL is a daily task for backend developers and data analysts
- **Diverse error types:** Covers syntax, semantic, and logical errors
- **Immediate feedback:** Agents learn from execution results and detailed reward signals
- **Scalable difficulty:** Three progressive difficulty levels for curriculum learning

**Database Schema:**

The environment uses an in-memory SQLite database with 4 tables:
- `employees` (8 rows): Employee data with department, salary, hire date, manager relationships
- `departments` (4 rows): Department information with budgets and locations  
- `orders` (8 rows): Customer orders with products, amounts, dates, and status
- `products` (6 rows): Product catalog with categories, prices, and stock

---

## 2. Observation Space

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
  - CTE with inverted logic (< instead of >)
  - Nested subquery filtering wrong dataset
  - Self-join condition inverted
  - Percentage calculation using wrong denominator
  - SELECT alias used in WHERE clause
  - Ranking logic with inverted sort order

**Example:**
```sql
-- Broken:
WITH dept_avg AS (
    SELECT department, AVG(salary) as avg_sal
    FROM employees
    GROUP BY department
)
SELECT e.name, e.salary
FROM employees e
JOIN dept_avg d ON e.department = d.department
WHERE e.salary < d.avg_sal  -- Wrong: should be >

-- Fixed:
WHERE e.salary > d.avg_sal  -- Get employees ABOVE average
```

---

## 6. Setup Instructions

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)

### Local Setup (without Docker)

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/sql-query-debugger.git
cd sql-query-debugger
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

### Running the Baseline Agent

```bash
export OPENAI_API_KEY=sk-...
python baseline.py
```

Optional environment variables:
- `OPENAI_MODEL` (default: gpt-4o-mini)
- `BASE_URL` (default: http://localhost:8000)

---

## 7. Baseline Scores

Baseline agent using **gpt-4o-mini** via AIPipe (temperature=0.0):

| Task | Score | Queries Solved | Accuracy |
|------|-------|----------------|----------|
| Easy | 0.800 | 4/5 | 80% |
| Medium | 0.868 | 5/7 | 86.8% |
| Hard | 0.756 | 6/8 | 75.6% |
| **Average** | **0.808** | **15/20** | **80.8%** |

**Performance breakdown:**

**Easy Task (0.800):**
- ✅ Solved: Queries 1, 2, 4, 5 (syntax errors, typos, missing DESC)
- ❌ Failed: Query 3 (GROUP BY - model repeated same incorrect answer)

**Medium Task (0.868):**
- ✅ Perfect: Queries 101, 103, 105, 106, 107 (JOINs, aggregates, syntax)
- ⚠️ Partial: Queries 102, 104 (HAVING threshold, subquery logic - close but not exact)

**Hard Task (0.756):**
- ✅ Perfect: Queries 202, 203, 205, 206, 207 (nested subqueries, self-joins, aliases)
- ⚠️ Partial: Queries 201, 204, 208 (CTE logic inversion, percentage calculation, ranking order)

**Key Insights:**
- Syntax errors (typos, missing quotes) → **100% success rate**
- JOIN type errors (INNER vs LEFT) → **100% success rate**
- Logic inversions (< vs >, ASC vs DESC) → **~60% partial success** (challenging for LLMs)
- Complex percentage calculations → **Requires multiple attempts**

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
  "easy": 0.95,
  "medium": 0.82,
  "hard": 0.65,
  "model_used": "gpt-4o-mini"
}
```

---

### GET /health

Health check.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## Development

### Project Structure

```
sql-query-debugger/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI routes
│   ├── environment.py       # Core environment logic
│   ├── models.py            # Pydantic models
│   ├── database.py          # SQLite setup and execution
│   ├── rewards.py           # Reward calculation
│   ├── graders.py           # Episode grading
│   └── tasks/
│       ├── __init__.py
│       ├── task_easy.py     # Easy task queries
│       ├── task_medium.py   # Medium task queries
│       └── task_hard.py     # Hard task queries
├── baseline.py              # Baseline agent script
├── requirements.txt
├── Dockerfile
├── openenv.yaml
└── README.md
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

## Citation

If you use this environment in your research, please cite:

```bibtex
@software{sql_query_debugger,
  title = {SQL Query Debugger: An OpenEnv Environment for AI Agents},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/your-username/sql-query-debugger}
}
```

---

## License

MIT License - See LICENSE file for details

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

## Contact

- **Issues:** [GitHub Issues](https://github.com/your-username/sql-query-debugger/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-username/sql-query-debugger/discussions)

---

**Built with ❤️ for the OpenEnv ecosystem**
