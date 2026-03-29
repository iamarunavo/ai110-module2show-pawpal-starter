import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

with st.expander("Scenario"):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

with st.expander("What you need to build"):
    st.markdown(
        """
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

# ------------------------------------------------------------------
# Session state bootstrap — objects survive button clicks / reruns
# ------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None
if "pets" not in st.session_state:
    st.session_state.pets = {}   # pet_name -> Pet object

# ------------------------------------------------------------------
# Section A: Owner setup
# ------------------------------------------------------------------
st.divider()
st.subheader("1. Owner Setup")

with st.form("owner_form"):
    owner_name = st.text_input("Owner name", value="Jordan")
    available_minutes = st.number_input(
        "Time available today (minutes)", min_value=10, max_value=480, value=90
    )
    submitted = st.form_submit_button("Save owner")

if submitted:
    st.session_state.owner = Owner(
        name=owner_name, available_minutes=int(available_minutes)
    )
    st.success(f"Owner saved: {owner_name} ({available_minutes} min available)")

if st.session_state.owner:
    o = st.session_state.owner
    st.info(f"Current owner: **{o.name}** — {o.available_minutes} min available")

# ------------------------------------------------------------------
# Section B: Add a pet
# ------------------------------------------------------------------
if st.session_state.owner:
    st.divider()
    st.subheader("2. Add a Pet")

    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

    if st.button("Add pet"):
        if pet_name in st.session_state.pets:
            st.warning(f"{pet_name} is already added.")
        else:
            pet = Pet(name=pet_name, species=species, age=int(age))
            st.session_state.owner.add_pet(pet)
            st.session_state.pets[pet_name] = pet
            st.success(f"Added {pet_name} the {species}!")

    if st.session_state.pets:
        st.write("**Registered pets:**")
        for name, pet in st.session_state.pets.items():
            st.write(f"- {pet.name} ({pet.species}, age {pet.age})")

# ------------------------------------------------------------------
# Section C: Add a task to a pet
# ------------------------------------------------------------------
if st.session_state.pets:
    st.divider()
    st.subheader("3. Add a Task")

    col1, col2 = st.columns(2)
    with col1:
        selected_pet = st.selectbox("Assign to pet", list(st.session_state.pets.keys()))
        task_title = st.text_input("Task title", value="Morning walk")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col2:
        priority = st.selectbox("Priority", ["high", "medium", "low"])
        frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])
        task_time = st.text_input("Start time (HH:MM, optional)", value="", placeholder="e.g. 08:00")

    if st.button("Add task"):
        pet = st.session_state.pets[selected_pet]
        pet.add_task(
            Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                frequency=frequency,
                time=task_time.strip(),
            )
        )
        st.success(f"Added '{task_title}' to {selected_pet}.")

    st.write("**Current tasks by pet:**")
    for name, pet in st.session_state.pets.items():
        pending = pet.get_pending_tasks()
        if pending:
            st.write(f"**{name}**")
            st.table(
                [
                    {
                        "Task": t.title,
                        "Duration (min)": t.duration_minutes,
                        "Priority": t.priority,
                        "Frequency": t.frequency,
                    }
                    for t in pending
                ]
            )

# ------------------------------------------------------------------
# Section D: Generate schedule
# ------------------------------------------------------------------
if st.session_state.owner and st.session_state.pets:
    st.divider()
    st.subheader("4. Generate Today's Schedule")

    if st.button("Generate schedule"):
        owner = st.session_state.owner
        scheduler = Scheduler(owner)

        # --- Conflict warnings (shown before plans so owner can act on them) ---
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            for w in conflicts:
                if "multiple tasks scheduled at" in w:
                    st.error(f"Time conflict: {w}")
                else:
                    st.warning(f"Budget warning: {w}")
        else:
            st.success("No scheduling conflicts detected.")

        # --- Per-pet plans ---
        plans = scheduler.build_all_plans()
        if not plans:
            st.warning("No pets found. Add at least one pet first.")
        else:
            for plan in plans:
                st.markdown(f"### {plan.pet.name}'s Plan ({plan.pet.species})")

                # Scheduled tasks sorted by start time
                sorted_scheduled = scheduler.sort_by_time(plan.scheduled_tasks)
                if sorted_scheduled:
                    st.success(
                        f"Scheduled {len(sorted_scheduled)} task(s) — "
                        f"{plan.total_duration()} / {owner.available_minutes} min used"
                    )
                    st.dataframe(
                        [
                            {
                                "Time": t.time if t.time else "--",
                                "Task": t.title,
                                "Duration (min)": t.duration_minutes,
                                "Priority": t.priority,
                                "Frequency": t.frequency,
                            }
                            for t in sorted_scheduled
                        ],
                        use_container_width=True,
                    )
                else:
                    st.warning("No tasks could be scheduled for this pet.")

                # Skipped tasks with reasons
                if plan.skipped_tasks:
                    st.warning(f"{len(plan.skipped_tasks)} task(s) could not be scheduled:")
                    st.table(
                        [
                            {"Task": t.title, "Reason": t.reason_skipped or "reason unknown"}
                            for t in plan.skipped_tasks
                        ]
                    )

                with st.expander("Reasoning"):
                    st.text(plan.explain())
