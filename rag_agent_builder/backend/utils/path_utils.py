import os
from uuid import uuid4

BASE_OUTPUT_DIR = os.path.join("rag_agent_builder", "generated_agents")

def get_agent_output_dir(session_id: str = None) -> str:
    session_id = session_id or str(uuid4())
    path = os.path.join(BASE_OUTPUT_DIR, session_id)
    os.makedirs(path, exist_ok=True)
    return path, session_id
