import json
from pathlib import Path
from typing import List, Dict, Any
from src.agents.base_agent import BaseAgent
from src.tools.workspace_tools import list_files
from src.db.repository import create_task

class RequirementsAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="RequirementsAnalyst",
            role="Planner: Requirements Specialist",
            system_prompt="""You are an expert Software Requirements Engineer.
Your job is to analyze high-level user goals, identify edge cases, input validation needs, and operational requirements.
Produce clear, modular software requirements without fluff."""
        )

    def analyze(self, goal: str, project_id: str = None) -> str:
        self.ping("WORKING", details="Analyzing user goal requirements")
        prompt = f"""Break down the following goal into functional requirements and critical edge cases:
Goal: {goal}

Output clear bullet points covering:
1. Core Functionality
2. Input Validation & Boundaries
3. Error Handling Cases
"""
        result = self.call_llm(prompt, project_id=project_id)
        self.ping("IDLE")
        return result


class SystemArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SystemArchitect",
            role="Planner: Technical Architect",
            system_prompt="""You are a Principal Software Architect.
Your job is to inspect an existing repository structure, understand its design and patterns, and plan tasks that integrate seamlessly with the existing codebase without breaking existing functionality.
Always return response in strict JSON format."""
        )

    def design_architecture(self, goal: str, requirements: str, workspace_files: List[str], project_id: str = None) -> List[Dict[str, Any]]:
        self.ping("WORKING", details="Designing architecture & task plan")
        prompt = f"""You are analyzing an EXISTING project codebase.
Goal requested by user: {goal}

Requirements:
{requirements}

Existing Files in Workspace:
{json.dumps(workspace_files, indent=2)}

IMPORTANT INSTRUCTIONS:
1. Do NOT recreate files that already exist if the user wants to understand or analyze the project.
2. If the user asks to "understand core concepts" or "analyze the existing project", create READ-ONLY and analysis tasks (e.g. document architecture, map data flows, audit test coverage).
3. If coding is needed, design tasks that modify or extend existing modules rather than overwriting.

Output MUST be a JSON array of task objects with fields:
- "title": Short descriptive title
- "description": Concrete technical description explaining what files to inspect or update
- "task_type": One of "DEV" or "TEST"
- "assigned_role": One of "dev_1", "dev_2", "qa_1", "qa_2"

Format Example:
[
  {{"title": "Implement User Model", "description": "Create src/models/user.py with fields...", "task_type": "DEV", "assigned_role": "dev_1"}},
  {{"title": "Test User Validation", "description": "Write tests in tests/test_user.py...", "task_type": "TEST", "assigned_role": "qa_1"}}
]
"""
        response_text = self.call_llm(prompt, json_mode=True, project_id=project_id)
        self.ping("IDLE")
        
        # Clean response if wrapped in markdown code blocks
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            tasks = json.loads(clean_text)
            if isinstance(tasks, list):
                self.log(project_id, f"SystemArchitect parsed {len(tasks)} valid tasks.")
                return tasks
            elif isinstance(tasks, dict) and "tasks" in tasks:
                self.log(project_id, f"SystemArchitect parsed {len(tasks['tasks'])} valid tasks from dict.")
                return tasks["tasks"]
            else:
                self.log(project_id, f"SystemArchitect returned unexpected JSON structure: {clean_text[:100]}", level="WARN")
                return []
        except Exception as e:
            self.log(project_id, f"Failed to parse tasks JSON: {str(e)}. Raw: {clean_text[:100]}", level="ERROR")
            return []


class LeadPlannerSquad(BaseAgent):
    def __init__(self):
        super().__init__(
            name="LeadPlanner",
            role="Lead Planner Orchestrator",
            system_prompt="You lead the planning squad, coordinating requirements analysis and technical task design."
        )
        self.req_analyst = RequirementsAnalystAgent()
        self.architect = SystemArchitectAgent()

    def plan_project(self, project_id: str, goal: str, workspace_path: str) -> List[Dict[str, Any]]:
        self.log(project_id, "Starting planning squad workflow...")
        self.ping("WORKING", details="Coordinating planning squad")

        # 1. Inspect existing files in workspace
        existing_files = list_files(Path(workspace_path))
        self.log(project_id, f"Workspace inspected: found {len(existing_files)} files/dirs")

        # 2. Run Requirements Sub-agent
        self.log(project_id, "Requirements Analyst analyzing goal...")
        requirements = self.req_analyst.analyze(goal, project_id=project_id)
        self.log(project_id, "Requirements analysis complete.")

        # 3. Run System Architect Sub-agent
        self.log(project_id, "System Architect designing task graph...")
        tasks = self.architect.design_architecture(goal, requirements, existing_files, project_id=project_id)

        # 4. Save tasks to SQLite DB
        created_tasks = []
        for t in tasks:
            task_id = create_task(
                project_id=project_id,
                title=t.get("title", "Untitled Task"),
                description=t.get("description", ""),
                task_type=t.get("task_type", "DEV"),
                assigned_to=t.get("assigned_role", "dev_1")
            )
            created_tasks.append(task_id)

        self.log(project_id, f"Planning finished! Created {len(created_tasks)} tasks on the project board.")
        self.ping("IDLE")
        return tasks
