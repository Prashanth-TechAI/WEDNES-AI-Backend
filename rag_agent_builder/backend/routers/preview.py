import os
import subprocess
import time
from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse
from ..utils.path_utils import get_agent_output_dir
from ..utils.process_utils import kill_process_on_port


router = APIRouter()
preview_processes = {}

def sanitize_main_py(main_path: str):
    with open(main_path, "r") as f:
        lines = f.readlines()
    clean_lines = [line for line in lines if not line.strip().startswith("```")]
    if len(clean_lines) != len(lines):
        with open(main_path, "w") as f:
            f.writelines(clean_lines)

def detect_ui_framework(main_path: str) -> str:
    with open(main_path, "r") as f:
        content = f.read()
    if "streamlit" in content:
        return "streamlit"
    elif "gr.Interface" in content or "gradio" in content:
        return "gradio"
    return "unknown"

@router.post("/previews/{session_id}/start")
def start_preview(session_id: str):
    agent_path, _ = get_agent_output_dir(session_id)
    main_path = os.path.join(agent_path, "main.py")

    if not os.path.exists(main_path):
        raise HTTPException(status_code=404, detail="main.py not found")

    sanitize_main_py(main_path)

    # Kill previous process if exists
    prev = preview_processes.get(session_id)
    if prev and prev.poll() is None:
        prev.terminate()

    ui = detect_ui_framework(main_path)

    if ui == "streamlit":
        kill_process_on_port(8501)
        cmd = [
            "streamlit", "run", "main.py",
            "--server.port", "8501",
            "--server.headless", "true"
        ]
        preview_url = "http://localhost:8501"

    elif ui == "gradio":
        cmd = ["python", "main.py"]
        preview_url = "http://127.0.0.1:7860/"

    else:
        raise HTTPException(status_code=400, detail="Unknown UI framework in main.py")

    # Log output to file
    log_path = os.path.join(agent_path, "preview.log")
    try:
        with open(log_path, "w") as log_file:
            process = subprocess.Popen(
                cmd,
                cwd=agent_path,
                stdout=log_file,
                stderr=log_file,
                env=os.environ.copy()
            )
            preview_processes[session_id] = process
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch preview: {str(e)}")

    time.sleep(2)

    return JSONResponse({
        "message": f"{ui.capitalize()} preview started",
        "session_id": session_id,
        "preview_url": preview_url,
        "pid": process.pid,
        "log_file": f"/{agent_path}/preview.log"
    })
