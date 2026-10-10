import sys
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import time

from src.db.database import init_db
from src.db.repository import (
    create_project,
    create_or_resume_project,
    get_all_projects,
    get_project,
    get_tasks_for_project,
    get_all_heartbeats,
    get_logs,
    update_task_status
)
from src.agents.planner_squad import LeadPlannerSquad
from src.agents.project_manager import ProjectManagerAgent
from src.monitor.watchdog import HealthWatchdog
from src.config import TARGET_WORKSPACE

# Page configuration
st.set_page_config(
    page_title="Multi-AI Agent Fleet Control",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_db()

# Custom styles
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .status-badge {
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Multi-AI Agent Fleet Management")
st.caption("Directory-Agnostic, Plug-and-Play Multi-Agent Autonomous SDLC Fleet")

# Sidebar: Project Management & Human PM Input
st.sidebar.header("🎯 Product Manager (You)")

with st.sidebar.expander("➕ Launch New Project / Goal", expanded=True):
    with st.form("new_project_form"):
        proj_name = st.text_input("Project Name", placeholder="e.g. Option Trading System")
        proj_goal = st.text_area("What do you want the AI fleet to do in this project?", placeholder="e.g. Audit test coverage in tests/, fix failing tests, or add a new risk management module.")
        
        # Dynamic Mode Selection
        from src.config import IS_EXISTING_PROJECT
        is_existing = st.checkbox("Existing Project Codebase", value=IS_EXISTING_PROJECT, help="If checked, agents reuse cached architectural understanding to save tokens. If unchecked, agents design from scratch based on Product Manager input.")
        
        # Target workspace
        workspace_dir = st.text_input(
            "Workspace Path", 
            value=str(TARGET_WORKSPACE),
            help="In Docker, leave this as '/workspace'. It automatically mirrors your host project defined in TARGET_PROJECT_PATH."
        )
        if is_existing:
            st.caption("💡 *Existing Mode: Planner inspects architecture once, caches it, and plans changes strictly aligned with existing modules.*")
        else:
            st.caption("💡 *New Project Mode: Planner drafts new architecture strictly from your requirements from scratch.*")
        submitted = st.form_submit_button("🚀 Inspect Repo & Plan Tasks")
        
        if submitted and proj_name and proj_goal:
            proj_id, is_resumed = create_or_resume_project(proj_name, proj_goal, workspace_dir)
            existing_tasks = get_tasks_for_project(proj_id)
            
            # If project already exists and has tasks, RESUME seamlessly without re-planning
            if is_resumed and existing_tasks:
                st.info(f"🔄 Resumed active project **{proj_name}**! Restored {len(existing_tasks)} tasks from last session without spending new tokens.")
                time.sleep(1)
                st.rerun()
            else:
                with st.spinner("Lead Planner Squad is analyzing requirements and generating tasks..."):
                    planner = LeadPlannerSquad()
                    tasks_created = planner.plan_project(proj_id, proj_goal, workspace_dir)
                    if tasks_created:
                        st.success(f"🎉 Generated {len(tasks_created)} technical tasks on the Kanban board!")
                    else:
                        st.warning("⚠️ Planning completed, but 0 tasks were generated. Check 'Live Agent Logs' for details.")
                    st.rerun()

# Select Active Project
projects = get_all_projects()
project_options = {p["name"] + f" ({p['id']})": p["id"] for p in projects}

if project_options:
    selected_label = st.sidebar.selectbox("Active Project", list(project_options.keys()))
    selected_proj_id = project_options[selected_label]
    current_proj = get_project(selected_proj_id)
else:
    selected_proj_id = None
    current_proj = None

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Projects", len(projects))
with col2:
    status_text = current_proj["status"] if current_proj else "N/A"
    st.metric("Project Status", status_text)
with col3:
    heartbeats = get_all_heartbeats()
    active_agents = len([h for h in heartbeats if h["status"] == "WORKING"])
    st.metric("Agents Working", f"{active_agents} / {len(heartbeats) if heartbeats else 7}")
with col4:
    if selected_proj_id:
        tasks = get_tasks_for_project(selected_proj_id)
        done_tasks = len([t for t in tasks if t["status"] == "DONE"])
        st.metric("Tasks Completed", f"{done_tasks} / {len(tasks)}")
    else:
        st.metric("Tasks Completed", "0 / 0")

# Prominent System Error / Alert Banner
latest_errors = [l for l in get_logs(selected_proj_id, limit=10) if l["level"] in ("ERROR", "ALERT")]
if latest_errors:
    most_recent = latest_errors[0]
    st.error(f"🚨 **Latest Issue Detected [{most_recent['agent_name']} - {most_recent['created_at']}]:**\n\n`{most_recent['message']}`")

st.divider()

# Main Workspace Tabs
tab_board, tab_fleet, tab_logs, tab_actions = st.tabs([
    "📋 Task Kanban Board", 
    "🩺 Fleet Health & Monitoring", 
    "📜 Live Agent Logs", 
    "⚡ Project Execution Controls"
])

# 1. Kanban Board
with tab_board:
    if selected_proj_id:
        tasks = get_tasks_for_project(selected_proj_id)
        cols = st.columns(4)
        col_map = {"TODO": cols[0], "IN_PROGRESS": cols[1], "TESTING": cols[2], "DONE": cols[3]}
        
        cols[0].markdown("### 📝 To Do")
        cols[1].markdown("### 🔨 In Progress (Dev)")
        cols[2].markdown("### 🧪 Testing (QA)")
        cols[3].markdown("### ✅ Done")

        for task in tasks:
            status = task["status"]
            target_col = col_map.get(status, cols[0])
            with target_col:
                with st.expander(f"**{task['title']}**", expanded=True):
                    st.write(task["description"])
                    st.caption(f"Assigned to: `{task['assigned_to']}` | Type: `{task['task_type']}`")
                    if task.get("result_summary"):
                        st.info(f"**Summary:** {task['result_summary']}")
                    if task["retry_count"] > 0:
                        st.warning(f"Retries: {task['retry_count']}")
    else:
        st.info("No active project. Create a project in the sidebar to get started.")

# 2. Fleet Health & Monitoring
with tab_fleet:
    st.markdown("### 🩺 Fleet Health & Live Agent Activity")
    
    # Auto-refresh option
    col_auto, col_btn = st.columns([3, 1])
    with col_btn:
        if st.button("🔄 Refresh Fleet Status"):
            st.rerun()

    # Visual agent status grid
    if heartbeats:
        st.markdown("#### 🤖 Agent Fleet Roster")
        hb_cols = st.columns(3)
        for idx, hb in enumerate(heartbeats):
            c = hb_cols[idx % 3]
            with c:
                status = hb.get("status", "IDLE")
                # Visual styling based on agent activity
                if status == "WORKING":
                    card_border = "#28a745" # green
                    badge = "🟢 WORKING"
                elif status == "ERROR":
                    card_border = "#dc3545" # red
                    badge = "🔴 ERROR"
                else:
                    card_border = "#6c757d" # grey
                    badge = "⚪ IDLE"
                
                st.markdown(f"""
                <div style="border: 2px solid {card_border}; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: rgba(255,255,255,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0;">{hb['agent_name']}</h4>
                        <span style="font-size: 0.85em; font-weight: bold;">{badge}</span>
                    </div>
                    <p style="color: #888; margin: 4px 0 8px 0; font-size: 0.9em;">{hb['role']}</p>
                    <p style="margin: 2px 0;"><strong>Active Task:</strong> <code>{hb.get('current_task_id') or 'None'}</code></p>
                    <p style="margin: 2px 0; font-size: 0.85em;"><strong>Current Action:</strong> {hb.get('details') or 'Standing by'}</p>
                    <p style="margin: 2px 0; font-size: 0.75em; color: #aaa;">Last heartbeat: {hb.get('last_heartbeat', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No agents registered yet. Agents register heartbeats automatically when a project starts.")

    st.divider()
    st.markdown("#### 🛡️ Deadlock & Health Watchdog Audit")
    if selected_proj_id:
        if st.button("🔍 Run Full Fleet Watchdog Audit", type="secondary"):
            watchdog = HealthWatchdog()
            report = watchdog.check_health(selected_proj_id)
            if report["alerts"]:
                for alert in report["alerts"]:
                    st.error(f"🚨 {alert}")
            else:
                st.success("✅ Watchdog check passed: All agents responsive, 0 deadlocks or feedback loops detected.")

# 3. Live Logs
with tab_logs:
    st.markdown("### 📜 System & Agent Audit Trail")
    logs = get_logs(selected_proj_id, limit=50)
    if logs:
        for log in logs:
            badge = "ℹ️" if log["level"] == "INFO" else "⚠️" if log["level"] == "WARN" else "🚨"
            st.markdown(f"`{log['created_at']}` {badge} **[{log['agent_name']}]**: {log['message']}")
    else:
        st.info("No logs found for this project.")

# 4. Execution Controls
with tab_actions:
    if selected_proj_id and current_proj:
        st.markdown(f"### ⚙️ Execute Project: **{current_proj['name']}**")
        st.write(f"**Target Workspace:** `{current_proj['workspace_path']}`")
        
        col_exec, col_reset = st.columns(2)
        with col_exec:
            if st.button("▶️ Run Sprint (PM + 2 Devs + 2 Testers)", type="primary"):
                with st.spinner("Project Manager is dispatching tasks to Developers and Testers..."):
                    pm = ProjectManagerAgent()
                    pm.run_sprint(selected_proj_id, current_proj["workspace_path"])
                    st.success("Sprint iteration completed!")
                    st.rerun()
        with col_reset:
            if st.button("🔄 Refresh View"):
                st.rerun()
