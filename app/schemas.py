from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Finding(BaseModel):
    item: str
    url: Optional[str] = None
    snippet: Optional[str] = None


class TaskModel(BaseModel):
    id: str
    title: str
    objective: str
    status: TaskStatus = TaskStatus.TODO
    owner: Optional[str] = None
    created: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated: datetime = Field(default_factory=lambda: datetime.utcnow())
    inputs: dict = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    plan_steps: List[str] = Field(default_factory=list)
    progress_log: List[str] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    summary: Optional[str] = None

    def touch(self) -> None:
        self.updated = datetime.utcnow()
