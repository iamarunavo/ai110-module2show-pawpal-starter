from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Owner:
    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)

    def set_available_minutes(self, _minutes: int) -> None:
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int
    owner: Owner

    def get_species(self) -> str:
        pass


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str  # "low", "medium", or "high"
    completed: bool = False

    def is_high_priority(self) -> bool:
        pass

    def __repr__(self) -> str:
        pass


@dataclass
class DayPlan:
    scheduled_tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    date: date = field(default_factory=date.today)

    def total_duration(self) -> int:
        pass

    def explain(self) -> str:
        pass

    def summary(self) -> list[dict]:
        pass


class Scheduler:
    def __init__(self, owner: Owner, pet: Pet) -> None:
        self.owner = owner
        self.pet = pet

    def build_plan(self, tasks: list[Task]) -> DayPlan:
        pass

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        pass

    def _fits_in_time(self, task: Task, remaining: int) -> bool:
        pass
