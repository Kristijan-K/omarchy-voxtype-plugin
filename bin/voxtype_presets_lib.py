"""Shared helpers for the voxtype presets scripts (CLI, GTK popup, TUI).

Installed to ~/.local/bin alongside the other scripts; they add this file's
directory to sys.path and import it as `voxtype_presets_lib`.
"""

import json
from pathlib import Path

PRESETS = Path.home() / ".config/voxtype/presets.json"
STATE = Path.home() / ".config/voxtype/presets-state.json"
THEME_DIR = Path.home() / ".local/state/omarchy/current/theme"

DEFAULT_THEME = {
    "background": "#1a1b26",
    "foreground": "#a9b1d6",
    "accent": "#7aa2f7",
    "urgent": "#f7768e",
    "muted": "#565f89",
}


def load():
    try:
        return json.loads(PRESETS.read_text())
    except Exception:
        return {"active": "", "presets": []}


def save(data):
    PRESETS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def parse_toml_flat(path):
    """Flatten a simple TOML file into 'section.key' -> stripped string."""
    data = {}
    section = ""
    if not path.exists():
        return data
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            data[f"{section}.{key.strip()}"] = value.strip().strip('"')
    return data


def hex_to_rgba(hex_color, alpha):
    """'#a9b1d6' + 0.08 -> 'rgba(169,177,214,0.08)'."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    try:
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        r, g, b = 169, 177, 214
    return f"rgba({r},{g},{b},{alpha})"


def theme_colors():
    """Resolve the Omarchy palette the same way qs.Commons Color does."""
    colors = parse_toml_flat(THEME_DIR / "colors.toml")
    shell = parse_toml_flat(THEME_DIR / "shell.toml")

    background = colors.get("background", DEFAULT_THEME["background"])
    foreground = colors.get("foreground", DEFAULT_THEME["foreground"])
    accent = colors.get("accent", DEFAULT_THEME["accent"])
    urgent = colors.get("red", DEFAULT_THEME["urgent"])
    muted = colors.get("dark_foreground", DEFAULT_THEME["muted"])

    selected_bg = shell.get("menu.selected-background", foreground)
    try:
        selected_alpha = max(0.0, min(1.0, float(
            shell.get("menu.selected-background-alpha", "0.08"))))
    except ValueError:
        selected_alpha = 0.08

    return {
        "background": background,
        "foreground": foreground,
        "accent": accent,
        "urgent": urgent,
        "muted": muted,
        "popup_bg": shell.get("popups.background", background),
        "popup_fg": shell.get("popups.text", foreground),
        "selected_row_bg": hex_to_rgba(selected_bg, selected_alpha),
        "selected_row_fg": shell.get("menu.selected-text", accent),
        "hover_bg": hex_to_rgba(foreground, 0.05),
        "border": hex_to_rgba(foreground, 0.25),
        "font_size": shell.get("font.base-size", "12"),
    }
