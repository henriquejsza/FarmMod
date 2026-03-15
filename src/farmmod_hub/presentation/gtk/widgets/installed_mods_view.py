from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from farmmod_hub.presentation.i18n import _

RemoveHandler = Callable[[Path], None]


def _format_size(path: Path) -> str:
    if path.is_dir():
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    else:
        size = path.stat().st_size

    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class InstalledModsView(Gtk.Stack):
    def __init__(self):
        super().__init__()

        self._mods_list = Gtk.ListBox()
        self._mods_list.add_css_class("boxed-list")
        self._mods_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._mods_list.set_margin_top(12)
        self._mods_list.set_margin_bottom(12)
        self._mods_list.set_margin_start(16)
        self._mods_list.set_margin_end(16)

        scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scroll.set_child(self._mods_list)

        empty_state = Adw.StatusPage()
        empty_state.set_icon_name("folder-open-symbolic")
        empty_state.set_title(_("Nenhum mod instalado"))
        empty_state.set_description(_("Instale mods pela aba Instalar"))
        empty_state.set_vexpand(True)

        self.add_named(empty_state, "empty")
        self.add_named(scroll, "list")

    def refresh(self, mods: list[Path], on_remove: RemoveHandler):
        while child := self._mods_list.get_first_child():
            self._mods_list.remove(child)

        if not mods:
            self.set_visible_child_name("empty")
            return

        for mod_path in mods:
            self._mods_list.append(self._mod_row(mod_path, on_remove))
        self.set_visible_child_name("list")

    def _mod_row(self, mod_path: Path, on_remove: RemoveHandler) -> Adw.ActionRow:
        is_dir = mod_path.is_dir()
        icon_name = "folder-symbolic" if is_dir else "package-x-generic-symbolic"
        type_label = _("Pasta") if is_dir else "ZIP"
        subtitle = f"{type_label} - {_format_size(mod_path)}"

        row = Adw.ActionRow(title=mod_path.name, subtitle=subtitle)

        img = Gtk.Image.new_from_icon_name(icon_name)
        img.set_pixel_size(32)
        row.add_prefix(img)

        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("destructive-action")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.connect("clicked", lambda _, p=mod_path: on_remove(p))
        row.add_suffix(delete_btn)

        return row
