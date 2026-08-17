#!/usr/bin/env python3
"""voxtype-presets-gui — GTK4 popup to manage Voxtype presets.

Launched from the Omarchy bar widget's right click (a standalone floating
window, not a Quickshell panel). The window is themed from the current
Omarchy theme (~/.local/state/omarchy/current/theme/colors.toml + shell.toml)
and floated/rounded via a Hyprland windowrule on its application id.

Keyboard controls (main window):
  Up / Down / j / k   move between presets
  Enter               apply the selected preset
  a                   add a new preset
  e                   edit the selected preset
  d                   delete the selected preset (confirm with y / n)
  Tab                 move focus between widgets
  Escape              close the window

A Gtk.Application id makes the window single-instance: right-clicking the bar
widget again raises the existing popup instead of opening a second one.
"""

import json
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, Gtk

APP_ID = "io.github.kkosu.voxtype-presets.gui"
PRESETS = Path.home() / ".config/voxtype/presets.json"
THEME_DIR = Path.home() / ".local/state/omarchy/current/theme"

MODELS = [
    "base.en", "base", "small.en", "small", "medium.en", "medium",
    "large-v3", "large-v3-turbo",
    "parakeet-tdt-0.6b-v3", "parakeet-tdt-0.6b-v3-int8",
]
LANGS = ["auto", "en", "is", "fr", "de", "es", "pt", "it", "nl", "sv",
         "da", "no", "fi", "pl", "ru", "uk", "ja", "zh", "ko", "ar", "hi"]

KEY_HINTS = "↑/↓  j/k move · Enter apply · a add · e edit · d delete · Esc close"


def load():
    try:
        return json.loads(PRESETS.read_text())
    except Exception:
        return {"active": "", "presets": []}


def save(data):
    PRESETS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# --- Omarchy theming --------------------------------------------------------

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
        return "rgba(169,177,214,0.08)"
    return f"rgba({r},{g},{b},{alpha})"


def theme_colors():
    """Resolve the Omarchy palette the same way qs.Commons Color does."""
    colors = parse_toml_flat(THEME_DIR / "colors.toml")
    shell = parse_toml_flat(THEME_DIR / "shell.toml")

    background = colors.get("background", "#1a1b26")
    foreground = colors.get("foreground", "#a9b1d6")
    accent = colors.get("accent", "#7aa2f7")
    urgent = colors.get("red", "#f7768e")
    muted = colors.get("dark_foreground", "#565f89")

    selected_bg = shell.get("menu.selected-background", foreground)
    selected_alpha = shell.get("menu.selected-background-alpha", "0.08")
    try:
        selected_alpha = max(0.0, min(1.0, float(selected_alpha)))
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


def build_css(c):
    return f"""
window, dialog {{
  background-color: {c['popup_bg']};
  color: {c['popup_fg']};
  font-family: monospace;
  font-size: {c['font_size']}px;
}}
headerbar {{
  background-color: {c['popup_bg']};
  color: {c['popup_fg']};
  border-bottom: 1px solid {c['border']};
  min-height: 40px;
}}
headerbar title {{
  color: {c['popup_fg']};
  font-weight: 700;
}}
label.heading {{
  font-weight: 700;
  color: {c['popup_fg']};
}}
label.dim-label {{
  color: {c['muted']};
  font-size: {max(9, int(c['font_size']) - 2)}px;
}}
listbox {{
  background-color: transparent;
  padding: 6px;
}}
listbox row {{
  background-color: transparent;
  border-radius: 8px;
  margin: 1px 0;
}}
listbox row:hover {{
  background-color: {c['hover_bg']};
}}
listbox row:selected {{
  background-color: {c['selected_row_bg']};
}}
listbox row:selected label.heading {{
  color: {c['selected_row_fg']};
}}
button {{
  background-color: {hex_to_rgba(c['foreground'], 0.06)};
  border: 1px solid {c['border']};
  border-radius: 8px;
  padding: 4px 12px;
  color: {c['popup_fg']};
  font-family: monospace;
}}
button:hover {{
  background-color: {hex_to_rgba(c['foreground'], 0.12)};
}}
button.suggested-action {{
  background-color: {c['accent']};
  border-color: {c['accent']};
  color: {c['background']};
  font-weight: 700;
}}
button.destructive-action {{
  color: {c['urgent']};
  border-color: {hex_to_rgba(c['urgent'], 0.5)};
}}
entry, textview {{
  background-color: {c['background']};
  color: {c['popup_fg']};
  border: 1px solid {c['border']};
  border-radius: 6px;
  font-family: monospace;
}}
combobox > box > button {{
  background-color: {c['background']};
  border-radius: 6px;
}}
checkbutton check {{
  background-color: {c['background']};
  border: 1px solid {c['border']};
  border-radius: 4px;
  min-width: 14px;
  min-height: 14px;
}}
checkbutton check:checked {{
  background-color: {c['accent']};
}}
scrolledwindow {{
  background-color: transparent;
}}
"""


# --- Dialogs ----------------------------------------------------------------

class EditDialog(Gtk.Dialog):
    def __init__(self, parent, title, preset=None):
        super().__init__(title=title, transient_for=parent, modal=True,
                         use_header_bar=False)
        self.set_default_size(480, 560)

        content = self.get_content_area()
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_spacing(10)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("e.g. english")

        self.model_combo = Gtk.ComboBoxText.new_with_entry()
        for model in MODELS:
            self.model_combo.append_text(model)

        self.lang_combo = Gtk.ComboBoxText.new_with_entry()
        for lang in LANGS:
            self.lang_combo.append_text(lang)

        self.keywords_view = Gtk.TextView()
        self.keywords_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.keywords_view.set_top_margin(4)
        self.keywords_view.set_bottom_margin(4)
        self.keywords_view.set_left_margin(6)
        self.keywords_view.set_right_margin(6)
        keyword_scroll = Gtk.ScrolledWindow(min_content_height=110, hexpand=True)
        keyword_scroll.set_child(self.keywords_view)

        self.clip_check = Gtk.CheckButton(label="Copy transcription to clipboard")
        self.media_check = Gtk.CheckButton(label="Pause other media while recording")

        grid = Gtk.Grid(column_spacing=8, row_spacing=8, hexpand=True, vexpand=True)

        def place(row, label_text, widget):
            label = Gtk.Label(label=label_text, halign=Gtk.Align.START, valign=Gtk.Align.START)
            label.set_margin_top(6)
            grid.attach(label, 0, row, 1, 1)
            widget.set_hexpand(True)
            grid.attach(widget, 1, row, 1, 1)

        place(0, "Name", self.name_entry)
        place(1, "Model", self.model_combo)
        place(2, "Language", self.lang_combo)
        place(3, "Keywords", keyword_scroll)
        grid.attach(self.clip_check, 1, 4, 1, 1)
        grid.attach(self.media_check, 1, 5, 1, 1)
        content.append(grid)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Save", Gtk.ResponseType.OK)

        if preset is not None:
            self.name_entry.set_text(preset.get("name", ""))
            self.model_combo.get_child().set_text(preset.get("model", ""))
            self.lang_combo.get_child().set_text(preset.get("language", "auto"))
            self.keywords_view.get_buffer().set_text(preset.get("keywords", ""))
            self.clip_check.set_active(bool(preset.get("copyToClipboard", True)))
            self.media_check.set_active(bool(preset.get("pauseMedia", True)))
        else:
            self.model_combo.get_child().set_text("base.en")
            self.lang_combo.get_child().set_text("auto")
            self.clip_check.set_active(True)
            self.media_check.set_active(True)

    def get_preset(self):
        buffer = self.keywords_view.get_buffer()
        return {
            "name": self.name_entry.get_text().strip(),
            "model": self.model_combo.get_child().get_text().strip(),
            "language": self.lang_combo.get_child().get_text().strip() or "auto",
            "keywords": buffer.get_text(buffer.get_start_iter(),
                                        buffer.get_end_iter(), False).strip(),
            "copyToClipboard": self.clip_check.get_active(),
            "pauseMedia": self.media_check.get_active(),
        }


def confirm(parent, text):
    """y/n confirmation dialog."""
    dialog = Gtk.MessageDialog(transient_for=parent, modal=True,
                               message_type=Gtk.MessageType.QUESTION,
                               buttons=Gtk.ButtonsType.NONE, text=text)
    dialog.add_button("No (n)", Gtk.ResponseType.CANCEL)
    dialog.add_button("Yes (y)", Gtk.ResponseType.OK)

    controller = Gtk.EventControllerKey.new()

    def on_key(_ctrl, keyval, _keycode, _state):
        name = Gdk.keyval_name(keyval)
        if name in ("y", "Y"):
            dialog.response(Gtk.ResponseType.OK)
            return True
        if name in ("n", "N"):
            dialog.response(Gtk.ResponseType.CANCEL)
            return True
        return False

    controller.connect("key-pressed", on_key)
    dialog.add_controller(controller)
    dialog.present()
    result = dialog.run()
    dialog.destroy()
    return result


# --- Main window ------------------------------------------------------------

class PresetWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Voxtype Presets")
        self.set_default_size(520, 560)

        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        self.active_label = Gtk.Label(label="", halign=Gtk.Align.START)
        self.active_label.add_css_class("dim-label")
        header.set_title_widget(self.active_label)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.set_hexpand(True)
        self.listbox.set_vexpand(True)
        self.listbox.add_css_class("rich-list")
        self.listbox.connect("row-activated", lambda box, row: self.on_apply())

        scroll = Gtk.ScrolledWindow(child=self.listbox)

        hints = Gtk.Label(label=KEY_HINTS, halign=Gtk.Align.START)
        hints.add_css_class("dim-label")
        hints.set_margin_start(12)
        hints.set_margin_end(12)
        hints.set_margin_top(2)

        add_button = Gtk.Button(label="Add (a)", action_name="win.add")
        edit_button = Gtk.Button(label="Edit (e)", action_name="win.edit")
        delete_button = Gtk.Button(label="Delete (d)", action_name="win.delete")
        delete_button.add_css_class("destructive-action")
        apply_button = Gtk.Button(label="Apply (Enter)", action_name="win.apply")
        apply_button.add_css_class("suggested-action")

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_margin_top(10)
        button_box.set_margin_bottom(4)
        button_box.set_margin_start(12)
        button_box.set_margin_end(12)
        button_box.append(add_button)
        button_box.append(edit_button)
        button_box.append(delete_button)
        spacer = Gtk.Label(label="", hexpand=True)
        button_box.append(spacer)
        button_box.append(apply_button)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.append(scroll)
        main.append(hints)
        main.append(button_box)
        self.set_child(main)

        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_key)
        self.add_controller(key_controller)

        self._add_actions()
        self.refresh()

    def _add_actions(self):
        handlers = {
            "add": self.on_add,
            "edit": self.on_edit,
            "delete": self.on_delete,
            "apply": self.on_apply,
            "refresh": self.refresh,
        }
        for name, handler in handlers.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, fn=handler: fn())
            self.add_action(action)

    def on_key(self, _ctrl, keyval, _keycode, state):
        name = Gdk.keyval_name(keyval) or ""
        modifiers = state & Gdk.ModifierType.MODIFIER_MASK
        if modifiers not in (0, Gdk.ModifierType.SHIFT_MASK):
            return False
        if name in ("j", "Down"):
            self.move_selection(1)
            return True
        if name in ("k", "Up"):
            self.move_selection(-1)
            return True
        if name in ("a", "A"):
            self.on_add()
            return True
        if name in ("e", "E"):
            self.on_edit()
            return True
        if name in ("d", "D"):
            self.on_delete()
            return True
        if name == "Escape":
            self.close()
            return True
        return False

    def move_selection(self, delta):
        row = self.listbox.get_selected_row()
        if row is None:
            target = self.listbox.get_first_child()
        else:
            target = row.get_next_sibling() if delta > 0 else row.get_prev_sibling()
        if target is not None:
            self.listbox.select_row(target)
            target.grab_focus()

    def refresh(self):
        data = load()
        while self.listbox.get_first_child() is not None:
            self.listbox.remove(self.listbox.get_first_child())

        active = data.get("active", "")
        for preset in data.get("presets", []):
            name = preset.get("name", "")
            mark = "✓  " if name == active else "    "
            title = Gtk.Label(label=f"{mark}{name}", xalign=0, hexpand=True)
            title.add_css_class("heading")
            detail = Gtk.Label(
                label=f"{preset.get('model', '')} · {preset.get('language', '')} · "
                      f"{'clipboard' if preset.get('copyToClipboard', True) else 'type'} · "
                      f"{'pause media' if preset.get('pauseMedia', True) else 'media untouched'}",
                xalign=0, halign=Gtk.Align.START)
            detail.add_css_class("dim-label")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.append(title)
            box.append(detail)
            row = Gtk.ListBoxRow()
            row.set_child(box)
            row.preset_name = name
            self.listbox.append(row)
            if name == active:
                self.listbox.select_row(row)

        if self.listbox.get_selected_row() is None and self.listbox.get_first_child() is not None:
            self.listbox.select_row(self.listbox.get_first_child())
        self.active_label.set_text(f"Active: {active or 'none'}")

    def selected_name(self):
        row = self.listbox.get_selected_row()
        return getattr(row, "preset_name", None)

    def on_apply(self):
        name = self.selected_name()
        if not name:
            return
        subprocess.run(["omarchy-voxtype-presets", "apply", name], check=False)
        self.refresh()

    def on_add(self):
        dialog = EditDialog(self, "New preset")
        dialog.present()
        result = dialog.run()
        if result == Gtk.ResponseType.OK:
            preset = dialog.get_preset()
            if not preset["name"]:
                self._error("The preset needs a name.")
            else:
                data = load()
                data["presets"] = [p for p in data["presets"] if p.get("name") != preset["name"]]
                data["presets"].append(preset)
                save(data)
                self.refresh()
        dialog.destroy()

    def on_edit(self):
        name = self.selected_name()
        if not name:
            return
        data = load()
        preset = next((p for p in data["presets"] if p.get("name") == name), None)
        if preset is None:
            return
        dialog = EditDialog(self, f"Edit {name}", preset=preset)
        dialog.present()
        result = dialog.run()
        if result == Gtk.ResponseType.OK:
            updated = dialog.get_preset()
            if not updated["name"]:
                self._error("The preset needs a name.")
            else:
                data = load()
                was_active = data.get("active") == name
                data["presets"] = [updated if p.get("name") == name else p
                                   for p in data["presets"]]
                if was_active:
                    data["active"] = updated["name"]
                save(data)
                if was_active:
                    subprocess.run(["omarchy-voxtype-presets", "apply", updated["name"]],
                                   check=False)
                self.refresh()
        dialog.destroy()

    def on_delete(self):
        name = self.selected_name()
        if not name:
            return
        if confirm(self, f"Delete preset “{name}”?") != Gtk.ResponseType.OK:
            return
        data = load()
        data["presets"] = [p for p in data["presets"] if p.get("name") != name]
        if data.get("active") == name:
            data["active"] = data["presets"][0]["name"] if data["presets"] else ""
        save(data)
        self.refresh()

    def _error(self, message):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK, text=message)
        dialog.present()
        dialog.run()
        dialog.destroy()


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = PresetWindow(self)
        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_string(build_css(theme_colors()))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
