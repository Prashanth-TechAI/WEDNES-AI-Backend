import os
import subprocess
import time
from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse
from ..utils.path_utils import get_agent_output_dir
from ..utils.process_kill import kill_process_on_port

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
    elif "gr.Interface" in content:
        return "gradio"
    return "unknown"

@router.post("/previews/{session_id}/start")
def start_preview(session_id: str):
    agent_path, _ = get_agent_output_dir(session_id)
    main_path = os.path.join(agent_path, "main.py")

    if not os.path.exists(main_path):
        raise HTTPException(status_code=404, detail="main.py not found in session directory")

    try:
        sanitize_main_py(main_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sanitize main.py: {str(e)}")

    try:
        ui = detect_ui_framework(main_path)

        if ui == "streamlit":
            port = 8501
            preview_url = f"http://localhost:{port}"
            cmd = [
                "streamlit", "run", "main.py",
                "--server.port", str(port),
                "--server.headless", "true"
            ]
        elif ui == "gradio":
            port = 7860
            preview_url = f"http://127.0.0.1:{port}/"
            cmd = ["python", "main.py"]
        else:
            raise HTTPException(status_code=400, detail="Unknown UI framework in main.py")

        # Kill any process on the desired port before launching
        kill_process_on_port(port)

        process = subprocess.Popen(
            cmd,
            cwd=agent_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        preview_processes[session_id] = process

        log_file = os.path.join(agent_path, "preview.log")
        with open(log_file, "wb") as f:
            f.write(f"[{ui.upper()} Preview] Session: {session_id}\n\n".encode())
            # Start logging process output
            subprocess.Popen(
                ["tee", log_file],
                stdin=process.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        time.sleep(2)

        return JSONResponse({
            "message": f"{ui.capitalize()} preview started",
            "session_id": session_id,
            "preview_url": preview_url,
            "pid": process.pid,
            "log_file": log_file
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start preview: {str(e)}")
