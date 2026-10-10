import sqlite3
from contextlib import contextmanager
from src.config import DB_PATH

def init_db():
    """Initializes SQLite database schema for projects, tasks, logs, and heartbeats."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Projects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                goal TEXT NOT NULL,
                workspace_path TEXT NOT NULL,
                status TEXT DEFAULT 'PLANNING', -- PLANNING, ACTIVE, COMPLETED, BLOCKED
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                task_type TEXT NOT NULL, -- ARCHITECTURE, DEV, TEST
                assigned_to TEXT,        -- Agent name (e.g. dev_1, qa_1)
                status TEXT DEFAULT 'TODO', -- TODO, IN_PROGRESS, TESTING, DONE, BLOCKED
                retry_count INTEGER DEFAULT 0,
                result_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        
        # Heartbeats & Agent Status Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_heartbeats (
                agent_name TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'IDLE', -- IDLE, WORKING, STUCK, ERROR
                current_task_id TEXT,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        """)
        
        # Logs / Audit Trail Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                agent_name TEXT NOT NULL,
                level TEXT DEFAULT 'INFO', -- INFO, WARN, ERROR, ALERT
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

@contextmanager
def get_db():
    """Context manager for SQLite connections with dict-like row access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
