"""
FastAPI application for SQL Query Debugger OpenEnv.
Implements all required endpoints.
"""

import os
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx

from app.models import (
    Action, Observation, Reward, ResetRequest, 
    EpisodeState, GraderResponse, TaskInfo, BaselineResponse
)
from app.environment import SQLDebuggerEnvironment
from app.tasks import task_easy, task_medium, task_hard


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
async def reset(request: ResetRequest):
    """
    Reset the environment for a new episode.
    
    Args:
        request: ResetRequest with task_id
        
    Returns:
        Initial Observation
    """
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
                    scores[task_id] = 0.0
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
                        scores[task_id] = 0.0
                        done = True
                        break
                
                # Get grader score
                if done:
                    grader_response = await http_client.post(f"{BASE_URL}/grader")
                    if grader_response.status_code == 200:
                        scores[task_id] = grader_response.json()["score"]
                    else:
                        scores[task_id] = 0.0
        
        return BaselineResponse(
            easy=scores.get("easy", 0.0),
            medium=scores.get("medium", 0.0),
            hard=scores.get("hard", 0.0),
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
@app.get("/")
async def root():
    """Root endpoint with environment information."""
    return {
        "name": "SQL Query Debugger",
        "version": "1.0.0",
        "description": "An OpenEnv environment where AI agents debug broken SQL queries",
        "endpoints": {
            "health": "GET /health",
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state",
            "tasks": "GET /tasks",
            "grader": "POST /grader",
            "baseline": "POST /baseline"
        }
    }
