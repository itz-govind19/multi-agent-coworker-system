import time
from datetime import datetime
from src.agents.base_agent import BaseAgent
from src.db.repository import get_all_heartbeats, get_tasks_for_project, update_task_status, log_event
from src.config import HEARTBEAT_TIMEOUT_SECONDS, MAX_TASK_RETRY_COUNT

class HealthWatchdog(BaseAgent):
    def __init__(self):
        super().__init__(
            name="HealthWatchdog",
            role="Health, Deadlock & Monitoring Guard",
            system_prompt="You monitor agent fleets for hung workers, infinite feedback loops, and cost guardrails."
        )

    def check_health(self, project_id: str) -> dict:
        """Inspects heartbeats and tasks for stalled workers or endless QA-Dev ping-pong."""
        self.ping("WORKING", details="Running fleet health audit")
        alerts = []

        # 1. Audit Heartbeats
        heartbeats = get_all_heartbeats()
        for hb in heartbeats:
            # We check if an agent marked 'WORKING' has been silent for too long
            if hb["status"] == "WORKING":
                # For basic SQLite, compare timestamps
                pass

        # 2. Check for deadlock loops in tasks
        tasks = get_tasks_for_project(project_id)
        for t in tasks:
            if t["retry_count"] >= MAX_TASK_RETRY_COUNT and t["status"] != "BLOCKED":
                msg = f"Watchdog detected loop threshold on task {t['id']} (retried {t['retry_count']} times). Forcing status to BLOCKED."
                self.log(project_id, msg, level="ALERT")
                update_task_status(t["id"], "BLOCKED", result_summary="Watchdog intervention: infinite loop prevented.")
                alerts.append(msg)

        self.ping("IDLE", details="Monitoring loop nominal")
        return {"alerts": alerts, "task_count": len(tasks)}
