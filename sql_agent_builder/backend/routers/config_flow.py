from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from ..state.session_store import update_session, get_session
from ..utils.helpers import render_and_save_section
import os
from urllib.parse import urlparse
import shutil
from ..utils.path_utils import get_agent_output_dir

router = APIRouter()

@router.post("/source")
def set_source(session_id: str = Form(...), source_type: str = Form(...)):
    update_session(session_id, "source_type", source_type)
    update_session(session_id, "source", source_type)
    return {"message": f"Source type '{source_type}' set."}

@router.post("/source-details")
def upload_source_details(
    session_id: str = Form(...),
    file: UploadFile = File(None),
    db_uri: str = Form(None),
    db_name: str = Form(None),
    table_name: str = Form(None)
):
    config = get_session(session_id)
    source_type = config.get("source_type")

    if not source_type:
        raise HTTPException(status_code=400, detail="Source type must be set before uploading source details.")

    output_path, _ = get_agent_output_dir(session_id)

    if source_type in ["csv", "excel"]:
        if not file:
            raise HTTPException(status_code=400, detail="File is required for CSV/Excel source.")

        try:
            filename = "data.csv" if source_type == "csv" else "data.xlsx"
            output_file = os.path.join(output_path, filename)

            with open(output_file, "wb") as f_out:
                shutil.copyfileobj(file.file, f_out)

            update_session(session_id, "source_details", {"file_path": filename})
            render_and_save_section("source", source_type, config, session_id)

            return {"message": f"{source_type.upper()} file uploaded and source.py rendered."}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

@router.post("/source-details/db")
def upload_db_config(
    session_id: str = Form(...),
    db_uri: str = Form(...),
    db_name: str = Form(...),
    table_name: str = Form(...)
):
    config = get_session(session_id)
    source_type = config.get("source_type")

    if source_type not in ["postgres", "mysql", "sqlite"]:
        raise HTTPException(status_code=400, detail="Invalid source type for DB config.")

    try:
        parsed = urlparse(db_uri)

        db_details = {
            "db_host": parsed.hostname,
            "db_user": parsed.username,
            "db_password": parsed.password,
            "db_port": parsed.port or (5432 if source_type == "postgres" else 3306),
            "db_name": db_name,
            "table_name": table_name
        }

        if source_type == "sqlite":
            db_details["db_path"] = f"generated_agents/{session_id}/{db_name}.db"

        update_session(session_id, "source_details", db_details)
        render_and_save_section("source", source_type, config, session_id)

        return {"message": f"Database credentials saved and source.py rendered for {source_type}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse DB URI or render template: {str(e)}")


@router.post("/llm")
def set_llm(session_id: str = Form(...), llm_provider: str = Form(...)):
    update_session(session_id, "llm_provider", llm_provider)
    update_session(session_id, "llm", llm_provider)

    config = get_session(session_id)
    try:
        render_and_save_section("llm", llm_provider, config, session_id)
        return {"message": f"LLM provider '{llm_provider}' set and llm.py rendered."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template rendering failed: {str(e)}")

@router.post("/llm-key")
def set_llm_key(session_id: str = Form(...), api_key: str = Form(...)):
    update_session(session_id, "llm_key", api_key)

    config = get_session(session_id)
    llm_provider = config.get("llm_provider")
    if llm_provider:
        try:
            render_and_save_section("llm", llm_provider, config, session_id)
            return {"message": "LLM API key saved and llm.py updated."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Template rendering failed: {str(e)}")

    return {"message": "LLM API key saved."}


@router.post("/model")
def set_model(session_id: str = Form(...), model: str = Form(...)):
    update_session(session_id, "llm_model", model)
    update_session(session_id, "model", model)

    config = get_session(session_id)
    try:
        render_and_save_section("model", model, config, session_id)
        return {"message": f"Model '{model}' set and model.py rendered."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template error: {str(e)}")

@router.post("/system-prompt")
def set_system_prompt(session_id: str = Form(...), prompt: str = Form(...)):
    update_session(session_id, "system_prompt", prompt)

    config = get_session(session_id)
    try:
        render_and_save_section("prompt", "default", config, session_id)
        return {"message": f"System prompt set and prompt.py rendered."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt rendering error: {str(e)}")

@router.post("/framework")
def set_framework(session_id: str = Form(...), framework: str = Form(...)):
    update_session(session_id, "framework", framework)

    config = get_session(session_id)
    try:
        render_and_save_section("framework", framework, config, session_id)
        return {"message": f"Framework '{framework}' set and framework.py rendered."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template error: {str(e)}")

@router.post("/ui")
def set_ui(session_id: str = Form(...), ui: str = Form(...)):
    update_session(session_id, "ui", ui)

    config = get_session(session_id)
    try:
        render_and_save_section("ui", ui, config, session_id)
        return {"message": f"UI '{ui}' set and ui.py rendered."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template error: {str(e)}")