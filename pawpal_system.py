from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


# ------------------------------------------------------------------
# Task
# A single pet care activity with scheduling metadata.
# ------------------------------------------------------------------

@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str        # "low", "medium", or "high"
    frequency: str       # "daily", "weekly", or "as-needed"
    completed: bool = False
    reason_skipped: str = ""   # filled in by Scheduler when task is deferred

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def is_high_priority(self) -> bool:
        """Return True if the task's priority is high."""
        return self.priority == "high"

    def __repr__(self) -> str:
        """Return a compact string representation of the task."""
        status = "done" if self.completed else "pending"
        return f"Task('{self.title}', {self.duration_minutes}min, {self.priority}, {self.frequency}, {status})"


# ------------------------------------------------------------------
# Pet
# Stores pet details and owns a list of Tasks.
# ------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove a task by title (removes first match)."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that have not been marked completed."""
        return [t for t in self.tasks if not t.completed]


# ------------------------------------------------------------------
# Owner
# Manages one or more pets and exposes their tasks to the Scheduler.
# ------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    available_minutes: int
    pets: list[Pet] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        """Remove a pet by name (removes first match)."""
        self.pets = [p for p in self.pets if p.name != name]

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all pets (completed and pending)."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.tasks)
        return tasks

    def get_all_pending_tasks(self) -> list[Task]:
        """Return only pending tasks across all pets."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.get_pending_tasks())
        return tasks


# ------------------------------------------------------------------
# DayPlan
# The output of one scheduling run for a specific pet.
# ------------------------------------------------------------------

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class DayPlan:
    owner: Owner
    pet: Pet
    scheduled_tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    date: date = field(default_factory=date.today)

    def total_duration(self) -> int:
        """Total minutes consumed by scheduled tasks."""
        return sum(t.duration_minutes for t in self.scheduled_tasks)

    def explain(self) -> str:
        """Human-readable summary of what was planned and why."""
        lines = [
            f"Plan for {self.pet.name} ({self.pet.species}) - {self.date}",
            f"Owner: {self.owner.name} | Available: {self.owner.available_minutes} min\n",
        ]

        if self.scheduled_tasks:
            lines.append("Scheduled:")
            for task in self.scheduled_tasks:
                lines.append(
                    f"  [x] {task.title} - {task.duration_minutes} min [{task.priority} priority]"
                )
        else:
            lines.append("No tasks could be scheduled.")

        if self.skipped_tasks:
            lines.append("\nSkipped:")
            for task in self.skipped_tasks:
                reason = task.reason_skipped or "reason unknown"
                lines.append(f"  [ ] {task.title} - {reason}")

        lines.append(
            f"\nTotal: {self.total_duration()} / {self.owner.available_minutes} min used"
        )
        return "\n".join(lines)

    def summary(self) -> list[dict]:
        """Machine-friendly list of scheduled tasks (for Streamlit tables, etc.)."""
        return [
            {
                "title": t.title,
                "duration_minutes": t.duration_minutes,
                "priority": t.priority,
                "frequency": t.frequency,
                "status": "scheduled",
            }
            for t in self.scheduled_tasks
        ]


# ------------------------------------------------------------------
# Scheduler
# The "brain": retrieves tasks from Owner's pets, sorts by priority,
# and greedily fits tasks into the available time window.
#
# How Scheduler talks to Owner to get pet data:
#   - For a single pet:  pet.get_pending_tasks()
#   - Across all pets:   owner.get_all_pending_tasks()
# ------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        """Initialise the scheduler with the owner whose pets will be planned."""
        self.owner = owner

    def build_plan(self, pet: Pet) -> DayPlan:
        """Sort a pet's pending tasks by priority and fit them into the owner's available time."""
        plan = DayPlan(owner=self.owner, pet=pet)
        remaining = self.owner.available_minutes
        sorted_tasks = self._sort_by_priority(pet.get_pending_tasks())

        for task in sorted_tasks:
            if self._fits_in_time(task, remaining):
                plan.scheduled_tasks.append(task)
                remaining -= task.duration_minutes
            else:
                task.reason_skipped = (
                    f"only {remaining} min left, needs {task.duration_minutes} min"
                )
                plan.skipped_tasks.append(task)

        return plan

    def build_all_plans(self) -> list[DayPlan]:
        """Build a DayPlan for every pet the owner has."""
        return [self.build_plan(pet) for pet in self.owner.pets]

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low."""
        return sorted(tasks, key=lambda t: _PRIORITY_RANK.get(t.priority, 99))

    def _fits_in_time(self, task: Task, remaining: int) -> bool:
        """True if the task fits within the remaining available minutes."""
        return task.duration_minutes <= remaining
