"""
FastAPI application for SQL Query Debugger OpenEnv.
Implements all required endpoints.
"""

import os
from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import httpx

from app.models import (
    Action, Observation, Reward, ResetRequest, 
    EpisodeState, GraderResponse, TaskInfo, BaselineResponse
)
from app.environment import SQLDebuggerEnvironment
from app.tasks import task_easy, task_medium, task_hard
from app.graders import clamp_score


# Initialize FastAPI app
app = FastAPI(
    title="SQL Query Debugger",
    description="An OpenEnv environment where AI agents debug broken SQL queries",
    version="1.0.0"
)

# Initialize environment instance on startup
@app.on_event("startup")
async def startup_event():
    app.state.env = SQLDebuggerEnvironment()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/metadata")
async def metadata():
    """Environment metadata endpoint."""
    return {
        "name": "QueryFix SQL Query Debugger",
        "description": "An OpenEnv environment where AI agents debug broken SQL queries across three difficulty levels. Queries are executed against SQLite and scored by comparing results to ground truth.",
        "version": "1.0.0",
        "author": "Shashwat1306"
    }


@app.get("/schema")
async def schema():
    """Schema endpoint describing action, observation, and state structures."""
    return {
        "action": {
            "type": "object",
            "properties": {
                "query_id": {"type": "integer", "description": "ID of the query being fixed"},
                "fixed_query": {"type": "string", "description": "The corrected SQL query string"}
            },
            "required": ["query_id", "fixed_query"]
        },
        "observation": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "current_query": {"type": "object"},
                "queries_remaining": {"type": "integer"},
                "queries_total": {"type": "integer"},
                "queries_solved": {"type": "integer"},
                "episode_score_so_far": {"type": "number"},
                "done": {"type": "boolean"}
            }
        },
        "state": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "current_query_index": {"type": "integer"},
                "queries_total": {"type": "integer"},
                "queries_solved": {"type": "integer"},
                "episode_score_so_far": {"type": "number"},
                "done": {"type": "boolean"},
                "step_count": {"type": "integer"}
            }
        }
    }


@app.post("/mcp")
async def mcp():
    """MCP endpoint for model context protocol."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "name": "QueryFix SQL Query Debugger",
            "version": "1.0.0",
            "description": "OpenEnv environment for SQL query debugging"
        }
    }


@app.post("/reset", response_model=Observation)
async def reset(request: Optional[ResetRequest] = None):
    """
    Reset the environment for a new episode.
    
    Args:
        request: ResetRequest with task_id (optional, defaults to "easy")
        
    Returns:
        Initial Observation
    """
    if request is None:
        request = ResetRequest()  # Uses default task_id="easy"
    
    try:
        observation = app.state.env.reset(request.task_id)
        return observation
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/step")
async def step(action: Action):
    """
    Execute one step: agent submits a fixed query.
    
    Args:
        action: Action with query_id and fixed_query
        
    Returns:
        Dict with observation, reward, done, info
    """
    try:
        observation, reward, done, info = app.state.env.step(action)
        return {
            "observation": observation,
            "reward": reward,
            "done": done,
            "info": info
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/state", response_model=EpisodeState)
async def state():
    """
    Get current episode state.
    
    Returns:
        EpisodeState with current episode information
    """
    try:
        return app.state.env.state()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/tasks", response_model=list[TaskInfo])
async def tasks():
    """
    Get metadata for all available tasks.
    
    Returns:
        List of TaskInfo for all tasks
    """
    action_schema = {
        "query_id": "int — ID of the query being fixed",
        "fixed_query": "str — The corrected SQL query string"
    }
    
    tasks_list = [
        TaskInfo(
            task_id=task_easy.TASK_INFO["task_id"],
            description=task_easy.TASK_INFO["description"],
            difficulty=task_easy.TASK_INFO["difficulty"],
            num_queries=task_easy.TASK_INFO["num_queries"],
            max_attempts_per_query=task_easy.TASK_INFO["max_attempts_per_query"],
            action_schema=action_schema
        ),
        TaskInfo(
            task_id=task_medium.TASK_INFO["task_id"],
            description=task_medium.TASK_INFO["description"],
            difficulty=task_medium.TASK_INFO["difficulty"],
            num_queries=task_medium.TASK_INFO["num_queries"],
            max_attempts_per_query=task_medium.TASK_INFO["max_attempts_per_query"],
            action_schema=action_schema
        ),
        TaskInfo(
            task_id=task_hard.TASK_INFO["task_id"],
            description=task_hard.TASK_INFO["description"],
            difficulty=task_hard.TASK_INFO["difficulty"],
            num_queries=task_hard.TASK_INFO["num_queries"],
            max_attempts_per_query=task_hard.TASK_INFO["max_attempts_per_query"],
            action_schema=action_schema
        ),
    ]
    
    return tasks_list


@app.post("/grader", response_model=GraderResponse)
async def grader():
    """
    Get final episode score. Must be called after episode is done.
    
    Returns:
        GraderResponse with score and details
    """
    try:
        return app.state.env.get_grader_score()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/baseline", response_model=BaselineResponse)
async def baseline():
    """
    Run baseline agent on all tasks using OpenAI API.
    Requires OPENAI_API_KEY environment variable.
    
    Returns:
        BaselineResponse with scores for all tasks
    """
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY not configured. Set environment variable to use baseline."
        )
    
    try:
        # Import baseline logic
        from openai import OpenAI
        
        # Use internal URL
        BASE_URL = os.getenv("BASE_URL", "http://localhost:7860")
        print(f"Baseline using BASE_URL: {BASE_URL}")  # Debug log
        
        MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
        
        SYSTEM_PROMPT = """You are a SQL debugging expert. You will be given a broken SQL query along with:
- The database schema
- The error message (if any)
- A hint about the expected output

Your job is to return ONLY the corrected SQL query, with no explanation, no markdown, no code fences.
Just the raw SQL string."""
        
        # Initialize OpenAI client with optional base URL
        if OPENAI_BASE_URL:
            client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)
        else:
            client = OpenAI(api_key=api_key)
        
        scores = {}
        
        # Use httpx AsyncClient for HTTP requests
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            for task_id in ["easy", "medium", "hard"]:
                # Reset environment
                reset_response = await http_client.post(f"{BASE_URL}/reset", json={"task_id": task_id})
                if reset_response.status_code != 200:
                    scores[task_id] = 0.01  # Use minimum clamped value
                    continue
                    
                obs = reset_response.json()
                done = False
                
                while not done:
                    # Build prompt from observation
                    current_query = obs["current_query"]
                    user_prompt = f"""
Schema:
{current_query['schema_description']}

Broken query:
{current_query['broken_query']}

Error message:
{current_query['error_message']}

Expected output hint:
{current_query['expected_output_hint']}

Return only the fixed SQL query:
"""
                    # Call OpenAI
                    try:
                        response = client.chat.completions.create(
                            model=MODEL,
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.0
                        )
                        
                        fixed_query = response.choices[0].message.content.strip()
                        
                        # Step environment
                        step_response = await http_client.post(f"{BASE_URL}/step", json={
                            "query_id": current_query["query_id"],
                            "fixed_query": fixed_query
                        })
                        
                        if step_response.status_code != 200:
                            break
                            
                        step_result = step_response.json()
                        obs = step_result["observation"]
                        done = step_result["done"]
                        
                    except Exception as e:
                        # If OpenAI call fails, break
                        scores[task_id] = 0.01  # Use minimum clamped value
                        done = True
                        break
                
                # Get grader score
                if done:
                    grader_response = await http_client.post(f"{BASE_URL}/grader")
                    if grader_response.status_code == 200:
                        scores[task_id] = clamp_score(grader_response.json()["score"])
                    else:
                        scores[task_id] = 0.01  # Use minimum clamped value instead of 0.0
        
        return BaselineResponse(
            easy=clamp_score(scores.get("easy", 0.01)),
            medium=clamp_score(scores.get("medium", 0.01)),
            hard=clamp_score(scores.get("hard", 0.01)),
            model_used=MODEL
        )
        
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Missing required packages: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline execution failed: {str(e)}"
        )


# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QueryFix — SQL Query Debugger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f1117;
            color: #e6edf3;
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 50px; }
        .emoji { font-size: 64px; margin-bottom: 16px; }
        h1 { font-size: 42px; font-weight: 700; color: #58a6ff; margin-bottom: 8px; }
        .subtitle { font-size: 18px; color: #8b949e; line-height: 1.6; max-width: 600px; margin: 0 auto; }
        .badges { display: flex; gap: 10px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }
        .badge {
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 13px;
            color: #58a6ff;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
        }
        .stat-value { font-size: 36px; font-weight: 700; color: #58a6ff; }
        .stat-label { font-size: 13px; color: #8b949e; margin-top: 4px; }
        .section { margin-bottom: 32px; }
        h2 { font-size: 20px; font-weight: 600; margin-bottom: 16px; color: #e6edf3; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
        .tasks { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .task-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
        }
        .task-title { font-weight: 600; font-size: 16px; margin-bottom: 8px; }
        .easy { color: #3fb950; }
        .medium { color: #d29922; }
        .hard { color: #f85149; }
        .task-score { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
        .task-meta { font-size: 12px; color: #8b949e; }
        .endpoints { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .endpoint {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            color: #e6edf3;
            transition: border-color 0.2s;
        }
        .endpoint:hover { border-color: #58a6ff; }
        .method {
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            background: #1f6feb;
            color: white;
        }
        .method.get { background: #1a7f37; }
        .endpoint-path { font-size: 14px; font-family: monospace; }
        .endpoint-desc { font-size: 12px; color: #8b949e; margin-left: auto; }
        .footer { text-align: center; margin-top: 50px; color: #8b949e; font-size: 14px; }
        .footer a { color: #58a6ff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="emoji">🔍</div>
            <h1>QueryFix</h1>
            <p class="subtitle">An OpenEnv environment where AI agents learn to debug broken SQL queries across syntax, semantic, and logical error categories.</p>
            <div class="badges">
                <span class="badge">⚡ OpenEnv Compliant</span>
                <span class="badge">🗄️ SQLite Powered</span>
                <span class="badge">🤖 20 SQL Queries</span>
                <span class="badge">📊 6 Bug Categories</span>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">20</div>
                <div class="stat-label">Hand-crafted Queries</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">0.839</div>
                <div class="stat-label">Baseline Score (avg)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">6</div>
                <div class="stat-label">Bug Categories</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Baseline Performance</h2>
            <div class="tasks">
                <div class="task-card">
                    <div class="task-title easy">Easy</div>
                    <div class="task-score easy">1.000</div>
                    <div class="task-meta">5 queries · 5 steps</div>
                    <div class="task-meta">Syntax errors & typos</div>
                </div>
                <div class="task-card">
                    <div class="task-title medium">Medium</div>
                    <div class="task-score medium">0.868</div>
                    <div class="task-meta">7 queries · 11 steps</div>
                    <div class="task-meta">JOIN & aggregate bugs</div>
                </div>
                <div class="task-card">
                    <div class="task-title hard">Hard</div>
                    <div class="task-score hard">0.650</div>
                    <div class="task-meta">8 queries · 12 steps</div>
                    <div class="task-meta">Silent logic bugs</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🔌 API Endpoints</h2>
            <div class="endpoints">
                <a class="endpoint" href="/docs">
                    <span class="method get">GET</span>
                    <span class="endpoint-path">/docs</span>
                    <span class="endpoint-desc">Interactive docs</span>
                </a>
                <a class="endpoint" href="/health">
                    <span class="method get">GET</span>
                    <span class="endpoint-path">/health</span>
                    <span class="endpoint-desc">Health check</span>
                </a>
                <a class="endpoint" href="/tasks">
                    <span class="method get">GET</span>
                    <span class="endpoint-path">/tasks</span>
                    <span class="endpoint-desc">List all tasks</span>
                </a>
                <a class="endpoint" href="/schema">
                    <span class="method get">GET</span>
                    <span class="endpoint-path">/schema</span>
                    <span class="endpoint-desc">Action & observation schema</span>
                </a>
                <div class="endpoint">
                    <span class="method">POST</span>
                    <span class="endpoint-path">/reset</span>
                    <span class="endpoint-desc">Start episode</span>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span>
                    <span class="endpoint-path">/step</span>
                    <span class="endpoint-desc">Submit fix</span>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span>
                    <span class="endpoint-path">/grader</span>
                    <span class="endpoint-desc">Get score</span>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span>
                    <span class="endpoint-path">/baseline</span>
                    <span class="endpoint-desc">Run baseline agent</span>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>Built for the <strong>Meta PyTorch × Hugging Face OpenEnv Hackathon</strong></p>
            <p style="margin-top: 8px;">
                <a href="/docs">API Docs</a> · 
                <a href="https://huggingface.co/spaces/Shashwat1306/queryfix-env">HF Space</a> ·
                <a href="/tasks">View Tasks</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
