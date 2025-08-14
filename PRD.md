PRD: Parallel Research Assistant (MVP)

1. Problem & Goals

• Problem: Users need a concise, actionable plan that requires pulling info from multiple sources. Doing that
manually is slow; single-agent systems are sequential and slow.
• Goal: Create an orchestrator that breaks a prompt into tasks, runs agents in parallel with web access, and
returns a clear, cited summary.

2. Users & Personas

• Primary: Hackathon judges and general users who enter a research-style query in a single text box.
• Secondary: Developers wanting an example of orchestrated, parallel agent workflows.

3. Scope (MVP)

• In-scope
• Streamlit UI: single text prompt input + generated plan output.
• Orchestrator uses Gemini Flash to:
• Understand intent.
• Produce 1–3 tasks max for MVP.
• Save tasks as Markdown via MCP Filesystem.
• Spawn N workers (1–3) using browser-use to browse and gather results concurrently.
• Workers update their own task Markdown with findings and sources.
• Orchestrator aggregates outputs into a final, concise summary with citations.
• Travel demo preset: “Find flights,” “Find accommodation,” “Draft itinerary” (2–3 tasks).
• Out-of-scope (MVP)
• Authentication, multi-user sessions, databases.
• Payment, persistence beyond local files.
• Full-blown tool ecosystems, plugins, or continuous monitoring.

4. Success Metrics

• Functional
• ≥2 tasks created and run in parallel for the travel prompt.
• Workers write findings back to the task files with at least 3 citations total.
• Final response returned in ≤60–120 seconds for a simple query.
• UX
• Single-screen flow; visible progress states; easy to re-run.
• Output includes an actionable plan and links.

5. User Stories

• As a user, I can enter a travel plan prompt and receive a concise, step-by-step plan with links.
• As a user, I can see progress states: task creation → agents running → results → summary.
• As a user, I can download or view the generated task Markdown files.

6. Key Functional Requirements

• FR-1: Accept prompt via Streamlit and trigger orchestration.
• FR-2: Use Gemini Flash to produce a normalized task list (title, objective, constraints, acceptance criteria).
• FR-3: Create each task as a Markdown file via MCP Filesystem (or local FS fallback).
• FR-4: Spawn 1 worker per task with browser-use, each with its own browser context.
• FR-5: Workers update the corresponding task file with progress, findings, and citations.
• FR-6: Orchestrator watches for completion or timeout; then generates a final summary using Gemini Flash.
• FR-7: Show progress and final output in Streamlit; link to local task files.

7. Non-Functional Requirements

• Performance: Parallel tasks via asyncio; timebox each worker (e.g., 45–90s).
• Reliability: If a worker fails, mark task as blocked and proceed with partial results.
• Security: Do not execute arbitrary code; sandbox browsing; redact secrets in logs.
• Observability: Simple console logs + status chips in UI; optional JSON logs.
• Portability: Mac-friendly; minimal external services besides Gemini.

8. Constraints & Assumptions

• Gemini Flash is available via google-generativeai or Vertex AI.
• browser-use works headless via Playwright; Chromium installed.
• MCP Filesystem server available; if not, fallback to local filesystem while keeping the same task file schema.

9. Risks & Mitigations

• Browser automation flakiness: Use shorter deterministic paths; strict timeouts and retries.
• Sites blocking automation: Prefer public sources; fail softly with partial results.
• Time overrun: Cap tasks at 2–3; simplify scraping to page titles/snippets/links.

10. Acceptance Criteria

• Entering a travel prompt produces:
• 2–3 Markdown task files with structured headers.
• Parallel worker activity evidenced by timestamps and different agents writing to different files.
• A final summarized plan with 3+ linked sources.
• All within a single Streamlit session; no manual CLI steps during demo.

11. Demo Script (5 minutes)

• Open Streamlit, input: “Trip to Tokyo, 5 days in Nov, budget $1500.”
• Show created tasks in UI with links to files.
• Show live statuses (e.g., “Finding flights…”, “Finding stays…”).
• Display final summary with a compact itinerary and links.
• Open a task Markdown to show worker notes and citations.

---

Task & Protocol Specifications

Task Markdown schema (MVP)

     1 │ # Task: {title}
     2 │ id: {uuid}
     3 │ status: todo | in_progress | done | blocked
     4 │ owner: {agent_id}
     5 │ created: {ISO8601}
     6 │ updated: {ISO8601}
     7 │
     8 │ objective: >
     9 │   One-sentence task goal.
    10 │
    11 │ inputs:
    12 │ - key: value
    13 │
    14 │ constraints:
    15 │ - brief constraint 1
    16 │ - brief constraint 2
    17 │
    18 │ plan:
    19 │ - [ ] step 1
    20 │ - [ ] step 2
    21 │
    22 │ progress_log:
    23 │ - {ISO8601} - created
    24 │ - {ISO8601} - started
    25 │ - {ISO8601} - note...
    26 │
    27 │ findings:
    28 │ - item: brief finding
    29 │   url: https://example.com
    30 │   snippet: short supporting text
    31 │
    32 │ citations:
    33 │ - https://example.com/page1
    34 │ - https://example.com/page2
    35 │
    36 │ summary: >
    37 │   2–5 sentences summarizing findings and recommendations.

Minimal Agent2Agent protocol (file- and message-based)

• Message types
• assignment (from orchestrator to worker): includes task_path, objective, constraints, acceptance_criteria,
time_budget_s.
• status_update (from worker to orchestrator): status, notes.
• completion (from worker): final summary, citations.
• Transport
• MVP: filesystem + in-process queue. Orchestrator holds worker handles; workers write to task Markdown and emit
in-memory events.
• State
• Single source of truth is the task Markdown. Orchestrator also keeps a lightweight in-memory registry.

---

Top-Level System Architecture

Components

• Streamlit UI
• Prompt input, “Run” button, progress badges, final output, links to tasks.
• Orchestrator
• Intent understanding and task decomposition (Gemini).
• Task file creation via MCP Filesystem (or FS fallback).
• Worker lifecycle management (spawn, monitor, timeouts).
• Aggregation and final summary (Gemini).
• Worker Agent(s)
• One per task; browser-use driven browsing and extraction.
• Writes progress_log, findings, citations to its task file.
• Task Store
• MCP Filesystem abstraction; interface: create_task, update_task, read_task, list_tasks.
• LLM Client
• Gemini Flash wrapper with prompting utilities and safety settings.
• Concurrency Layer
• asyncio tasks with per-worker time budgets.

Data Flow (happy path)

1. User submits prompt in Streamlit.
2. Orchestrator calls Gemini to produce 2–3 normalized tasks.
3. Orchestrator creates Markdown files for each task via Task Store (MCP FS).
4. Orchestrator spawns workers (async) passing task_id and task_path.
5. Each worker uses browser-use to browse; periodically updates its task file.
6. Workers complete or time out; orchestrator detects completion states.
7. Orchestrator reads all task files, asks Gemini for final summary and plan.
8. Streamlit renders final plan with citations and links to task files.

Sequence (textual)

• UI → Orchestrator: start(prompt)
• Orchestrator → LLM: decompose(prompt) → tasks
• Orchestrator → Task Store: create files
• Orchestrator → Workers: run(task_x)
• Workers → web (browser-use): fetch, extract
• Workers → Task Store: append progress/findings
• Orchestrator ← Workers: completion/timeouts
• Orchestrator → LLM: summarize(all_tasks)
• Orchestrator → UI: final_result

Interfaces (high-level)

• TaskStore.create(task: TaskMeta) -> path
• TaskStore.append_progress(task_id, entry)
• TaskStore.append_finding(task_id, finding)
• TaskStore.update_status(task_id, status)
• LLM.decompose(prompt) -> List[TaskMeta]
• LLM.summarize(task_docs) -> str
• Worker.run(task_path, time_budget_s) -> Completion

Tech Stack

• Python 3.11+
• Streamlit for UI
• Google Gemini Flash (via google-generativeai or Vertex AI SDK)
• browser-use + Playwright (Chromium)
• MCP Filesystem server; Python adapter client (fallback: local FS)
• asyncio for concurrency
• pydantic (optional) for data models

Deployment & Config

• Local run via streamlit run app.py
• Env vars: GOOGLE_API_KEY, BROWSER_USE_HEADLESS=1
• Playwright install step (playwright install chromium)
• If MCP FS not reachable, log warning and write to ./tasks/

Minimal repo structure

• app/
• ui.py (Streamlit)
• orchestrator.py
• workers.py
• llm.py
• task_store.py (MCP FS + fallback)
• schemas.py
• tasks/ (generated)
• requirements.txt
• .env.example

Observability

• Console logs per worker with task IDs.
• Streamlit status badges per task: todo/in_progress/done/blocked.
• Optional JSON logs to ./run_logs/.

Safety & Guardrails

• Limit pages visited and depth (e.g., 3 pages per task).
• Restrict domains if needed; strip PII; do not execute downloaded code.
• Respect robots.txt where feasible.

Stretch goals (post-MVP)

• Cache results.
• Retry with alternative sources when blocked.
• Richer UI with task-by-task panels.
• Export full report as PDF/Markdown bundle.

---

Build Time Plan (fits ~2 hours)

• 0:00–0:20 Scaffolding, env, Streamlit input/output.
• 0:20–0:45 LLM task decomposition + Task Store (local FS fallback).
• 0:45–1:20 Worker with browser-use and file updates; parallel via asyncio.
• 1:20–1:40 Aggregation summarizer.
• 1:40–2:00 Polish UI and demo flow; add travel preset.
• Key cuts if behind: limit to 2 tasks; shorten worker time budgets; reduce extraction to titles + first paragraph + link.

---

• Implementing this will yield a crisp demo: you type a trip query, see tasks created, watch parallel workers
browse and update Markdown files, then receive a clean plan with citations.
