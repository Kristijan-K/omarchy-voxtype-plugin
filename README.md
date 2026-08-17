# omarchy-voxtype-plugin

Omarchy Quattro bar plugin for switching between user-defined **Voxtype
presets** — a name plus a **model** and a **language** — with a real config
reload.

- **Bar widget** (`io.github.kkosu.voxtype-presets`): shows the active
  preset's language code (e.g. `󰍬 en`). **Left click** cycles to the next
  preset, **right click** opens the preset TUI.
- **One TUI for everything**: right-click opens `voxtype-presets` in the same
  floating presentation terminal the built-in Dictation indicator uses for
  `voxtype configure` — presets list, apply, add, edit (model + language),
  and delete all in one window.
- **Default preset**: `english` (`base.en` / `en`) is the Omarchy Quattro
  default and cannot be deleted.
- **Keybind**: `SUPER + CTRL + ALT + V` cycles presets (in
  `~/.config/hypr/bindings.lua`).
- **Presets** are stored in `~/.config/voxtype/presets.json`; applying one
  patches only `[whisper] model` and `[whisper] language` in
  `~/.config/voxtype/config.toml` (comments preserved, timestamped backup)
  and restarts the `voxtype.service` user daemon — the only reload voxtype
  currently supports.
- **Missing models download automatically**: switching to a preset downloads
  the selected model (a fast no-op when it is already present). Whisper
  models are fetched directly because Voxtype 0.7.5 incorrectly treats
  Whisper `small` as the optional SenseVoice model. Other engine models use
  `voxtype setup --download --model <name>`. The TUI does this inside the popup with a
  "downloading …" message; only when the model is available does it apply the
  config, reload the daemon, and close itself. On a download failure the
  popup stays open with the error and nothing is changed. The bar left-click
  and the cycle keybind download the same way.

## TUI keys

| Keys                          | Action                              |
|-------------------------------|-------------------------------------|
| `j` `k` / `↑` `↓`             | Move between presets or editor fields |
| `h` `l` / `←` `→`             | Cycle the selected editor field     |
| `Enter`                       | Switch to the selected preset      |
| `a`                           | Add a preset and open the editor    |
| `e`                           | Edit the selected preset            |
| `d`                           | Delete selected preset (`y` / `n`)  |
| `s`                           | Save all drafts, download missing models, apply the selected preset, then close |
| `Esc`                         | Return from the editor, or close the popup |
| `q`                           | Quit; with changes choose `y` save or `d` discard |

The editor shows only two fields: `Model` and `Language`. Use `Enter` to type a
custom value, or use `h/l` to cycle the supported values. Press `Esc` to return
to the preset list; continue editing other presets if needed, then press `s`
there to save all drafts and apply the selected preset. Exact duplicate
model/language combinations are rejected, while the same language may use
different models. Nothing is written until `s`, or until `q` is confirmed with
the save option.

## Install

```bash
./install-local.sh
```

This validates the plugin folder, copies the QML into
`~/.config/omarchy/plugins/io.github.kkosu.voxtype-presets/`, installs the CLI
and TUI into `~/.local/bin/`, seeds the protected `english` default preset,
then enables the widget in the bar's right section.

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
omarchy-voxtype-presets seed          # first-run default preset
omarchy-voxtype-presets migrate       # strip legacy preset fields
```

## Debugging

```bash
omarchy plugin list --json | jq '.[] | select(.id == "io.github.kkosu.voxtype-presets")'
omarchy-shell shell rescanPlugins
qs log -p /usr/share/omarchy/shell --tail 100
```
