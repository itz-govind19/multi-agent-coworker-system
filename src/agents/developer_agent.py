import json
from pathlib import Path
from src.agents.base_agent import BaseAgent
from src.tools.workspace_tools import read_file, write_file, list_files

class DeveloperAgent(BaseAgent):
    def __init__(self, agent_id: str = "dev_1", specialty: str = "Core Implementation"):
        super().__init__(
            name=agent_id,
            role=f"Developer ({specialty})",
            system_prompt=f"""You are an expert Senior Software Engineer ({specialty}).
Your role is to implement code based on assigned task descriptions.
Always produce clean, working code.
When instructed, format your file updates as JSON containing:
{{
  "filepath": "relative/path/to/file.ext",
  "content": "full code content to write",
  "summary": "short explanation of changes"
}}"""
        )

    def execute_task(self, project_id: str, task: dict, workspace_path: Path) -> dict:
        self.ping("WORKING", current_task_id=task["id"], details=f"Implementing {task['title']}")
        self.log(project_id, f"Picked up task {task['id']}: {task['title']}")

        files = list_files(workspace_path)
        prompt = f"""Task: {task['title']}
Description: {task['description']}

Current Project Files:
{json.dumps(files, indent=2)}

Please write the complete code needed for this task. Return ONLY a valid JSON object with fields:
- "filepath": relative path inside workspace
- "content": full file content
- "summary": what was done
"""
        response_text = self.call_llm(prompt, json_mode=True, project_id=project_id)
        
        # Clean markdown wrappers if any
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            # strict=False allows control characters / unescaped backslashes in code strings
            plan = json.loads(clean_text, strict=False)
            filepath = plan.get("filepath")
            content = plan.get("content")
            summary = plan.get("summary", "Code updated")

            if filepath and content:
                res = write_file(workspace_path, filepath, content)
                self.log(project_id, f"File written: {filepath} ({res})")
                self.ping("IDLE")
                return {"success": True, "summary": summary, "file": filepath}
            else:
                self.ping("IDLE")
                return {"success": False, "summary": "Invalid file plan returned by LLM"}
        except Exception as e:
            self.ping("ERROR", details=str(e))
            self.log(project_id, f"Error in implementation: {str(e)}", level="ERROR")
            return {"success": False, "summary": f"Failed to parse implementation: {str(e)}"}
