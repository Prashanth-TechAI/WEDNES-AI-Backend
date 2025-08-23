import os
from jinja2 import Environment, FileSystemLoader
from ..state.session_store import get_session

TEMPLATE_DIR = "backend/templates"

def append_rendered_template(session_id: str, section: str, variant: str):
    config = get_session(session_id)
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), trim_blocks=True, lstrip_blocks=True)
    template_path = f"{section}/{variant}.j2"
    tpl = env.get_template(template_path)
    rendered_code = tpl.render(config=config)

    all_py_path = os.path.join(f"generated_agents/{session_id}", "all.py")
    os.makedirs(os.path.dirname(all_py_path), exist_ok=True)

    with open(all_py_path, "a") as f:
        f.write(f"\n\n# === {section}/{variant}.j2 ===\n")
        f.write(rendered_code)
        f.write("\n")
