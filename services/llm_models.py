"""Pydantic-Modelle für strukturierte LLM-Antworten."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParentReport(BaseModel):
    """Struktur für Elternberichte."""

    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class ContractClause(BaseModel):
    """Eine einzelne Vertragsklausel."""

    heading: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ContractClausesResponse(BaseModel):
    """Sammlung von Vertragsklauseln."""

    clauses: list[ContractClause] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    """Generische Zusammenfassung."""

    summary: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)


class TodoItem(BaseModel):
    """Ein To-do-Eintrag."""

    task: str = Field(min_length=1)
    owner: str | None = None
    due_date: str | None = None


class TodoListResponse(BaseModel):
    """To-do-Liste mit strukturierten Einträgen."""

    todos: list[TodoItem] = Field(default_factory=list)
