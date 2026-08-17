#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$ROOT_DIR/omarchy-plugin"
PLUGIN_ID="$(jq -r '.id' "$SOURCE_DIR/manifest.json")"
TARGET_DIR="$HOME/.config/omarchy/plugins/$PLUGIN_ID"

omarchy plugin validate "$SOURCE_DIR"

# QML plugin files
mkdir -p "$TARGET_DIR"
find "$TARGET_DIR" -maxdepth 1 -type f -delete
cp "$SOURCE_DIR"/* "$TARGET_DIR/"

# CLI + TUI scripts
mkdir -p "$HOME/.local/bin"
install -m 755 "$ROOT_DIR/bin/omarchy-voxtype-presets" "$HOME/.local/bin/omarchy-voxtype-presets"
install -m 755 "$ROOT_DIR/bin/voxtype-presets" "$HOME/.local/bin/voxtype-presets"
install -m 644 "$ROOT_DIR/bin/voxtype_presets_lib.py" "$HOME/.local/bin/voxtype_presets_lib.py"

# Retired pieces from the GTK-popup iteration
rm -f "$HOME/.local/bin/voxtype-presets-gui.py" \
      "$HOME/.local/bin/voxtype-presets-edit" \
      "$HOME/.config/hypr/conf.d/voxtype-presets.conf"
hyprctl reload

# Seed the default preset from the current voxtype config on first install
omarchy-voxtype-presets seed
# Clean legacy preset fields (keywords/copy/pause) if an older version ran
omarchy-voxtype-presets migrate >/dev/null

# Rescanning does not reconstruct an already enabled QML component. Disable
# first so local installs always load the files that were just copied.
if omarchy plugin list --json | jq -e --arg id "$PLUGIN_ID" '.[] | select(.id == $id and .enabled == true)' >/dev/null; then
  omarchy plugin disable "$PLUGIN_ID"
fi
omarchy-shell shell rescanPlugins

omarchy plugin enable "$PLUGIN_ID"
omarchy bar move "$PLUGIN_ID" --section right
echo "Installed $PLUGIN_ID from $SOURCE_DIR"
