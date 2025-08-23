import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from ..utils.path_utils import get_agent_output_dir

TEMPLATE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../templates"))

FILE_MAP = {
    "source":       "source.py",
    "embedding":    "embedding_model.py",
    "vector_store": "vector_db.py",
    "prompt":       "system_prompt.py",
    "ui":           "ui.py",
    "llm":          "llm.py",
    "models":       "llm.py",
}

def render_and_save_section(section: str, template: str, config: dict, session_id: str):
    env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT), trim_blocks=True, lstrip_blocks=True)
    rel_path = f"{section}/{template}.j2"

    try:
        tpl = env.get_template(rel_path)
    except TemplateNotFound as exc:
        raise FileNotFoundError(f"Template not found: {rel_path}") from exc

    rendered = tpl.render(config=config).rstrip() + "\n"

    sess_dir, _ = get_agent_output_dir(session_id)
    os.makedirs(sess_dir, exist_ok=True)

    for key, fname in FILE_MAP.items():
        if section.startswith(key):
            with open(os.path.join(sess_dir, fname), "w") as fh:
                fh.write(rendered)
            break

    marker = f"# === {section}/{template}.j2 ==="
    all_path = os.path.join(sess_dir, "all.py")
    new_lines, inside = [], False

    if os.path.exists(all_path):
        with open(all_path, "r") as fh:
            for line in fh:
                if line.strip() == marker:
                    inside = True
                    continue
                if inside and line.strip().startswith("# ==="):
                    inside = False
                if not inside:
                    new_lines.append(line)

    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    new_lines.extend([f"\n{marker}\n", rendered])

    with open(all_path, "w") as fh:
        fh.writelines(new_lines)

    return rendered
