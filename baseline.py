
#!/usr/bin/env python3
"""
Baseline inference script for SQL Query Debugger OpenEnv.
Uses OpenAI API to run an LLM agent against all 3 tasks.

Usage:
  OPENAI_API_KEY=sk-... python baseline.py

Environment variables:
  OPENAI_API_KEY   — required
  OPENAI_MODEL     — optional, defaults to 'gpt-4o-mini'
  BASE_URL         — optional, defaults to 'http://localhost:8000'
"""

import os
import sys
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
MODEL = os.getenv("OPENAI_MODEL") or "Qwen/Qwen2.5-72B-Instruct"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or "https://router.huggingface.co/v1" # For AIPipe or custom endpoints

SYSTEM_PROMPT = """You are a SQL debugging expert. You will be given a broken SQL query along with:
- The database schema
- The error message (if any)
- A hint about the expected output

Your job is to return ONLY the corrected SQL query, with no explanation, no markdown, no code fences.
Just the raw SQL string."""


def run_task(task_id: str, client: OpenAI) -> float:
    """
    Run the baseline agent on a single task.
    
    Args:
        task_id: Task to run ('easy', 'medium', or 'hard')
        client: OpenAI client instance
        
    Returns:
        Final score for the task
    """
    print(f"\n{'='*60}")
    print(f"Running task: {task_id}")
    print(f"{'='*60}")
    
    # Reset environment
    try:
        response = requests.post(f"{BASE_URL}/reset", json={"task_id": task_id})
        response.raise_for_status()
        obs = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error resetting environment: {e}")
        return 0.0
    
    step_num = 0
    done = False
    
    while not done:
        step_num += 1
        
        # Get current query info
        current_query = obs["current_query"]
        print(f"\n--- Query {current_query['query_id']} (Step {step_num}) ---")
        print(f"Broken query: {current_query['broken_query'][:100]}...")
        print(f"Error: {current_query['error_message'][:80]}...")
        print(f"Attempts: {current_query['attempts_used']}/{current_query['max_attempts']}")
        
        # Build prompt
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
            
            # Clean up any markdown code fences if model added them
            if fixed_query.startswith("```"):
                lines = fixed_query.split("\n")
                # Remove first and last lines if they're code fences
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                fixed_query = "\n".join(lines).strip()
            
            print(f"Fixed query: {fixed_query[:100]}...")
            
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return 0.0
        
        # Step environment
        try:
            response = requests.post(f"{BASE_URL}/step", json={
                "query_id": current_query["query_id"],
                "fixed_query": fixed_query
            })
            response.raise_for_status()
            step_result = response.json()
            
            obs = step_result["observation"]
            reward = step_result["reward"]
            done = step_result["done"]
            
            print(f"Reward: {reward['value']:.2f} - {reward['reason']}")
            print(f"Score so far: {obs['episode_score_so_far']:.3f}")
            
        except requests.exceptions.RequestException as e:
            print(f"Error stepping environment: {e}")
            return 0.0
    
    # Get final grader score
    try:
        response = requests.post(f"{BASE_URL}/grader")
        response.raise_for_status()
        grader_result = response.json()
        score = grader_result["score"]
        
        print(f"\n{'='*60}")
        print(f"Task {task_id} complete!")
        print(f"Final score: {score:.3f}")
        print(f"{'='*60}")
        
        return score
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting grader score: {e}")
        return 0.0


def main():
    """Main entry point for baseline script."""
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print("  OPENAI_API_KEY=sk-... python baseline.py", file=sys.stderr)
        sys.exit(1)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: Cannot connect to server at {BASE_URL}", file=sys.stderr)
        print(f"Make sure the server is running: uvicorn app.main:app --host 0.0.0.0 --port 8000", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n{'#'*60}")
    print(f"# SQL Query Debugger - Baseline Agent")
    print(f"{'#'*60}")
    print(f"Model: {MODEL}")
    print(f"Base URL: {BASE_URL}")
    if OPENAI_BASE_URL:
        print(f"OpenAI Base URL: {OPENAI_BASE_URL}")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)
    
    # Run all tasks
    scores = {}
    for task_id in ["easy", "medium", "hard"]:
        try:
            score = run_task(task_id, client)
            scores[task_id] = score
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            sys.exit(0)
        except Exception as e:
            print(f"Unexpected error running task {task_id}: {e}")
            scores[task_id] = 0.0
    
    # Print summary
    print(f"\n\n{'#'*60}")
    print(f"# Baseline Results Summary")
    print(f"{'#'*60}")
    print(f"  {'Task':<10} {'Score':>10}")
    print(f"  {'-'*10} {'-'*10}")
    for task_id, score in scores.items():
        print(f"  {task_id:<10} {score:>10.3f}")
    print(f"  {'-'*10} {'-'*10}")
    avg_score = sum(scores.values()) / len(scores)
    print(f"  {'Average':<10} {avg_score:>10.3f}")
    print(f"{'#'*60}\n")
    
    return scores


if __name__ == "__main__":
    main()
