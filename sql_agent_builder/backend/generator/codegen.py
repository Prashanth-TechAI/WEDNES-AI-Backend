import os
import traceback
import logging
import requests
from dotenv import load_dotenv
from ..state.session_store import get_session
from ..utils.path_utils import get_agent_output_dir  # ✅ Path utility

load_dotenv()

logging.basicConfig(level=logging.INFO)

LLM_API_KEY = os.getenv("GROQ_API_KEY")
assert LLM_API_KEY, "Missing GROQ_API_KEY in .env"

LLM_URL = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


def build_final_prompt(combined_code: str, system_prompt: str, ui: str, source_type: str, source_details: dict) -> str:
    # ✅ Correct template path
    template_path = "sql_agent_builder/backend/templates/combined/main_embed.py"
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Structure template not found at: {template_path}")

    with open(template_path, "r") as f:
        structure_reference = f.read()

    source_info = ""
    if source_type == "csv":
        source_info = f"CSV file path: {source_details.get('csv_path', '')}"
    elif source_type == "excel":
        source_info = f"Excel file path: {source_details.get('excel_path', '')}"
    elif source_type == "postgres":
        source_info = f"Postgres URI: {source_details.get('pg_uri', '')}"
    elif source_type == "mysql":
        source_info = f"MySQL URI: {source_details.get('mysql_uri', '')}"
    elif source_type == "sqlite":
        source_info = f"SQLite database path: {source_details.get('sqlite_path', '')}"

    return f"""
{system_prompt}

You are a senior Python developer. Generate a complete `{ui}` app named main.py for an SQL-based chatbot.

Requirements:
- Use the provided structural reference exactly.
- Integrate the logic from the component code.
- Connect to the data source using the following details:
  {source_info}
- Match the UI type: generate a valid {ui} UI (Streamlit or Gradio).
- Use the following combined component logic:
{combined_code}
- Do not include markdown, comments, or explanations.

=== Structure Reference ===

{structure_reference}

=== Combined Component Logic ===

{combined_code}

Output: a valid main.py Python script.
"""


def render_agent(session_id: str) -> str:
    config = get_session(session_id)
    output_dir, _ = get_agent_output_dir(session_id)  # ✅ use central path utility
    all_py_path = os.path.join(output_dir, "all.py")

    try:
        required = ["source_type", "source_details", "llm_provider", "llm_model", "system_prompt", "framework", "ui"]
        missing = [r for r in required if r not in config or not config[r]]
        if missing:
            raise ValueError(f"Missing required configurations: {', '.join(missing)}")

        with open(all_py_path, "r") as f:
            combined_code = f.read()

        prompt = build_final_prompt(
            combined_code=combined_code,
            system_prompt=config["system_prompt"],
            ui=config["ui"],
            source_type=config["source_type"],
            source_details=config["source_details"]
        )

        response = requests.post(
            LLM_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a senior Python engineer. Only output valid Python code—no markdown, no comments."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60,
        )
        response.raise_for_status()
        main_code = response.json()["choices"][0]["message"]["content"]

        # Save generated files
        with open(os.path.join(output_dir, "main.py"), "w") as f:
            f.write(main_code)

        with open(os.path.join(output_dir, "config.json"), "w") as f:
            import json
            json.dump(config, f, indent=2)

        with open(os.path.join(output_dir, ".env"), "w") as f:
            f.write(f"LLM_API_KEY={config.get('llm_key', '')}\n")
            details = config.get("source_details", {})
            source_type = config.get("source_type")

            if source_type in ["postgres", "mysql"]:
                f.write(f"DB_HOST={details.get('db_host')}\n")
                f.write(f"DB_NAME={details.get('db_name')}\n")
                f.write(f"DB_USER={details.get('db_user')}\n")
                f.write(f"DB_PASSWORD={details.get('db_password')}\n")
                f.write(f"DB_PORT={details.get('db_port')}\n")
            elif source_type == "sqlite":
                f.write(f"SQLITE_PATH={details.get('db_path')}\n")
            elif source_type in ["csv", "excel"]:
                f.write(f"FILE_PATH={details.get('file_path')}\n")

        with open(os.path.join(output_dir, "requirements.txt"), "w") as f:
            f.write("\n".join([
                "streamlit",
                "gradio",
                "python-dotenv",
                "pandas",
                "psycopg2-binary",
                "requests",
                "openpyxl",
                "sqlite3",
                "mysql-connector-python",
                "pandasai",
                "langchain-groq"
            ]))

        return output_dir

    except Exception as e:
        logging.error(f"[render_agent] Agent generation failed: {str(e)}")
        traceback.print_exc()
        raise ValueError(f"Failed to generate agent: {traceback.format_exc()}")
