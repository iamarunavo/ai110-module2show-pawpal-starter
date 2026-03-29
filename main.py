from pawpal_system import Owner, Pet, Task, Scheduler

# --- Setup ---
owner = Owner(name="Jordan", available_minutes=90)

mochi = Pet(name="Mochi", species="dog", age=3)
luna = Pet(name="Luna", species="cat", age=5)

# Tasks added out of order intentionally to demonstrate sort_by_time()
mochi.add_task(Task("Morning walk",      duration_minutes=30, priority="high",   frequency="daily",  time="07:30"))
mochi.add_task(Task("Enrichment puzzle", duration_minutes=20, priority="medium", frequency="weekly", time="14:00"))
mochi.add_task(Task("Breakfast feeding", duration_minutes=10, priority="high",   frequency="daily",  time="08:00"))
mochi.add_task(Task("Grooming brush",    duration_minutes=15, priority="low",    frequency="weekly", time="11:00"))

# Luna's "Breakfast feeding" intentionally uses 08:00 — same as Mochi's — to trigger conflict detection
luna.add_task(Task("Playtime",           duration_minutes=20, priority="medium", frequency="daily",  time="15:30"))
luna.add_task(Task("Breakfast feeding",  duration_minutes=10, priority="high",   frequency="daily",  time="08:00"))
luna.add_task(Task("Nail trim",          duration_minutes=10, priority="low",    frequency="weekly", time="10:00"))

owner.add_pet(mochi)
owner.add_pet(luna)

# --- Schedule ---
scheduler = Scheduler(owner)

# --- Sort by time ---
print("\n--- All tasks sorted by scheduled start time (HH:MM) ---")
all_tasks = owner.get_all_tasks()
for t in scheduler.sort_by_time(all_tasks):
    print(f"  {t.time or '--:--'}  {t.title}")

# --- Filter by pet name ---
print("\n--- Mochi's tasks (filtered by pet) ---")
for t in scheduler.filter_by_pet("Mochi"):
    print(f"  {t}")

# --- Filter by status ---
print("\n--- All pending tasks (filtered by status) ---")
pending = scheduler.filter_tasks(owner.get_all_tasks(), status="pending")
for t in pending:
    print(f"  {t}")

# Feature 4: Conflict detection
conflicts = scheduler.detect_conflicts()
if conflicts:
    print("\n--- Conflict Warnings ---")
    for w in conflicts:
        print(f"  WARNING: {w}")
else:
    print("\nNo scheduling conflicts detected.")

# --- Recurring task automation ---
print("\n--- Recurring task automation ---")
morning_walk = mochi.tasks[0]  # "Morning walk" (daily)
next_task = scheduler.mark_task_complete(mochi, morning_walk)
if next_task:
    print(f"  Completed: '{morning_walk.title}' (now marked done)")
    print(f"  Auto-scheduled next occurrence: '{next_task.title}' due {next_task.due_date}")
else:
    print(f"  '{morning_walk.title}' is as-needed — no recurrence created")

plans = scheduler.build_all_plans()

# --- Display ---
print("=" * 50)
print("        TODAY'S SCHEDULE - PawPal+")
print("=" * 50)

for plan in plans:
    print()
    print(plan.explain())
    print("-" * 50)
