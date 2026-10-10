import os
import json
import uuid
from typing import List, Optional, Dict, Any
from src.db.database import get_db

def create_project(name: str, goal: str, workspace_path: str) -> str:
    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, goal, workspace_path, status) VALUES (?, ?, ?, ?, 'PLANNING')",
            (project_id, name, goal, workspace_path)
        )
        conn.commit()
    log_event(project_id, "System", f"Project created: {name} with target {workspace_path}")
    return project_id

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None

def get_all_projects() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def update_project_status(project_id: str, status: str):
    with get_db() as conn:
        conn.execute("UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, project_id))
        conn.commit()

def create_task(project_id: str, title: str, description: str, task_type: str, assigned_to: Optional[str] = None) -> str:
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, project_id, title, description, task_type, assigned_to, status) 
               VALUES (?, ?, ?, ?, ?, ?, 'TODO')""",
            (task_id, project_id, title, description, task_type, assigned_to)
        )
        conn.commit()
    log_event(project_id, "ProjectManager", f"New task created: [{task_type}] {title}")
    return task_id

def get_tasks_for_project(project_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at ASC", (project_id,)).fetchall()
        return [dict(r) for r in rows]

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

def update_task_status(task_id: str, status: str, result_summary: Optional[str] = None):
    with get_db() as conn:
        if result_summary:
            conn.execute(
                """UPDATE tasks SET status = ?, result_summary = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""", (status, result_summary, task_id)
            )
        else:
            conn.execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, task_id))
        conn.commit()

def increment_task_retry(task_id: str) -> int:
    with get_db() as conn:
        conn.execute("UPDATE tasks SET retry_count = retry_count + 1 WHERE id = ?", (task_id,))
        conn.commit()
        row = conn.execute("SELECT retry_count FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row["retry_count"] if row else 0

def update_heartbeat(agent_name: str, role: str, status: str, current_task_id: Optional[str] = None, details: str = ""):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO agent_heartbeats (agent_name, role, status, current_task_id, last_heartbeat, details)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(agent_name) DO UPDATE SET
                status = excluded.status,
                current_task_id = excluded.current_task_id,
                last_heartbeat = CURRENT_TIMESTAMP,
                details = excluded.details
        """, (agent_name, role, status, current_task_id, details))
        conn.commit()

def get_all_heartbeats() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM agent_heartbeats ORDER BY agent_name ASC").fetchall()
        return [dict(r) for r in rows]

def log_event(project_id: Optional[str], agent_name: str, message: str, level: str = "INFO"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO agent_logs (project_id, agent_name, level, message) VALUES (?, ?, ?, ?)",
            (project_id, agent_name, level, message)
        )
        conn.commit()

def get_logs(project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    with get_db() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM agent_logs WHERE project_id = ? ORDER BY id DESC LIMIT ?", (project_id, limit)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM agent_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
