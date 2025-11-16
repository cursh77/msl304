import streamlit as st
import gurobipy as gp
from gurobipy import GRB
import pandas as pd

# ---------------------------------------
# CONSTANTS
# ---------------------------------------
SKILLS = ['cleaning', 'cooking', 'serving', 'receptionist']
MAX_TIME_SLOTS = 12


# ---------------------------------------
# GUROBI OPTIMIZATION  
# ---------------------------------------
def optimize_schedule(staff_skills, jobs, time_slots):
    STAFF = list(staff_skills.keys())
    JOBS = list(jobs.keys())
    TIMES = list(range(time_slots))

    m = gp.Model("HotelScheduler_Priority")
    m.Params.LogToConsole = 0

    possible_assignments = []
    for s in STAFF:
        for j in JOBS:
            job = jobs[j]
            for t in TIMES:
                has_skill = job['skill'] in staff_skills.get(s, [])
                meets_deadline = (t + job['duration_slots']) <= job['deadline_slot']
                in_shift = (t + job['duration_slots']) <= time_slots
                if has_skill and meets_deadline and in_shift:
                    possible_assignments.append((s, j, t))

    x = m.addVars(possible_assignments, vtype=GRB.BINARY, name="assign")
    is_completed = m.addVars(JOBS, vtype=GRB.BINARY, name="completed")

    m.setObjective(gp.quicksum(jobs[j]['priority'] * is_completed[j] for j in JOBS), GRB.MAXIMIZE)

    # Link completion variable to assignments
    for j in JOBS:
        m.addConstr(is_completed[j] == x.sum('*', j, '*'))

    # No overlapping jobs for a staff member
    for s in STAFF:
        for tau in TIMES:
            overlapping = []
            for (s2, j2, t2) in x.keys():
                if s2 != s:
                    continue
                duration = jobs[j2]['duration_slots']
                if t2 <= tau < t2 + duration:
                    overlapping.append(x[s2, j2, t2])
            if overlapping:
                m.addConstr(gp.quicksum(overlapping) <= 1)

    m.optimize()

    schedule = []
    uncompleted = []

    if m.Status == GRB.OPTIMAL:
        scheduled_jobs = set()
        for (s, j, t) in x.keys():
            if x[s, j, t].X > 0.5:
                job = jobs[j]
                schedule.append({
                    'Staff': s,
                    'Job ID': j,
                    'Task': job['task_name'],
                    'Start Slot': t,
                    'End Slot': t + job['duration_slots'],
                    'Priority': job['priority']
                })
                scheduled_jobs.add(j)

        for j in JOBS:
            if j not in scheduled_jobs:
                uncompleted.append({'job_id': j, **jobs[j]})

        schedule.sort(key=lambda d: d['Start Slot'])
        return schedule, uncompleted, m.ObjVal

    return None, JOBS, 0


# ---------------------------------------
# DEFAULT DATA (your Test Case 1)
# ---------------------------------------
def get_default_staff():
    return pd.DataFrame([
        {"staff_name": "Staff_1", "skills": "cooking, cleaning, receptionist"},
        {"staff_name": "Staff_2", "skills": "cleaning, receptionist, serving"},
        {"staff_name": "Staff_3", "skills": "receptionist, cooking, cleaning"},
        {"staff_name": "Staff_4", "skills": "serving"},
        {"staff_name": "Staff_5", "skills": "serving, cleaning, receptionist"},
        {"staff_name": "Staff_6", "skills": "cooking"},
        {"staff_name": "Staff_7", "skills": "serving"},
        {"staff_name": "Staff_8", "skills": "receptionist, cleaning"},
        {"staff_name": "Staff_9", "skills": "serving, receptionist"},
        {"staff_name": "Staff_10", "skills": "cleaning, cooking"},
    ])


def get_default_jobs():
    rows = [
        {"job_id": "Job_1", "task_name": "Morning Check-out Rush", "skill": "receptionist", "priority": 10, "duration_slots": 3, "deadline_slot": 5},
        {"job_id": "Job_2", "task_name": "Room 201 Turnover", "skill": "cleaning", "priority": 9, "duration_slots": 2, "deadline_slot": 6},
        {"job_id": "Job_3", "task_name": "Room 202 Turnover", "skill": "cleaning", "priority": 9, "duration_slots": 2, "deadline_slot": 7},
        {"job_id": "Job_4", "task_name": "Lunch Prep", "skill": "cooking", "priority": 8, "duration_slots": 3, "deadline_slot": 4},
        {"job_id": "Job_5", "task_name": "Lunch Service", "skill": "serving", "priority": 7, "duration_slots": 3, "deadline_slot": 8},
        {"job_id": "Job_6", "task_name": "Afternoon Check-in Wave", "skill": "receptionist", "priority": 10, "duration_slots": 3, "deadline_slot": 9},
        {"job_id": "Job_7", "task_name": "Lobby & Restroom Clean", "skill": "cleaning", "priority": 5, "duration_slots": 2, "deadline_slot": 10},
        {"job_id": "Job_8", "task_name": "Dinner Prep", "skill": "cooking", "priority": 8, "duration_slots": 3, "deadline_slot": 8},
        {"job_id": "Job_9", "task_name": "Dinner Service", "skill": "serving", "priority": 7, "duration_slots": 4, "deadline_slot": 12},
        {"job_id": "Job_10", "task_name": "Audit Night Books", "skill": "receptionist", "priority": 3, "duration_slots": 1, "deadline_slot": 12},
    ]
    return pd.DataFrame(rows)


# ---------------------------------------
# INIT DEFAULTS ON FIRST LOAD
# ---------------------------------------
if "staff_df" not in st.session_state:
    st.session_state.staff_df = get_default_staff()

if "jobs_df" not in st.session_state:
    st.session_state.jobs_df = get_default_jobs()

# Initialize empty schedule variables on first load
if "schedule" not in st.session_state:
    st.session_state.schedule = []
if "uncompleted" not in st.session_state:
    st.session_state.uncompleted = []
if "score" not in st.session_state:
    st.session_state.score = 0

# ---------------------------------------
# UI LAYOUT
# ---------------------------------------
st.set_page_config(layout="wide", page_title="Hotel Scheduler")
st.title("Welcome to GydeXP!")

col1, col2 = st.columns(2)

with col1:
    st.header("Staff Configuration")
    staff_df = st.data_editor(
        st.session_state.staff_df,
        key="staff_editor",
        num_rows="dynamic",
        use_container_width=True
    )
    # Only update if editor actually changed the data
    st.session_state.staff_df = staff_df

with col2:
    st.header("Job Configuration")
    jobs_df = st.data_editor(
        st.session_state.jobs_df,
        key="jobs_editor",
        num_rows="dynamic",
        column_config={"skill": st.column_config.SelectboxColumn(options=SKILLS)},
        use_container_width=True
    )
    st.session_state.jobs_df = jobs_df


st.divider()


# ---------------------------------------
# GENERATE BUTTON
# ALWAYS reads current UI state!
# ---------------------------------------
if st.button("🚀 Generate Optimal Schedule", type="primary"):

    # Convert staff table
    staff_dict = {}
    for _, row in staff_df.iterrows():
        if not row["staff_name"]:
            continue
        skills = [s.strip() for s in str(row["skills"]).split(",") if s.strip()]
        staff_dict[row["staff_name"]] = skills

    # Convert jobs table
    job_dict = {}
    for _, row in jobs_df.iterrows():
        if not row["job_id"]:
            continue
        job_dict[row["job_id"]] = {
            "task_name": row["task_name"],
            "skill": row["skill"],
            "priority": int(row["priority"]),
            "duration_slots": int(row["duration_slots"]),
            "deadline_slot": int(row["deadline_slot"])
        }

    # -------------------------------------------------------
    # REMOVE IMPOSSIBLE JOBS (duration > deadline)
    # -------------------------------------------------------
    removed = []
    for jid in list(job_dict.keys()):
        j = job_dict[jid]
        if j["duration_slots"] > j["deadline_slot"]:
            removed.append(jid)
            del job_dict[jid]

    if removed:
        st.warning(
            "⚠️ The following jobs were removed because their duration exceeds their deadline: "
            + ", ".join(removed)
        )

    # RUN OPTIMIZATION
    with st.spinner("Optimizing..."):
        schedule, uncompleted, score = optimize_schedule(staff_dict, job_dict, MAX_TIME_SLOTS)

    st.session_state.schedule = schedule
    st.session_state.uncompleted = uncompleted
    st.session_state.score = score


# ---------------------------------------
# DISPLAY RESULTS
# ---------------------------------------
if "schedule" in st.session_state:
    st.header("Results")

    st.metric("Total Priority", int(st.session_state.score))

    st.subheader("Completed Jobs")
    st.dataframe(pd.DataFrame(st.session_state.schedule), use_container_width=True)

    st.subheader("Uncompleted Jobs")
    st.dataframe(pd.DataFrame(st.session_state.uncompleted), use_container_width=True)

# -------------------------------------------------------
# GANTT CHART
# -------------------------------------------------------
# -------------------------------------------------------
# GANTT CHART (X-axis = Slots)
# -------------------------------------------------------
# -------------------------------------------------------
# GANTT CHART (SLOT-BASED, ALWAYS VISIBLE)
# -------------------------------------------------------
# -------------------------------------------------------
# GANTT CHART
# -------------------------------------------------------
st.subheader("📅 Gantt Chart")

if st.session_state.schedule:
    import plotly.express as px
    import pandas as pd
    from datetime import datetime, timedelta

    gantt_df = pd.DataFrame(st.session_state.schedule)

    # Convert slots to datetime for proper timeline visualization
    base_time = datetime(2024, 1, 1, 8, 0)  # Start at 8 AM
    gantt_df["Start_Time"] = gantt_df["Start Slot"].apply(
        lambda x: base_time + timedelta(hours=x)
    )
    gantt_df["End_Time"] = gantt_df["End Slot"].apply(
        lambda x: base_time + timedelta(hours=x)
    )
    
    # Add hover information
    gantt_df["Hover"] = gantt_df.apply(
        lambda row: f"{row['Task']}<br>Slots: {row['Start Slot']}-{row['End Slot']}<br>Priority: {row['Priority']}", 
        axis=1
    )

    fig = px.timeline(
        gantt_df,
        x_start="Start_Time",
        x_end="End_Time",
        y="Staff",
        color="Task",
        title="Staff Schedule (Slot-based)",
        hover_data={"Hover": True, "Start_Time": False, "End_Time": False}
    )

    # Update layout for better visualization
    fig.update_yaxes(autorange="reversed", title="Staff Member")
    fig.update_xaxes(
        title="Time Slot",
        tickformat="%H:%M",
        tickmode="linear",
        dtick=3600000  # 1 hour in milliseconds
    )
    fig.update_layout(
        bargap=0.2,
        height=max(400, len(gantt_df["Staff"].unique()) * 50),
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No schedule generated yet. Click 'Generate Optimal Schedule' to see the Gantt chart.")