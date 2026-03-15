from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from farmmod_hub.presentation.i18n import _


def _gio_list_to_paths(file_list: Gio.ListModel) -> list[Path]:
    paths = []
    for i in range(file_list.get_n_items()):
        gfile = file_list.get_item(i)
        file_path = gfile.get_path() if gfile else None
        if file_path:
            paths.append(Path(file_path))
    return paths


class DropZone(Gtk.Overlay):
    def __init__(self, on_install):
        super().__init__(vexpand=True, hexpand=True)
        self._on_install = on_install
        self._busy = False

        page = Adw.StatusPage()
        page.set_icon_name("document-send-symbolic")
        page.set_title(_("Arraste seus mods aqui para instalar"))
        page.set_description(_("Aceita arquivos .zip ou pastas com modDesc.xml"))
        page.set_vexpand(True)
        page.set_hexpand(True)

        btn = Gtk.Button(label=_("Selecionar Arquivos"))
        btn.set_halign(Gtk.Align.CENTER)
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.connect("clicked", self._pick_files)
        page.set_child(btn)

        self.set_child(page)

        self._spinner = Gtk.Spinner()
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_valign(Gtk.Align.CENTER)
        self._spinner.set_size_request(48, 48)

        lbl = Gtk.Label(label=_("Instalando…"))
        lbl.add_css_class("title-4")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_halign(Gtk.Align.CENTER)
        inner.set_valign(Gtk.Align.CENTER)
        inner.append(self._spinner)
        inner.append(lbl)

        self._busy_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.FILL,
            hexpand=True,
            vexpand=True,
        )
        self._busy_box.add_css_class("drop-zone-busy")
        self._busy_box.append(inner)
        self._busy_box.set_visible(False)

        self.add_overlay(self._busy_box)

        target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        target.connect("enter", self._drag_enter)
        target.connect("leave", self._drag_leave)
        target.connect("drop", self._drag_drop)
        self.add_controller(target)

    def set_busy(self, is_busy: bool):
        self._busy = is_busy
        self._busy_box.set_visible(is_busy)
        if is_busy:
            self._spinner.start()
        else:
            self._spinner.stop()

    def _drag_enter(self, target, x, y):
        if self._busy:
            return Gdk.DragAction(0)
        self.add_css_class("drop-zone-over")
        return Gdk.DragAction.COPY

    def _drag_leave(self, target):
        self.remove_css_class("drop-zone-over")

    def _drag_drop(self, target, value, x, y):
        if self._busy:
            return False
        self.remove_css_class("drop-zone-over")
        paths = [Path(f.get_path()) for f in value.get_files() if f.get_path()]
        if paths:
            self._on_install(paths)
        return True

    def _pick_files(self, _btn):
        if self._busy:
            return
        dialog = Gtk.FileDialog(title=_("Selecionar Mods"))

        filters = Gio.ListStore.new(Gtk.FileFilter)

        zip_filter = Gtk.FileFilter()
        zip_filter.set_name(_("Mods do FS19 (.zip)"))
        zip_filter.add_pattern("*.zip")
        filters.append(zip_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name(_("Todos os arquivos"))
        all_filter.add_pattern("*")
        filters.append(all_filter)

        dialog.set_filters(filters)
        dialog.open_multiple(self.get_root(), None, self._pick_done)

    def _pick_done(self, dialog, result):
        try:
            paths = _gio_list_to_paths(dialog.open_multiple_finish(result))
            if paths:
                self._on_install(paths)
        except GLib.Error:
            pass
