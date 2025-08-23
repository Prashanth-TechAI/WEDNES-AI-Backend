import shutil
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..utils.path_utils import get_agent_output_dir

router = APIRouter()

@router.get("/builds/{session_id}/download")
def download_agent(session_id: str):
    folder, _ = get_agent_output_dir(session_id)

    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="Folder not found.")

    zip_path = f"/tmp/{session_id}.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)

    shutil.make_archive(f"/tmp/{session_id}", 'zip', folder)
    return FileResponse(zip_path, filename=f"{session_id}.zip", media_type="application/zip")
