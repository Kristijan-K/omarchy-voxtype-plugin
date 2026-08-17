#!/usr/bin/env python3
"""voxtype-presets-gui — GTK4 popup to manage Voxtype presets.

Launched from the Omarchy bar widget's right click (a standalone floating
window, not a Quickshell panel). The window is themed from the current
Omarchy theme (~/.local/state/omarchy/current/theme/colors.toml + shell.toml)
and floated/rounded via a Hyprland windowrule on its application id.

List window keys:
  Up / Down / j / k   move between presets
  Enter               apply the selected preset
  a                   add a preset (opens the voxtype-configure-style TUI)
  e                   edit the selected preset (same TUI, floating terminal)
  d                   delete the selected preset (confirm with y / n, Esc = no)
  Esc                 close the window

Editing happens in `voxtype-presets-edit`, launched through the same floating
terminal presentation wrapper the built-in Dictation indicator uses for
`voxtype configure`.

A Gtk.Application id makes the window single-instance: right-clicking the bar
widget again raises the existing popup instead of opening a second one.
"""

import shlex
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

sys.path.insert(0, str(Path(__file__).resolve().parent))
from voxtype_presets_lib import (  # noqa: E402
    hex_to_rgba, load, save, theme_colors)

APP_ID = "io.github.kkosu.voxtype-presets.gui"

KEY_HINTS = "↑/↓ j/k move · Enter apply · a add · e edit · d delete · Esc close"
EDIT_HINT = "Preset editor: tabs · j/k · Enter · s save · q quit (same style as voxtype configure)"


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
scrolledwindow {{
  background-color: transparent;
}}
"""


def confirm(parent, text):
    """y/n confirmation dialog (Esc = no)."""
    dialog = Gtk.MessageDialog(transient_for=parent, modal=True,
                               message_type=Gtk.MessageType.QUESTION,
                               buttons=Gtk.ButtonsType.NONE, text=text)
    dialog.add_button("No (n)", Gtk.ResponseType.CANCEL)
    dialog.add_button("Yes (y)", Gtk.ResponseType.OK)

    controller = Gtk.EventControllerKey.new()
    controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

    def on_key(_ctrl, keyval, _keycode, _state):
        name = Gdk.keyval_name(keyval)
        if name in ("y", "Y"):
            dialog.response(Gtk.ResponseType.OK)
            return True
        if name in ("n", "N", "Escape"):
            dialog.response(Gtk.ResponseType.CANCEL)
            return True
        return False

    controller.connect("key-pressed", on_key)
    dialog.add_controller(controller)
    dialog.present()
    result = dialog.run()
    dialog.destroy()
    return result


def launch_editor(name=""):
    """Open the preset TUI in the Dictate-style floating presentation terminal."""
    command = "voxtype-presets-edit"
    if name:
        command += " " + shlex.quote(name)
    subprocess.Popen(
        ["bash", "-c",
         f'omarchy-launch-floating-terminal-with-presentation "{command}"'],
        start_new_session=True)


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

        edit_hint = Gtk.Label(label=EDIT_HINT, halign=Gtk.Align.START)
        edit_hint.add_css_class("dim-label")
        edit_hint.set_margin_start(12)
        edit_hint.set_margin_end(12)

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
        main.append(edit_hint)
        main.append(button_box)
        self.set_child(main)

        key_controller = Gtk.EventControllerKey.new()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self.on_key)
        self.add_controller(key_controller)

        self._add_actions()
        self.refresh()
        # Keep the list in sync with TUI edits.
        GLib.timeout_add_seconds(1, self.refresh)

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
        # Ignore chords; plain keys only. LOCK (Caps/Num) must not block
        # j/k navigation the way MODIFIER_MASK does.
        chord = (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK |
                 Gdk.ModifierType.SUPER_MASK | Gdk.ModifierType.META_MASK |
                 Gdk.ModifierType.HYPER_MASK)
        if state & chord:
            return False
        name = Gdk.keyval_name(keyval) or ""
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
        return True  # keep the GLib timeout running

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
        launch_editor()

    def on_edit(self):
        name = self.selected_name()
        if not name:
            return
        launch_editor(name)

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
