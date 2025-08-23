from fastapi import APIRouter, Form, HTTPException
from ..state.session_store import get_session
from ..generator.codegen import render_agent
import os
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

router = APIRouter(prefix="/api", tags=["Builder"])

@router.post("/build/agent")
def build_agent(session_id: str = Form(...)):
    try:
        config = get_session(session_id)
        if not config:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No session found")

        required_fields = ["source", "llm", "model", "framework", "ui"]
        missing_fields = [field for field in required_fields if field not in config or not config[field]]

        if missing_fields:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Missing required configuration: {missing_fields}")

        # Check if source details are properly configured
        source_type = config.get("source_type")
        source_details = config.get("source_details")
        if not source_details:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Source details are missing")

        if source_type in ["csv", "excel"]:
            if "file_path" not in source_details:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Source file path is missing")

        elif source_type in ["postgres", "mysql", "sqlite"]:
            required_keys = ["db_host", "db_user", "db_password", "db_port", "db_name", "table_name"]
            if source_type == "sqlite":
                required_keys = ["db_path", "table_name"]

            missing = [key for key in required_keys if not source_details.get(key)]
            if missing:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Database credentials are incomplete: missing {missing}"
                )

        # Check if LLM configuration is complete
        if not all([config.get("llm_provider"), config.get("llm_key"), config.get("llm_model")]):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="LLM configuration is incomplete")

        # Check if UI is valid
        if config.get("ui") not in ["streamlit", "gradio"]:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid UI selection")

        # Render the agent
        agent_path = render_agent(session_id)
        if not agent_path:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to build agent")

        return {
            "status_code": HTTP_200_OK,
            "message": "Agent built successfully",
            "agent_path": agent_path,
            "session_id": session_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")
