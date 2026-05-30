import os
from pathlib import Path

ICONS = [
    "file_new", "file_open", "file_save", "view_3d", "view_levels",
    "settings", "tool_pilar", "tool_pantalla", "tool_losa", "tool_viga",
    "tool_carga", "tool_borrar", "tool_esc", "calc_solve", "res_deformada",
    "res_mxx", "res_myy", "group", "level", "level_active", "nav_up",
    "nav_down", "info"
]

SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24">
    <rect width="24" height="24" fill="#2E3A4E" rx="4" ry="4" />
</svg>"""

def main():
    root_dir = Path(__file__).resolve().parent.parent
    icons_dir = root_dir / "assets" / "icons"
    
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    for icon in ICONS:
        svg_path = icons_dir / f"{icon}.svg"
        if not svg_path.exists():
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(SVG_TEMPLATE)
            print(f"Created {svg_path.relative_to(root_dir)}")
        else:
            print(f"Already exists: {svg_path.relative_to(root_dir)}")

if __name__ == "__main__":
    main()
