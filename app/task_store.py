from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Iterable
import yaml

from .schemas import TaskModel, TaskStatus, Finding


class TaskStore:
    def __init__(self, base_dir: str | Path = "tasks") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        return self.base_dir / f"{task_id}.md"

    def create_task(self, task: TaskModel) -> Path:
        path = self._task_path(task.id)
        content = self._render_task(task)
        path.write_text(content, encoding="utf-8")
        return path

    def read_task_text(self, task_id: str) -> str:
        return self._task_path(task_id).read_text(encoding="utf-8")

    def list_task_paths(self) -> list[Path]:
        return sorted(self.base_dir.glob("*.md"))

    def update_status(self, task: TaskModel, status: TaskStatus) -> None:
        task.status = status
        task.touch()
        self._rewrite(task)

    def append_progress(self, task: TaskModel, note: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        task.progress_log.append(f"{timestamp} - {note}")
        task.touch()
        self._rewrite(task)

    def append_finding(self, task: TaskModel, finding: Finding) -> None:
        task.findings.append(finding)
        if finding.url and finding.url not in task.citations:
            task.citations.append(finding.url)
        task.touch()
        self._rewrite(task)

    def set_summary(self, task: TaskModel, summary: str) -> None:
        task.summary = summary
        task.touch()
        self._rewrite(task)

    def _rewrite(self, task: TaskModel) -> None:
        path = self._task_path(task.id)
        path.write_text(self._render_task(task), encoding="utf-8")

    def _render_task(self, task: TaskModel) -> str:
        header = {
            "id": task.id,
            "status": task.status.value,
            "owner": task.owner,
            "created": task.created.isoformat(),
            "updated": task.updated.isoformat(),
            "title": task.title,
            "objective": task.objective,
            "inputs": task.inputs,
            "constraints": task.constraints,
            "plan": task.plan_steps,
        }
        # Render YAML-like header followed by sections
        header_yaml = yaml.safe_dump(header, sort_keys=False).strip()
        progress_lines = "\n".join(f"- {e}" for e in task.progress_log)
        findings_lines = "\n".join(
            f"- item: {f.item}\n  url: {f.url or ''}\n  snippet: {f.snippet or ''}" for f in task.findings
        )
        citations_lines = "\n".join(f"- {u}" for u in task.citations)
        summary_block = task.summary or ""
        body = (
            f"---\n{header_yaml}\n---\n\n"
            f"## Progress\n{progress_lines or '- created'}\n\n"
            f"## Findings\n{findings_lines or ''}\n\n"
            f"## Citations\n{citations_lines or ''}\n\n"
            f"## Summary\n{summary_block}\n"
        )
        return body


class MCPTaskStore(TaskStore):
    # Placeholder for MCP Filesystem integration; same public API as TaskStore.
    def __init__(self, base_dir: str | Path = "tasks") -> None:
        super().__init__(base_dir)
        # In MVP we fallback to local FS; integrating an MCP client can be done later.
