"""
Inference Script for QueryFix SQL Query Debugger OpenEnv Environment
=====================================================================
MANDATORY environment variables:
    HF_TOKEN       Your Hugging Face / API key (also accepts API_KEY)
    API_BASE_URL   The API endpoint for the LLM (default: https://aipipe.org/openai/v1)
    MODEL_NAME     The model identifier (default: gpt-4o-mini)
    BASE_URL       The environment server URL (default: http://localhost:7860)
"""

import os
import requests
from typing import List, Optional
from openai import OpenAI

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
BASE_URL = os.getenv("BASE_URL", "http://localhost:7860")
BENCHMARK = "queryfix-sql-debugger"
SUCCESS_SCORE_THRESHOLD = 0.5

SYSTEM_PROMPT = """You are a SQL debugging expert. You will be given a broken SQL query along with:
- The database schema
- The error message (if any)  
- A hint about the expected output

Your job is to return ONLY the corrected SQL query, with no explanation, no markdown, no code fences.
Just the raw SQL string."""


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def get_fixed_query(client: OpenAI, current_query: dict) -> str:
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
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return ""


def run_task(client: OpenAI, task_id: str) -> None:
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        reset_response = requests.post(
            f"{BASE_URL}/reset",
            json={"task_id": task_id},
            timeout=30
        )
        reset_response.raise_for_status()
        obs = reset_response.json()
        done = obs.get("done", False)
        step = 0

        while not done:
            step += 1
            current_query = obs["current_query"]
            query_id = current_query["query_id"]

            # Get fix from LLM
            fixed_query = get_fixed_query(client, current_query)

            # Step environment
            error = None
            try:
                step_response = requests.post(
                    f"{BASE_URL}/step",
                    json={
                        "query_id": query_id,
                        "fixed_query": fixed_query
                    },
                    timeout=30
                )
                step_response.raise_for_status()
                step_result = step_response.json()

                obs = step_result["observation"]
                reward = step_result["reward"]["value"]
                done = step_result["done"]
                error = step_result.get("info", {}).get("execution_error")

            except Exception as e:
                reward = 0.0
                done = True
                error = str(e)

            rewards.append(reward)
            steps_taken = step

            # Truncate fixed_query for log (no newlines allowed in [STEP] line)
            action_log = fixed_query.replace("\n", " ").strip()[:100]

            log_step(step=step, action=action_log, reward=reward, done=done, error=error)

        # Get final score from grader
        try:
            grader_response = requests.post(f"{BASE_URL}/grader", timeout=30)
            if grader_response.status_code == 200:
                score = grader_response.json()["score"]
            else:
                score = sum(rewards) / len(rewards) if rewards else 0.0
        except Exception:
            score = sum(rewards) / len(rewards) if rewards else 0.0

        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Task {task_id} failed: {e}", flush=True)
        score = 0.0
        success = False

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


def main() -> None:
    if not API_KEY:
        raise EnvironmentError(
            "API key not set. Set HF_TOKEN or API_KEY environment variable."
        )

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    for task_id in ["easy", "medium", "hard"]:
        run_task(client, task_id)


if __name__ == "__main__":
    main()
