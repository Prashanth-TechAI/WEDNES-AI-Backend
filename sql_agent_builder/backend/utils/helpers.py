import os
from jinja2 import Environment, FileSystemLoader
from ..utils.path_utils import get_agent_output_dir

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../templates")

def render_and_save_section(section: str, template: str, config: dict, session_id: str):
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    tpl_path = f"{section}/{template}.j2"
    tpl = env.get_template(tpl_path)
    content = tpl.render(config=config)

    dest_dir, _ = get_agent_output_dir(session_id)
    os.makedirs(dest_dir, exist_ok=True)

    all_py_path = os.path.join(dest_dir, "all.py")
    with open(all_py_path, "a") as f:
        f.write(f"\n\n# === {section}/{template}.j2 ===\n")
        f.write(content)
        f.write("\n")

    section_file_path = os.path.join(dest_dir, f"{section}.py")
    with open(section_file_path, "w") as f:
        f.write(content)
