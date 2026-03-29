# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

The scheduler in `pawpal_system.py` goes beyond a simple priority list. Here is what it can do:

| Feature | Method | Description |
|---|---|---|
| **Sort by time** | `Scheduler.sort_by_time(tasks)` | Orders any task list chronologically by `HH:MM` start time. Tasks without a time are placed last. |
| **Filter by pet** | `Scheduler.filter_by_pet(pet_name)` | Returns all tasks (pending and completed) for a single named pet. |
| **Filter by status** | `Scheduler.filter_tasks(tasks, status)` | Narrows a task list to `"pending"` or `"completed"` tasks. |
| **Recurring tasks** | `Task.next_occurrence()` / `Scheduler.mark_task_complete(pet, task)` | Completing a `"daily"` or `"weekly"` task automatically queues the next occurrence using `timedelta` (+1 day or +7 days). |
| **Conflict detection** | `Scheduler.detect_conflicts()` | Returns warning strings (never crashes) for three conditions: high-priority tasks exceed available time, any pet's workload exceeds available time, and two tasks share the same start time slot. |
| **Weekly deprioritization** | `Scheduler.build_plan()` | Weekly-frequency tasks are scheduled after all daily tasks, so daily care is never bumped by lower-urgency weekly chores. |

## Testing PawPal+

Run the full test suite with:

```bash
python -m pytest
```

**18 tests — all passing.**

| Category | Tests | What is verified |
|---|---|---|
| **Sorting** | 4 | `sort_by_time()` returns chronological HH:MM order; untimed tasks land last; `build_plan()` schedules high priority first; shorter tasks come first within the same priority tier |
| **Recurrence** | 4 | Daily task completion creates a new task due tomorrow (`timedelta(days=1)`); weekly creates one due in 7 days; `as-needed` returns `None`; pet task list grows by one after completion |
| **Conflict detection** | 3 | Duplicate start times produce a warning; different times produce no warning; total high-priority time exceeding available minutes triggers a budget warning |
| **Edge cases** | 4 | Pet with no tasks yields an empty plan; task skipped when time runs out; `filter_tasks` correctly isolates pending and completed tasks; weekly tasks always scheduled after daily tasks |
| **Baseline** | 2 | `mark_complete()` flips status; `add_task()` grows the task list |

**Confidence level: ★★★★☆**
Core scheduling paths, sorting, recurrence, and conflict detection are fully covered. The remaining gap is integration-level testing (Streamlit UI + full multi-pet session flows), which would push confidence to 5 stars.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
