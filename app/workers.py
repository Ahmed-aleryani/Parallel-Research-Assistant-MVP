from __future__ import annotations

import asyncio
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from .schemas import TaskModel, Finding, TaskStatus
from .task_store import TaskStore

try:
    # Optional dependency; will be used if available
    from duckduckgo_search import DDGS  # type: ignore
except Exception:  # pragma: no cover
    DDGS = None  # type: ignore

try:  # Optional browser-use integration
    from browser_use.agent import Agent  # type: ignore
    from browser_use.browser import Browser  # type: ignore
except Exception:  # pragma: no cover
    Agent = None  # type: ignore
    Browser = None  # type: ignore


async def gather_web_findings(query: str, max_results: int = 3) -> List[Finding]:
    findings: List[Finding] = []
    if DDGS is None:
        return findings
    # Run in thread to avoid blocking
    def _search() -> List[Finding]:
        results: List[Finding] = []
        with DDGS() as ddgs:
            for idx, r in enumerate(ddgs.text(query, max_results=max_results)):
                title = r.get("title") or r.get("source") or "Result"
                href = r.get("href") or r.get("url")
                snippet = r.get("body") or r.get("snippet") or ""
                results.append(Finding(item=title, url=href, snippet=snippet))
        return results

    findings = await asyncio.to_thread(_search)
    return findings


async def run_worker(task: TaskModel, store: TaskStore, time_budget_s: int = 60, use_browser: bool = False) -> TaskModel:
    store.update_status(task, TaskStatus.IN_PROGRESS)
    store.append_progress(task, f"Worker started with budget {time_budget_s}s")

    # For MVP we simply search the objective
    try:
        search_query = task.objective or task.title
        results: List[Finding] = []

        if use_browser and Agent is not None and Browser is not None:
            # Attempt minimal browser-use workflow
            try:
                browser = Browser()
                agent = Agent(browser=browser)
                scenario = (
                    f"Research: {search_query}. Find 3-5 authoritative sources with brief snippets. Return links."
                )
                # Many implementations of browser-use are async
                agent_result = await asyncio.wait_for(agent.run(scenario, max_steps=8), timeout=time_budget_s)
                # Best-effort extraction from agent_result
                urls = []
                texts = []
                for key in ["links", "urls", "sources"]:
                    maybe = getattr(agent_result, key, None)
                    if isinstance(maybe, list):
                        urls.extend([str(u) for u in maybe if u])
                final_text = getattr(agent_result, "final_result", None) or getattr(agent_result, "result", None)
                if isinstance(final_text, str):
                    texts.append(final_text)
                for u in urls[:5]:
                    results.append(Finding(item="Source", url=u, snippet=(texts[0] if texts else None)))
                store.append_progress(task, f"browser-use collected {len(results)} links")
            except Exception as be:  # fall back to DDG
                store.append_progress(task, f"browser-use failed, fallback to search: {be}")

        if not results:
            # Fallback to DDG text search
            results = await asyncio.wait_for(gather_web_findings(search_query, max_results=5), timeout=time_budget_s)

        for f in results:
            store.append_finding(task, f)
        store.append_progress(task, f"Collected {len(results)} findings")
        # Naive summary from top findings
        if results:
            top = results[:3]
            summary_lines = [f"- {f.item} ({f.url})" for f in top if f.url]
            store.set_summary(task, "\n".join(summary_lines))
        store.update_status(task, TaskStatus.DONE)
    except asyncio.TimeoutError:
        store.append_progress(task, "Timed out")
        store.update_status(task, TaskStatus.BLOCKED)
    except Exception as exc:  # pragma: no cover - robust against runtime surprises
        store.append_progress(task, f"Error: {exc}")
        store.update_status(task, TaskStatus.BLOCKED)

    return task
