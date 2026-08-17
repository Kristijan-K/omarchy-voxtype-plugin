#!/usr/bin/env python3
"""voxtype-presets-gui — GTK4 popup to manage Voxtype presets.

Launched from the Omarchy bar widget's right click (a standalone window, not
a Quickshell panel). Edit preset fields, add/delete presets, and apply one
immediately — applying patches config.toml and restarts the voxtype daemon
through `omarchy-voxtype-presets apply`.

A Gtk.Application id makes the window single-instance: right-clicking the bar
widget again raises the existing popup instead of opening a second one.
"""

import json
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

APP_ID = "io.github.kkosu.voxtype-presets.gui"
PRESETS = Path.home() / ".config/voxtype/presets.json"

MODELS = [
    "base.en", "base", "small.en", "small", "medium.en", "medium",
    "large-v3", "large-v3-turbo",
    "parakeet-tdt-0.6b-v3", "parakeet-tdt-0.6b-v3-int8",
]
LANGS = ["auto", "en", "is", "fr", "de", "es", "pt", "it", "nl", "sv",
         "da", "no", "fi", "pl", "ru", "uk", "ja", "zh", "ko", "ar", "hi"]


def load():
    try:
        return json.loads(PRESETS.read_text())
    except Exception:
        return {"active": "", "presets": []}


def save(data):
    PRESETS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


class EditDialog(Gtk.Dialog):
    def __init__(self, parent, title, preset=None):
        super().__init__(title=title, transient_for=parent, modal=True,
                         use_header_bar=False)
        self.set_default_size(460, 520)

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


class PresetWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Voxtype Presets")
        self.set_default_size(480, 430)

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

        add_button = Gtk.Button(label="Add", action_name="win.add")
        edit_button = Gtk.Button(label="Edit", action_name="win.edit")
        delete_button = Gtk.Button(label="Delete", action_name="win.delete")
        apply_button = Gtk.Button(label="Apply", action_name="win.apply")
        apply_button.add_css_class("suggested-action")

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_margin_top(10)
        button_box.set_margin_bottom(10)
        button_box.set_margin_start(10)
        button_box.set_margin_end(10)
        button_box.append(add_button)
        button_box.append(edit_button)
        button_box.append(delete_button)
        spacer = Gtk.Label(label="", hexpand=True)
        button_box.append(spacer)
        button_box.append(apply_button)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.append(scroll)
        main.append(button_box)
        self.set_child(main)

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
        confirm = Gtk.MessageDialog(transient_for=self, modal=True,
                                    message_type=Gtk.MessageType.QUESTION,
                                    buttons=Gtk.ButtonsType.NONE,
                                    text=f"Delete preset “{name}”?")
        confirm.add_button("Cancel", Gtk.ResponseType.CANCEL)
        confirm.add_button("Delete", Gtk.ResponseType.OK)
        confirm.present()
        result = confirm.run()
        confirm.destroy()
        if result != Gtk.ResponseType.OK:
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


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
