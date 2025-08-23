from fastapi import APIRouter, Form, HTTPException
from ..state.session_store import get_session, update_session
from ..generator.codegen import render_agent

router = APIRouter(prefix="/api", tags=["Builder"])

FILE_BASED_SOURCES = {"pdf", "csv", "xls", "xlsx", "txt"}
DB_BASED_SOURCES = {"sqlite", "postgres", "mysql", "mongo"}

@router.post("/build/agent")
def build_agent(session_id: str = Form(...)):
    config = get_session(session_id)
    if not config:
        raise HTTPException(status_code=404, detail="No session found")

    missing = []

    for key in ["source", "embedding", "vector_store", "ui", "system_prompt"]:
        if key not in config or not config[key]:
            missing.append(key)

    source_conf = config.get("source", {})
    source_type = source_conf.get("type", "")

    if not source_type:
        missing.append("source.type")
    elif source_type in FILE_BASED_SOURCES:
        if not config.get("source_file"):
            missing.append("source_file")
    elif source_type in DB_BASED_SOURCES:
        if source_type == "sqlite":
            if not source_conf.get("db_path"):
                missing.append("source.db_path")
        else:
            for field in ["uri", "database", "collection_or_table"]:
                if not source_conf.get(field):
                    missing.append(f"source.{field}")

    llm_conf = config.get("llm", {})
    if not isinstance(llm_conf, dict):
        llm_conf = {}

    llm_conf.setdefault("type", config.get("llm_provider"))
    llm_conf.setdefault("api_key", config.get("llm_key"))
    llm_conf.setdefault("model_name", config.get("llm_model"))

    update_session(session_id, "llm", llm_conf)

    for field in ["type", "api_key", "model_name"]:
        if not llm_conf.get(field):
            missing.append(f"llm.{field}")

    ui_type = config.get("ui", {}).get("type", "")
    if ui_type not in {"streamlit", "gradio"}:
        missing.append("ui.type")

    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required configuration: {missing}")

    try:
        output_path = render_agent(session_id)
        return {
            "message": "Agent built successfully.",
            "path": output_path,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build failed: {str(e)}")
