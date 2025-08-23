from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from ..state.session_store import update_session, get_session
from ..utils.helpers import render_and_save_section
import os
import logging
from uuid import uuid4
from urllib.parse import urlparse

router = APIRouter(prefix="/api", tags=["Config"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_config")

from ..utils.path_utils import get_agent_output_dir


def _tpl_name(section: str, raw: str) -> str:
    """Map user-facing choices to real template filenames."""
    if section == "source":
        return {
            "xls":  "excel",
            "xlsx": "excel",
            "txt":  "csv",
        }.get(raw, raw)
    if section == "embedding":
        return "openai_embedding" if raw == "openai" else "sentence_transformers"
    return raw

@router.post("/source")
def select_source_type(session_id: str = Form(...), source_type: str = Form(...)):
    valid = {"pdf", "csv", "excel", "text_file", "postgres", "mysql", "mongo", "sqlite"}
    if source_type not in valid:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    update_session(session_id, "source", {"type": source_type})
    cfg = get_session(session_id)
    render_and_save_section("source", _tpl_name("source", source_type), cfg, session_id)

    return {"message": f"Source type '{source_type}' recorded and template rendered."}

@router.post("/source/upload")
async def upload_source_file(session_id: str = Form(...), file: UploadFile = File(...)):
    cfg = get_session(session_id)
    src_type = cfg.get("source", {}).get("type", "")

    if src_type not in {"pdf", "txt", "csv", "excel", "text_file"}:
        raise HTTPException(status_code=400, detail="Current source type does not support file upload.")

    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        raise HTTPException(status_code=400, detail="File must have an extension.")

    dest_dir, _ = get_agent_output_dir(session_id)
    dest_path = os.path.join(dest_dir, f"data{ext}")

    with open(dest_path, "wb") as fh:
        fh.write(await file.read())

    update_session(session_id, "source_file", dest_path)

    cfg = get_session(session_id)
    render_and_save_section("source", _tpl_name("source", src_type), cfg, session_id)

    return {"message": f"Uploaded to {dest_path} and template updated."}

@router.post("/source/db")
def configure_source_db(
    session_id: str = Form(...),
    source_type: str = Form(...),
    uri: str = Form(...),
    database: str = Form(...),
    collection_or_table: str = Form(...)
):
    if source_type not in {"postgres", "mysql", "mongo", "sqlite"}:
        raise HTTPException(status_code=400, detail="Unsupported DB type.")

    parsed = urlparse(uri)
    source_cfg = {
        "type": source_type,
        "uri": uri,
        "database": database,
        "collection_or_table": collection_or_table,
        "scheme": parsed.scheme,
        "host": parsed.hostname or "",
        "port": parsed.port or 5432,
        "user": parsed.username or "",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or database,
        "table": collection_or_table
    }

    update_session(session_id, "source", source_cfg)
    cfg = get_session(session_id)

    render_and_save_section("source", _tpl_name("source", source_type), cfg, session_id)

    return {"message": f"DB source '{source_type}' configured and template rendered."}

@router.post("/embeddings/model")
def set_embedding_model(session_id: str = Form(...), model_name: str = Form(...)):
    emb_type = "openai" if "openai" in model_name.lower() else "sentence_transformers"
    update_session(session_id, "embedding",
                   {"type": emb_type, "model_name": model_name})

    cfg = get_session(session_id)
    render_and_save_section("embedding", _tpl_name("embedding", emb_type), cfg, session_id)
    return {"message": f"Embedding model '{model_name}' set and template rendered."}

@router.post("/vectordb")
def choose_vector_db(session_id: str = Form(...), vector_db: str = Form(...)):
    if vector_db not in {"pinecone", "milvus", "qdrant", "faiss", "chromadb"}:
        raise HTTPException(status_code=400, detail="Invalid vector DB")
    update_session(session_id, "vector_store", {"type": vector_db})
    return {"message": f"Vector DB '{vector_db}' selected."}

@router.post("/vectordb/credentials/remote")
def configure_remote_vectordb(
    session_id: str = Form(...),
    api_key: str = Form(...),
    environment: str = Form(...),
    index_name: str = Form(...)
):
    update_session(session_id, "vector_store",
                   {"type": "pinecone", "api_key": api_key,
                    "environment": environment, "index_name": index_name})

    cfg = get_session(session_id)
    render_and_save_section("vector_store", "pinecone", cfg, session_id)
    return {"message": "Pinecone credentials saved and template rendered."}

@router.post("/vectordb/credentials/local")
def configure_local_vectordb(
    session_id: str = Form(...),
    vector_db: str = Form(...),
    url: str = Form(...),
    dimensions: int = Form(384),
    distance_metric: str = Form("cosine")
):
    if vector_db not in {"faiss", "chromadb", "qdrant", "milvus"}:
        raise HTTPException(status_code=400, detail="Invalid local vector DB")

    collection_name = f"rag_{uuid4().hex[:8]}"

    update_session(
        session_id,
        "vector_store",
        {
            "type":            vector_db,
            "url":             url if url.startswith("http") else f"http://{url}",
            "collection_name": collection_name,
            "dimensions":      dimensions,
            "distance_metric": distance_metric.lower(),
        },
    )

    cfg = get_session(session_id)
    render_and_save_section("vector_store", vector_db, cfg, session_id)

    return {
        "message": (
            f"{vector_db} configured. "
            f"Collection <{collection_name}> will be created on first ingest."
        )
    }

@router.post("/llm/provider")
def set_llm_provider(session_id: str = Form(...), provider: str = Form(...)):
    if provider not in {"openai", "groq", "gemini"}:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    update_session(session_id, "llm", {"type": provider, "provider": provider})
    return {"message": f"LLM provider '{provider}' recorded. Awaiting credentials."}

@router.post("/llm/credentials")
def set_llm_credentials(session_id: str = Form(...), api_key: str = Form(...), model_name: str = Form(...)):
    cfg = get_session(session_id)
    llm_cfg = cfg.get("llm", {})
    if not llm_cfg.get("type"):
        raise HTTPException(status_code=400, detail="Set provider first")

    llm_cfg.update({"api_key": api_key, "model_name": model_name})
    update_session(session_id, "llm", llm_cfg)

    cfg = get_session(session_id)
    render_and_save_section("llm", llm_cfg["type"],    cfg, session_id)
    render_and_save_section("models", model_name,      cfg, session_id)
    return {"message": "LLM credentials saved and templates rendered."}

@router.post("/system-prompt")
def set_system_prompt(session_id: str = Form(...), prompt: str = Form(...)):
    update_session(session_id, "system_prompt", prompt)
    cfg = get_session(session_id)
    render_and_save_section("prompt", "default", cfg, session_id)
    return {"message": "System prompt updated and template rendered."}

@router.post("/ui")
def select_ui_framework(session_id: str = Form(...), ui: str = Form(...)):
    if ui not in {"streamlit", "gradio"}:
        raise HTTPException(status_code=400, detail="Invalid UI")
    update_session(session_id, "ui", {"type": ui})
    cfg = get_session(session_id)
    render_and_save_section("ui", ui, cfg, session_id)
    return {"message": f"UI '{ui}' configured and template rendered."}
