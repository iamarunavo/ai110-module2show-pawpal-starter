from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Existing baseline tests
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    """Calling mark_complete() should flip completed from False to True."""
    task = Task(title="Morning walk", duration_minutes=30, priority="high", frequency="daily")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase its task list by one."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high", frequency="daily"))
    assert len(pet.tasks) == 1


# ---------------------------------------------------------------------------
# Sorting correctness
# ---------------------------------------------------------------------------

def test_sort_by_time_returns_chronological_order():
    """sort_by_time() must return tasks in ascending HH:MM order."""
    owner = Owner(name="Jordan", available_minutes=90)
    scheduler = Scheduler(owner)
    tasks = [
        Task("Afternoon walk", 20, "medium", "daily", time="14:00"),
        Task("Morning feeding", 10, "high",   "daily", time="07:30"),
        Task("Midday brush",    15, "low",    "weekly", time="11:00"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert [t.time for t in result] == ["07:30", "11:00", "14:00"]


def test_sort_by_time_places_untimed_tasks_last():
    """Tasks with no time string should appear after all timed tasks."""
    owner = Owner(name="Jordan", available_minutes=90)
    scheduler = Scheduler(owner)
    tasks = [
        Task("No time task", 10, "high", "daily", time=""),
        Task("Early task",   10, "high", "daily", time="06:00"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert result[0].time == "06:00"
    assert result[1].time == ""


def test_build_plan_schedules_high_priority_before_low():
    """High-priority tasks must appear before low-priority tasks in the plan."""
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task("Grooming",   15, "low",  "weekly"))
    pet.add_task(Task("Feeding",    10, "high", "daily"))
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan(pet)
    priorities = [t.priority for t in plan.scheduled_tasks]
    assert priorities.index("high") < priorities.index("low")


def test_build_plan_shorter_task_first_within_same_priority():
    """Within the same priority tier, the shorter task should be scheduled first."""
    pet = Pet(name="Luna", species="cat", age=5)
    pet.add_task(Task("Long high task",  30, "high", "daily"))
    pet.add_task(Task("Short high task", 10, "high", "daily"))
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan(pet)
    assert plan.scheduled_tasks[0].title == "Short high task"
    assert plan.scheduled_tasks[1].title == "Long high task"


# ---------------------------------------------------------------------------
# Recurrence logic
# ---------------------------------------------------------------------------

def test_daily_task_creates_next_occurrence_tomorrow():
    """Completing a daily task must produce a new task due tomorrow."""
    pet = Pet(name="Mochi", species="dog", age=3)
    task = Task("Morning walk", 30, "high", "daily")
    pet.add_task(task)
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    next_task = scheduler.mark_task_complete(pet, task)

    assert next_task is not None
    assert next_task.due_date == date.today() + timedelta(days=1)
    assert next_task.title == "Morning walk"
    assert next_task.completed is False


def test_weekly_task_creates_next_occurrence_in_seven_days():
    """Completing a weekly task must produce a new task due in 7 days."""
    pet = Pet(name="Mochi", species="dog", age=3)
    task = Task("Grooming brush", 15, "low", "weekly")
    pet.add_task(task)
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(pet)

    next_task = Scheduler(owner).mark_task_complete(pet, task)

    assert next_task is not None
    assert next_task.due_date == date.today() + timedelta(weeks=1)


def test_as_needed_task_does_not_recur():
    """Completing an as-needed task must return None — no automatic recurrence."""
    pet = Pet(name="Luna", species="cat", age=5)
    task = Task("Vet visit", 60, "high", "as-needed")
    pet.add_task(task)
    owner = Owner(name="Jordan", available_minutes=120)
    owner.add_pet(pet)

    next_task = Scheduler(owner).mark_task_complete(pet, task)

    assert next_task is None


def test_mark_task_complete_adds_new_task_to_pet():
    """After completing a recurring task, the pet's task list should grow by one."""
    pet = Pet(name="Mochi", species="dog", age=3)
    task = Task("Feeding", 10, "high", "daily")
    pet.add_task(task)
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(pet)

    initial_count = len(pet.tasks)
    Scheduler(owner).mark_task_complete(pet, task)
    assert len(pet.tasks) == initial_count + 1


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_detect_conflicts_flags_duplicate_start_times():
    """Two tasks sharing the same HH:MM time must produce a conflict warning."""
    mochi = Pet(name="Mochi", species="dog", age=3)
    luna  = Pet(name="Luna",  species="cat", age=5)
    mochi.add_task(Task("Feeding", 10, "high", "daily", time="08:00"))
    luna.add_task( Task("Feeding", 10, "high", "daily", time="08:00"))

    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    warnings = Scheduler(owner).detect_conflicts()
    assert any("08:00" in w for w in warnings)


def test_detect_conflicts_no_warning_when_times_differ():
    """Tasks at different times should not produce a time-slot conflict warning."""
    mochi = Pet(name="Mochi", species="dog", age=3)
    luna  = Pet(name="Luna",  species="cat", age=5)
    mochi.add_task(Task("Feeding", 10, "high", "daily", time="07:30"))
    luna.add_task( Task("Feeding", 10, "high", "daily", time="08:15"))

    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    warnings = Scheduler(owner).detect_conflicts()
    assert not any("Conflict: multiple tasks" in w for w in warnings)


def test_detect_conflicts_warns_when_budget_exceeded():
    """Total high-priority time exceeding available minutes must trigger a warning."""
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task("Task A", 50, "high", "daily"))
    pet.add_task(Task("Task B", 50, "high", "daily"))
    owner = Owner(name="Jordan", available_minutes=60)  # 100 min needed, only 60 available
    owner.add_pet(pet)

    warnings = Scheduler(owner).detect_conflicts()
    assert any("high-priority" in w for w in warnings)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_pet_with_no_tasks_produces_empty_plan():
    """A pet with zero tasks should yield a plan with no scheduled or skipped tasks."""
    pet = Pet(name="Ghost", species="cat", age=2)
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan(pet)
    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []


def test_task_skipped_when_time_runs_out():
    """A task that doesn't fit in remaining time must appear in skipped_tasks."""
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task("Big task",   80, "high", "daily"))
    pet.add_task(Task("Small task", 20, "high", "daily"))
    owner = Owner(name="Jordan", available_minutes=80)  # only fits one
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan(pet)
    assert len(plan.skipped_tasks) == 1


def test_filter_tasks_by_pending_status():
    """filter_tasks with status='pending' should exclude completed tasks."""
    owner = Owner(name="Jordan", available_minutes=90)
    scheduler = Scheduler(owner)
    done = Task("Done task",    10, "low", "daily")
    done.mark_complete()
    tasks = [Task("Pending task", 10, "high", "daily"), done]

    result = scheduler.filter_tasks(tasks, status="pending")
    assert len(result) == 1
    assert result[0].title == "Pending task"


def test_filter_tasks_by_completed_status():
    """filter_tasks with status='completed' should include only completed tasks."""
    owner = Owner(name="Jordan", available_minutes=90)
    scheduler = Scheduler(owner)
    done = Task("Done task", 10, "low", "daily")
    done.mark_complete()
    tasks = [Task("Pending task", 10, "high", "daily"), done]

    result = scheduler.filter_tasks(tasks, status="completed")
    assert len(result) == 1
    assert result[0].title == "Done task"


def test_weekly_tasks_deprioritized_after_daily_tasks():
    """Weekly tasks must be scheduled only after all daily tasks in build_plan."""
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task("Weekly groom",  15, "low",  "weekly"))
    pet.add_task(Task("Daily feeding", 10, "high", "daily"))
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan(pet)

    titles = [t.title for t in plan.scheduled_tasks]
    assert titles.index("Daily feeding") < titles.index("Weekly groom")
