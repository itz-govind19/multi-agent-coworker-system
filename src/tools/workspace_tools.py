import subprocess
from pathlib import Path
from typing import List, Dict, Any

def get_workspace_path(base_workspace: Path, relative_path: str = "") -> Path:
    """Safely resolves path inside workspace directory preventing traversal attacks."""
    resolved = (base_workspace / relative_path).resolve()
    if not str(resolved).startswith(str(base_workspace.resolve())):
        raise ValueError(f"Path traversal detected: {relative_path} is outside workspace")
    return resolved

def list_files(workspace_dir: Path, subpath: str = "") -> List[str]:
    """Lists files and directories recursively inside workspace."""
    target = get_workspace_path(workspace_dir, subpath)
    if not target.exists():
        return []
    
    file_list = []
    for item in target.rglob("*"):
        # Skip git metadata and virtual environments
        if ".git" in item.parts or "node_modules" in item.parts or "venv" in item.parts or "__pycache__" in item.parts:
            continue
        rel = item.relative_to(workspace_dir)
        file_list.append(str(rel) + ("/" if item.is_dir() else ""))
    return file_list[:200]  # Limit to 200 items

def read_file(workspace_dir: Path, filepath: str) -> str:
    """Reads content of a file in the workspace."""
    target = get_workspace_path(workspace_dir, filepath)
    if not target.exists() or not target.is_file():
        return f"Error: File {filepath} does not exist."
    try:
        return target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading file {filepath}: {str(e)}"

def write_file(workspace_dir: Path, filepath: str, content: str) -> str:
    """Writes content to a file in the workspace, creating parent directories if needed."""
    target = get_workspace_path(workspace_dir, filepath)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Success: File {filepath} written ({len(content)} chars)."
    except Exception as e:
        return f"Error writing file {filepath}: {str(e)}"

def run_command(workspace_dir: Path, command: str, timeout: int = 30) -> Dict[str, Any]:
    """Executes a command inside the target workspace directory safely."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution error: {str(e)}"
        }
