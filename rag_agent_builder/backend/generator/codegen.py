# backend/generator/codegen.py
import os
import re
import json
import traceback
import logging
import requests
from jinja2 import Template, Environment, FileSystemLoader
from ..state.session_store import get_session
from ..utils.path_utils import get_agent_output_dir

logging.basicConfig(level=logging.INFO)

LLM_API_KEY = os.getenv("GROQ_API_KEY")
LLM_URL     = os.getenv("GROQ_URL",  "https://api.groq.com/openai/v1/chat/completions")
LLM_MODEL   = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

assert LLM_API_KEY, "Missing GROQ_API_KEY in .env"

SECTION_RE = re.compile(r"# === ([\w\-/\.]+\.j2) ===")

def _write_component(output_dir: str, section: str, code: str) -> None:
    file_map = {
        "source":       "source.py",
        "embedding":    "embedding_model.py",
        "vector_store": "vector_db.py",
        "prompt":       "system_prompt.py",
        "ui":           "ui.py",
        "llm":          "llm.py",
        "models":       "llm.py",
    }
    for key, fname in file_map.items():
        if section.startswith(key):
            path = os.path.join(output_dir, fname)
            with open(path, "w") as fh:
                fh.write(code.rstrip() + "\n")
            logging.info(f"[saved] → {path} (for reference only)")
            return
    logging.warning(f"[skip] Unknown section: {section}")

def _build_prompt(code_map: dict, system_prompt: str, source: dict) -> str:
    struct_path = os.path.join(os.path.dirname(__file__), "../templates/combined/main.py.j2")
    struct_path = os.path.abspath(struct_path)
    
    if not os.path.exists(struct_path):
        raise FileNotFoundError(f"Missing template structure: {struct_path}")
    structure = open(struct_path, "r").read()

    src_type = source.get("type", "unknown")
    src_human = {
        "pdf": "PDF file at `data.pdf`",
        "csv": "CSV file at `data.csv`",
        "xls": "Excel file",
        "xlsx": "Excel file",
        "mongo": "MongoDB collection",
        "postgres": "PostgreSQL table",
        "mysql": "MySQL table",
    }.get(src_type, "a supported data source")

    combined = "\n\n".join(
        f"# === {k}.py ===\n{code.strip()}" for k, code in code_map.items()
    )

    return f"""
{system_prompt}

You are a senior Python developer building a Retrieval-Augmented Generation (RAG) chatbot.

### Objective
Generate a **single, runnable `main.py`** file for the application.

### Critical Requirements
- The entire RAG pipeline must exist **in one file** (`main.py`)
- **Do not use `import` statements** like `from source_pdf import ...`
- Instead, **inline all logic directly** into `main.py` using the component code provided.
- Follow the provided structure exactly as the skeleton.
- Avoid code duplication — reuse class definitions sensibly.
- Output **pure Python only** — no markdown, no explanations, no comments.

### Data Source
Use: {src_human}

### Reference Structure (main.py.j2)
{structure}

### Component Logic (use inline in main.py)
{combined}
"""
def render_agent(session_id: str) -> str:
    try:
        config = get_session(session_id)
        
        if not config:
            raise ValueError("No session config found")

        config.setdefault("llm", {}).update({
            "type":       config.get("llm", {}).get("type")       or config.get("llm_provider"),
            "api_key":    config.get("llm", {}).get("api_key")    or config.get("llm_key"),
            "model_name": config.get("llm", {}).get("model_name") or config.get("llm_model"),
        })

        out_dir, _ = get_agent_output_dir(session_id)
        all_path  = os.path.join(out_dir, "all.py")
        
        if not os.path.exists(all_path):
            raise FileNotFoundError("Missing all.py – render components first")

        code_map: dict[str, str] = {}
        new_all: list[str] = []
        cur, buf = None, []

        def _flush():
            if cur is None:
                return
            sid       = cur.replace(".j2", "").replace("/", "_")
            rendered  = Template("".join(buf)).render(config=config)
            marker    = f"# === {cur} ==="
            new_all.extend([f"\n{marker}\n", rendered.rstrip(), "\n"])
            code_map[sid] = rendered
            _write_component(out_dir, sid, rendered)

        with open(all_path, "r") as fh:
            for line in fh:
                m = SECTION_RE.match(line.strip())
                if m:
                    _flush()
                    cur, buf = m.group(1), []
                else:
                    buf.append(line)
            _flush()

        with open(all_path, "w") as fh:
            fh.writelines(new_all)

        prov = config["llm"]["type"]
        env_llm   = Environment(loader=FileSystemLoader("backend/templates/llm"))
        env_model = Environment(loader=FileSystemLoader("backend/templates/models"))

        llm_logic = env_llm.get_template(f"{prov}.j2").render(config=config) \
                    if os.path.exists(f"backend/templates/llm/{prov}.j2") else ""

        model_name  = config["llm"]["model_name"]
        model_logic = env_model.get_template(f"{model_name}.j2").render(config=config) \
                      if os.path.exists(f"backend/templates/models/{model_name}.j2") \
                      else f'MODEL_NAME = "{model_name}"'

        with open(os.path.join(out_dir, "llm.py"), "w") as fh:
            fh.write(model_logic.rstrip() + "\n\n" + llm_logic.rstrip() + "\n")

        prompt = _build_prompt(code_map, config.get("system_prompt", ""), config["source"])

        resp = requests.post(
            LLM_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a senior Python engineer. Output only valid Python code."},
                    {"role": "user",   "content": prompt}
                ]
            },
            timeout=60,
        )
        resp.raise_for_status()
        main_code = resp.json()["choices"][0]["message"]["content"].strip()
        open(os.path.join(out_dir, "main.py"), "w").write(main_code)

        json.dump(config, open(os.path.join(out_dir, "config.json"), "w"), indent=2)

        reqs = {"python-dotenv", "requests"}
        reqs |= {"streamlit"}             if config["ui"]["type"] == "streamlit" else {"gradio"}
        reqs |= {"PyMuPDF"}               if config["source"]["type"] == "pdf" else set()
        reqs |= {"pandas", "openpyxl"}    if config["source"]["type"] in {"csv", "xls", "xlsx"} else set()
        reqs |= {"pymongo"}               if config["source"]["type"] == "mongo" else set()
        reqs |= {"psycopg2-binary"}       if config["source"]["type"] == "postgres" else set()
        reqs |= {"mysql-connector-python"}if config["source"]["type"] == "mysql" else set()
        reqs |= {"sentence-transformers"} if config["embedding"]["type"] == "sentence_transformers" else {"openai"}
        reqs |= {
            "pinecone":  {"pinecone-client"},
            "faiss":     {"faiss-cpu", "numpy"},
            "qdrant":    {"qdrant-client"},
            "milvus":    {"pymilvus"},
            "chromadb":  {"chromadb"},
        }.get(config["vector_store"]["type"], set())

        open(os.path.join(out_dir, "requirements.txt"), "w") \
            .writelines(sorted(pkg + "\n" for pkg in reqs))

        return out_dir

    except Exception as exc:
        logging.error(f"[render_agent] Error: {exc}")
        traceback.print_exc()
        raise ValueError(f"Build failed: {exc}") from exc
