from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta


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
    time: str = ""             # scheduled start time in "HH:MM" format (optional)
    due_date: date = field(default_factory=date.today)  # when this task is next due

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return a fresh copy of this task due on its next occurrence date.

        Uses timedelta to calculate the next due date:
          - "daily"  → today + 1 day
          - "weekly" → today + 7 days
          - "as-needed" → no automatic recurrence (returns None)
        """
        if self.frequency == "daily":
            next_due = date.today() + timedelta(days=1)
        elif self.frequency == "weekly":
            next_due = date.today() + timedelta(weeks=1)
        else:
            return None  # "as-needed" tasks don't recur automatically

        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            time=self.time,
            due_date=next_due,
        )

    def is_high_priority(self) -> bool:
        """Return True if the task's priority is high."""
        return self.priority == "high"

    def __repr__(self) -> str:
        """Return a compact string representation of the task."""
        status = "done" if self.completed else "pending"
        time_str = f", @{self.time}" if self.time else ""
        return f"Task('{self.title}', {self.duration_minutes}min, {self.priority}, {self.frequency}{time_str}, {status})"


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

    def get_tasks_for_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks (completed and pending) belonging to the named pet.

        Args:
            pet_name: The exact name of the pet to look up (case-sensitive).

        Returns:
            The pet's full task list, or an empty list if no pet matches.
        """
        for pet in self.pets:
            if pet.name == pet_name:
                return pet.tasks
        return []


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
        pending    = pet.get_pending_tasks()
        non_weekly = self._sort_by_priority([t for t in pending if t.frequency != "weekly"])
        weekly     = self._sort_by_priority([t for t in pending if t.frequency == "weekly"])
        sorted_tasks = non_weekly + weekly

        for task in sorted_tasks:
            if self._fits_in_time(task, remaining):
                plan.scheduled_tasks.append(task)
                remaining -= task.duration_minutes
            else:
                if task.frequency == "weekly":
                    task.reason_skipped = (
                        f"weekly task deprioritized — only {remaining} min left, "
                        f"needs {task.duration_minutes} min"
                    )
                else:
                    task.reason_skipped = (
                        f"only {remaining} min left, needs {task.duration_minutes} min"
                    )
                plan.skipped_tasks.append(task)

        return plan

    def build_all_plans(self) -> list[DayPlan]:
        """Build a DayPlan for every pet the owner has."""
        return [self.build_plan(pet) for pet in self.owner.pets]

    def detect_conflicts(self) -> list[str]:
        """
        Return a list of warning messages for scheduling conflicts.

        Checks:
          (a) Total high-priority task time across all pets exceeds available minutes.
          (b) Any individual pet's total pending task time exceeds available minutes.
          (c) Two or more tasks (same or different pets) share the same start time.
        """
        warnings: list[str] = []
        available = self.owner.available_minutes

        all_pending = self.owner.get_all_pending_tasks()

        # (a) High-priority budget check
        high_total = sum(t.duration_minutes for t in all_pending if t.priority == "high")
        if high_total > available:
            warnings.append(
                f"Conflict: total high-priority task time ({high_total} min) "
                f"exceeds available time ({available} min) across all pets."
            )

        # (b) Per-pet budget check
        for pet in self.owner.pets:
            pet_total = sum(t.duration_minutes for t in pet.get_pending_tasks())
            if pet_total > available:
                warnings.append(
                    f"Conflict: {pet.name}'s pending tasks total {pet_total} min, "
                    f"which exceeds available time ({available} min)."
                )

        # (c) Time-slot collision check — lightweight: bucket tasks by time,
        #     flag any slot that has more than one task assigned to it.
        time_slots: dict[str, list[str]] = {}
        for pet in self.owner.pets:
            for task in pet.get_pending_tasks():
                if not task.time:
                    continue  # skip tasks with no scheduled time
                label = f"{pet.name} -> {task.title}"
                time_slots.setdefault(task.time, []).append(label)

        for slot, labels in time_slots.items():
            if len(labels) > 1:
                names = ", ".join(labels)
                warnings.append(
                    f"Conflict: multiple tasks scheduled at {slot}: {names}"
                )

        return warnings

    def mark_task_complete(self, pet: Pet, task: Task) -> Task | None:
        """Mark a task complete and automatically add the next occurrence to the pet.

        Calls task.mark_complete(), then task.next_occurrence() to compute the
        next due date using timedelta. If a next occurrence exists it is appended
        to the pet's task list so future calls to build_plan() will include it.

        Args:
            pet:  The Pet that owns the task (used to register the next occurrence).
            task: The Task to mark as done.

        Returns:
            The newly created Task for the next occurrence, or None if the task
            frequency is "as-needed" and does not repeat automatically.
        """
        task.mark_complete()
        next_task = task.next_occurrence()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by their scheduled start time in ascending HH:MM order.

        Tasks with no time set (empty string) are placed at the end.
        Sorting "HH:MM" strings lexicographically works correctly because
        the format is zero-padded and fixed-width, so alphabetical order
        equals chronological order (e.g. "08:00" < "09:30" < "14:00").
        """
        return sorted(tasks, key=lambda t: t.time if t.time else "99:99")

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks (completed and pending) belonging to the named pet.

        Delegates to Owner.get_tasks_for_pet(), giving callers a single
        Scheduler-level entry point for pet-based filtering.

        Args:
            pet_name: The exact name of the pet to filter by (case-sensitive).

        Returns:
            The pet's full task list, or an empty list if the name is not found.
        """
        return self.owner.get_tasks_for_pet(pet_name)

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low; shortest duration first within each tier."""
        return sorted(tasks, key=lambda t: (_PRIORITY_RANK.get(t.priority, 99), t.duration_minutes))

    def _fits_in_time(self, task: Task, remaining: int) -> bool:
        """True if the task fits within the remaining available minutes."""
        return task.duration_minutes <= remaining

    def filter_tasks(self, tasks: list[Task], status: str | None = None) -> list[Task]:
        """Filter a task list by completion status.

        Args:
            tasks:  The list of Task objects to filter. Can be any task list —
                    e.g. from owner.get_all_tasks() or owner.get_tasks_for_pet().
            status: The completion status to keep. Accepted values:
                      - "pending"   → returns tasks where completed is False
                      - "completed" → returns tasks where completed is True
                      - None        → returns all tasks unchanged (default)

        Returns:
            A new list containing only the tasks that match the requested status.
            Unrecognised status strings return all tasks (fail-open).
        """
        if status == "pending":
            return [t for t in tasks if not t.completed]
        if status == "completed":
            return [t for t in tasks if t.completed]
        return list(tasks)
