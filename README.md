# omarchy-voxtype-plugin

Omarchy Quattro bar plugin for switching between user-defined **Voxtype
presets** — model, language, vocabulary keywords, output mode, and media
pause — with a real config reload.

- **Bar widget** (`io.github.kkosu.voxtype-presets`): shows the active preset
  name. **Left click** cycles to the next preset, **right click** opens the
  GTK4 preset manager popup (a standalone floating window themed from the
  current Omarchy theme, not a Quickshell panel).
- **Keybind**: `SUPER + CTRL + ALT + V` cycles presets (added to
  `~/.config/hypr/bindings.lua`).
- **Presets** are stored in `~/.config/voxtype/presets.json`; applying one
  patches `~/.config/voxtype/config.toml` (comments preserved, timestamped
  backup) and restarts the `voxtype.service` user daemon — the only reload
  voxtype currently supports.

## Popup keyboard controls

| Keys            | Action                          |
|-----------------|---------------------------------|
| `↑` `↓` / `j` `k` | Move between presets          |
| `Enter`         | Apply the selected preset       |
| `a`             | Add a preset (opens the TUI editor) |
| `e`             | Edit the selected preset (same TUI) |
| `d`             | Delete (confirm with `y` / `n`, Esc = no) |
| `Esc`           | Close the popup                 |

`a` / `e` open `voxtype-presets-edit` in the same floating presentation
terminal the Dictation indicator uses for `voxtype configure` — a TUI with
tabs styled from the current Omarchy theme:

| Keys            | Action                                   |
|-----------------|------------------------------------------|
| `←` `→` / `Tab` / `Shift+Tab` | Switch tab (Model / Language / Keywords / Output) |
| `j` `k` / `↑` `↓` | Move between items / toggle rows      |
| `Enter` / `Space` | Select model or language, start keyword editing, toggle checkboxes |
| `s` / `Ctrl+S`  | Save (re-applies when the preset is active) |
| `q` / `Esc`     | Quit without saving                      |

## Preset fields

| Field            | config.toml mapping                          |
|------------------|----------------------------------------------|
| name             | preset identifier (shown in the bar)         |
| model            | `[whisper] model`                            |
| language         | `[whisper] language`                         |
| keywords         | `[whisper] initial_prompt` vocabulary hints  |
| copyToClipboard  | `[output] mode` = `clipboard` or `type`      |
| pauseMedia       | `[audio] pause_media` (MPRIS pause)          |

## Install

```bash
./install-local.sh
```

This validates the plugin folder, copies the QML into
`~/.config/omarchy/plugins/io.github.kkosu.voxtype-presets/`, installs the CLI
and popup into `~/.local/bin/`, adds the floating Hyprland windowrule for the
popup to `~/.config/hypr/conf.d/voxtype-presets.conf` (then reloads Hyprland),
seeds `english` (from your current voxtype
config) and `icelandic` presets on first run, then enables the widget in the
bar's right section.

### Keybind

Add once to `~/.config/hypr/bindings.lua`, then `hyprctl reload`:

```lua
o.bind("SUPER + CTRL + ALT + V", "Cycle voxtype preset", "omarchy-voxtype-presets cycle")
```

## CLI

```bash
omarchy-voxtype-presets list          # presets.json
omarchy-voxtype-presets state         # active preset one-liner
omarchy-voxtype-presets cycle         # apply next preset
omarchy-voxtype-presets apply <name>  # apply specific preset
omarchy-voxtype-presets watch         # stream state (used by the bar widget)
omarchy-voxtype-presets gui           # open the GTK4 manager popup
omarchy-voxtype-presets seed          # first-run preset seeding
```

## Debugging

```bash
omarchy plugin list --json | jq '.[] | select(.id == "io.github.kkosu.voxtype-presets")'
omarchy-shell shell rescanPlugins
qs log -p /usr/share/omarchy/shell --tail 100
```
