"""Shared helpers for the voxtype presets scripts (CLI, GTK popup, TUI).

Loaded from the plugin's `bin/` directory by the CLI and TUI scripts.
"""

import json
import os
import re
import subprocess
from pathlib import Path

PRESETS = Path.home() / ".config/voxtype/presets.json"
STATE = Path.home() / ".config/voxtype/presets-state.json"
CONFIG = Path(os.environ.get("VOXTYPE_CONFIG", str(Path.home() / ".config/voxtype/config.toml")))
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
            key = key.strip()
            data[f"{section}.{key}" if section else key] = value.strip().strip('"')
    return data


def config_defaults():
    """Return the current global keyword prompt and media-pause setting."""
    values = parse_toml_flat(CONFIG)
    prompt = values.get("whisper.initial_prompt", "")
    prefix = "Use these terms exactly when dictated:"
    if prompt.startswith(prefix):
        prompt = prompt[len(prefix):].strip()
    pause = values.get("audio.pause_media", "true").strip().lower()
    return prompt, pause not in {"false", "0", "no", "off"}


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


WHISPER_MODELS = {
    "tiny", "tiny.en", "base", "base.en", "small", "small.en",
    "medium", "medium.en", "large-v3", "large-v3-turbo",
}


def ensure_model(model):
    """Download a voxtype model if it is not present yet.

    Whisper models are downloaded directly because Voxtype 0.7.5 confuses
    Whisper ``small`` with its optional SenseVoice model. Other engine models
    use Voxtype's setup command. Returns (ok, error_message).
    """
    if model in WHISPER_MODELS:
        # Voxtype 0.7.5 incorrectly classifies Whisper "small" as the
        # optional SenseVoice model with the same short name. Download the
        # Whisper artifact directly until that upstream collision is fixed.
        data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
        models_dir = data_home / "voxtype" / "models"
        destination = models_dir / f"ggml-{model}.bin"
        if destination.exists() and destination.stat().st_size > 0:
            return True, ""
        models_dir.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".part")
        url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{destination.name}"
        try:
            result = subprocess.run(
                ["curl", "--fail", "--location", "--retry", "2",
                 "--connect-timeout", "15", "--output", str(partial), url],
                capture_output=True, text=True, timeout=7200)
        except FileNotFoundError:
            return False, "curl is not installed"
        except subprocess.TimeoutExpired:
            partial.unlink(missing_ok=True)
            return False, "download timed out"
        if result.returncode != 0:
            partial.unlink(missing_ok=True)
            return False, (result.stderr or result.stdout or "download failed").strip()
        if not partial.exists() or partial.stat().st_size == 0:
            partial.unlink(missing_ok=True)
            return False, "download produced an empty file"
        partial.replace(destination)
        return True, ""

    try:
        result = subprocess.run(
            ["voxtype", "setup", "--download", "--model", model, "--quiet"],
            capture_output=True, text=True, timeout=7200)
    except subprocess.TimeoutExpired:
        return False, "download timed out"
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "download failed").strip()
    return True, ""


def theme_colors():
    """Resolve the Omarchy palette the same way qs.Commons Color does."""
    colors = parse_toml_flat(THEME_DIR / "colors.toml")
    shell = parse_toml_flat(THEME_DIR / "shell.toml")
    gum = {}
    gum_path = THEME_DIR / "gum_env.lua"
    if gum_path.exists():
        for line in gum_path.read_text().splitlines():
            match = re.search(r'hl\.env\("(GUM_[A-Z0-9_]+)", "([^"]+)"\)', line)
            if match:
                gum[match.group(1)] = match.group(2)

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
        "selected_fg": gum.get("GUM_CHOOSE_SELECTED_FOREGROUND", foreground),
        "selected_bg": gum.get("GUM_CHOOSE_SELECTED_BACKGROUND", background),
        "selected_row_bg": hex_to_rgba(selected_bg, selected_alpha),
        "selected_row_fg": shell.get("menu.selected-text", accent),
        "hover_bg": hex_to_rgba(foreground, 0.05),
        "border": hex_to_rgba(foreground, 0.25),
        "font_size": shell.get("font.base-size", "12"),
    }
