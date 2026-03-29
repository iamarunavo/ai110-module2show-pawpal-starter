from pawpal_system import Owner, Pet, Task, Scheduler

# --- Setup ---
owner = Owner(name="Jordan", available_minutes=90)

mochi = Pet(name="Mochi", species="dog", age=3)
luna = Pet(name="Luna", species="cat", age=5)

mochi.add_task(Task("Morning walk",      duration_minutes=30, priority="high",   frequency="daily"))
mochi.add_task(Task("Breakfast feeding", duration_minutes=10, priority="high",   frequency="daily"))
mochi.add_task(Task("Enrichment puzzle", duration_minutes=20, priority="medium", frequency="weekly"))
mochi.add_task(Task("Grooming brush",    duration_minutes=15, priority="low",    frequency="weekly"))

luna.add_task(Task("Breakfast feeding",  duration_minutes=10, priority="high",   frequency="daily"))
luna.add_task(Task("Playtime",           duration_minutes=20, priority="medium", frequency="daily"))
luna.add_task(Task("Nail trim",          duration_minutes=10, priority="low",    frequency="weekly"))

owner.add_pet(mochi)
owner.add_pet(luna)

# --- Schedule ---
scheduler = Scheduler(owner)
plans = scheduler.build_all_plans()

# --- Display ---
print("=" * 50)
print("        TODAY'S SCHEDULE - PawPal+")
print("=" * 50)

for plan in plans:
    print()
    print(plan.explain())
    print("-" * 50)
