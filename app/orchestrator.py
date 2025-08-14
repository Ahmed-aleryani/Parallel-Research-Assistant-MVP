from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import List, Optional
import re

from .schemas import TaskModel, TaskStatus
from .task_store import TaskStore
from .llm import GeminiClient
from .workers import run_worker


def _make_task_model(raw: dict) -> TaskModel:
    task_id = str(uuid.uuid4())
    title = raw.get("title") or "Task"
    objective = raw.get("objective") or title
    constraints = list(raw.get("constraints") or [])
    return TaskModel(
        id=task_id,
        title=title,
        objective=objective,
        constraints=constraints,
        plan_steps=["Search the web", "Record findings", "Summarize"],
    )


async def _run_workers_for_tasks(tasks: List[TaskModel], store: TaskStore, use_browser: bool) -> List[TaskModel]:
    coros = [run_worker(t, store, time_budget_s=60, use_browser=use_browser) for t in tasks]
    results = await asyncio.gather(*coros)
    return results


def orchestrate(prompt: str, use_browser: bool = False, model_name: Optional[str] = None) -> dict:
    # Try to create LLM; fall back to heuristic decomposition if unavailable
    llm: Optional[GeminiClient]
    try:
        llm = GeminiClient(model_name=model_name)
    except Exception:
        llm = None
    store = TaskStore()

    # 1) Decompose into tasks
    if llm is not None:
        raw_tasks = llm.decompose(prompt)
    else:
        # Simple heuristic fallback for demo if Gemini is unavailable
        lower = prompt.lower()
        raw_tasks: List[dict]
        if any(k in lower for k in ["trip", "travel", "flight", "hotel", "itinerary"]):
            raw_tasks = [
                {"title": "Find flights", "objective": f"Find flight options: {prompt}", "constraints": ["Use reputable travel sites", "Include 2+ options"]},
                {"title": "Find accommodation", "objective": f"Find stays/lodging: {prompt}", "constraints": ["Include prices", "Provide booking links"]},
                {"title": "Draft itinerary", "objective": f"Draft a concise itinerary: {prompt}", "constraints": ["Daily highlights", "Top attractions"]},
            ]
        else:
            raw_tasks = [
                {"title": "Research key information", "objective": prompt, "constraints": ["Include 3+ citations"]}
            ]
    task_models: List[TaskModel] = [_make_task_model(rt) for rt in raw_tasks]

    # 2) Create task files
    for t in task_models:
        store.create_task(t)
        store.append_progress(t, "created")

    # 3) Run workers in parallel
    asyncio.run(_run_workers_for_tasks(task_models, store, use_browser))

    # 4) Aggregate and summarize
    combined_docs: List[str] = []
    for t in task_models:
        text = store.read_task_text(t.id)
        combined_docs.append(f"# Task {t.title}\n\n" + text)
    combined = "\n\n---\n\n".join(combined_docs)
    if llm is not None:
        final_summary = llm.summarize(combined)
    else:
        # Minimal fallback summary
        final_summary = (
            "Summary (fallback):\n\n" + combined[:1500] + ("..." if len(combined) > 1500 else "")
        )

    return {
        "tasks": task_models,
        "task_paths": [str(Path("tasks") / f"{t.id}.md") for t in task_models],
        "final_summary": final_summary,
    }
