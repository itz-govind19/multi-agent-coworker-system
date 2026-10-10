from pathlib import Path
from typing import Dict, Any, List
from src.agents.base_agent import BaseAgent
from src.agents.developer_agent import DeveloperAgent
from src.agents.tester_agent import TesterAgent
from src.db.repository import (
    get_tasks_for_project,
    update_task_status,
    increment_task_retry,
    update_project_status
)
from src.config import MAX_TASK_RETRY_COUNT

class ProjectManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ProjectManager",
            role="Project Manager & Fleet Coordinator",
            system_prompt="You manage the project board, assign tasks to developers and testers, and oversee deliverable quality."
        )
        # Squad of 4: 2 Developers + 2 Testers
        self.devs = {
            "dev_1": DeveloperAgent(agent_id="dev_1", specialty="Backend & Core Logic"),
            "dev_2": DeveloperAgent(agent_id="dev_2", specialty="Frontend & Integration")
        }
        self.testers = {
            "qa_1": TesterAgent(agent_id="qa_1", specialty="Unit & Regression Testing"),
            "qa_2": TesterAgent(agent_id="qa_2", specialty="End-to-End & Boundary Testing")
        }

    def run_sprint(self, project_id: str, workspace_path: str):
        """Runs the active sprint loop through TODO -> IN_PROGRESS -> TESTING -> DONE."""
        self.log(project_id, "Project Manager starting execution sprint...")
        self.ping("WORKING", details="Executing project tasks")
        update_project_status(project_id, "ACTIVE")

        ws_path = Path(workspace_path)

        while True:
            tasks = get_tasks_for_project(project_id)
            pending_tasks = [t for t in tasks if t["status"] in ("TODO", "IN_PROGRESS", "TESTING")]
            
            if not pending_tasks:
                self.log(project_id, "All tasks completed! Project finished successfully.")
                update_project_status(project_id, "COMPLETED")
                self.ping("IDLE")
                break

            for task in pending_tasks:
                task_id = task["id"]
                status = task["status"]

                # 1. Dev Phase
                if status == "TODO":
                    update_task_status(task_id, "IN_PROGRESS")
                    dev_id = task.get("assigned_to") if task.get("assigned_to") in self.devs else "dev_1"
                    dev_agent = self.devs[dev_id]

                    result = dev_agent.execute_task(project_id, task, ws_path)
                    if result["success"]:
                        update_task_status(task_id, "TESTING", result_summary=result["summary"])
                    else:
                        retries = increment_task_retry(task_id)
                        if retries >= MAX_TASK_RETRY_COUNT:
                            update_task_status(task_id, "BLOCKED", result_summary="Max retries reached during Dev phase.")
                            self.log(project_id, f"Task {task_id} BLOCKED: Dev failed {retries} times.", level="WARN")

                # 2. QA Phase
                elif status == "TESTING":
                    qa_id = "qa_1" if "qa_1" in task.get("assigned_to", "") else "qa_2"
                    qa_agent = self.testers[qa_id]

                    test_res = qa_agent.execute_test(project_id, task, ws_path)
                    if test_res["passed"]:
                        update_task_status(task_id, "DONE", result_summary=f"QA Passed: {test_res['output']}")
                        self.log(project_id, f"Task {task_id} verified and marked DONE by {qa_id}")
                    else:
                        retries = increment_task_retry(task_id)
                        if retries >= MAX_TASK_RETRY_COUNT:
                            update_task_status(task_id, "BLOCKED", result_summary=f"QA Repeated Failure: {test_res['output']}")
                            self.log(project_id, f"Task {task_id} BLOCKED: QA failed {retries} times.", level="ALERT")
                        else:
                            # Re-assign back to developer to fix
                            update_task_status(task_id, "IN_PROGRESS", result_summary=f"Bug reported by QA: {test_res['output']}")
                            self.log(project_id, f"Task {task_id} bounced back to Dev for fixes (Attempt {retries})")

            # Check if all remaining are blocked
            refreshed = get_tasks_for_project(project_id)
            non_done = [t for t in refreshed if t["status"] != "DONE"]
            all_blocked = non_done and all(t["status"] == "BLOCKED" for t in non_done)
            if all_blocked:
                self.log(project_id, "All remaining tasks are BLOCKED. Escalating to Product Manager.", level="ALERT")
                update_project_status(project_id, "BLOCKED")
                self.ping("IDLE", details="Blocked tasks require human review")
                break

        self.ping("IDLE")
