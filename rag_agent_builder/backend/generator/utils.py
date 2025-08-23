from ..state.session_store import get_session
from jinja2 import Environment, FileSystemLoader
import os

TEMPLATE_DIR = "backend/templates"

def append_rendered_template(session_id: str, section: str, variant: str):
    config = get_session(session_id)
    template_path = f"{section}/{variant}.j2"

    if section == "llm":
        llm = config.get("llm", {})
        if not llm.get("api_key") or not llm.get("model_name"):
            print(f"[skip] Not rendering {template_path} – LLM config incomplete.")
            return
        print(f"[DEBUG] Rendering: {template_path} with config:")
        print(config)

    if section == "models":
        llm = config.get("llm", {})
        if not llm.get("model_name"):
            print(f"[skip] Not rendering model template – model_name missing.")
            return

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), trim_blocks=True, lstrip_blocks=True)
    tpl = env.get_template(template_path)
    rendered_code = tpl.render(config=config)

    all_py_path = os.path.join(f"generated_agents/{session_id}", "all.py")
    os.makedirs(os.path.dirname(all_py_path), exist_ok=True)

    marker = f"# === {section}/{variant}.j2 ==="
    if os.path.exists(all_py_path):
        with open(all_py_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        inside = False
        for line in lines:
            if line.strip() == marker:
                inside = True
                continue
            if inside and line.strip().startswith("# ==="):
                inside = False
                new_lines.append(line)
                continue
            if not inside:
                new_lines.append(line)

        with open(all_py_path, "w") as f:
            f.writelines(new_lines)

    with open(all_py_path, "a") as f:
        f.write(f"\n\n{marker}\n")
        f.write(rendered_code)
        f.write("\n")
