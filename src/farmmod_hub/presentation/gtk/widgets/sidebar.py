from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from farmmod_hub.presentation.i18n import _

ViewSelectCallback = Callable[[str, str], None]
SettingsCallback = Callable[[], None]


class SidebarPage(Adw.NavigationPage):
    def __init__(self, on_view_select: ViewSelectCallback, on_settings: SettingsCallback):
        super().__init__(title="Menu")
        self._on_view_select = on_view_select

        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_title(False)
        toolbar.add_top_bar(header)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.set_vexpand(True)

        self._nav = Gtk.ListBox()
        self._nav.add_css_class("navigation-sidebar")
        self._nav.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._nav.set_vexpand(True)

        self._views = [
            ("instalar", _("Instalar Mods"), "document-send-symbolic", _("Instalar")),
            (
                "instalados",
                _("Mods Instalados"),
                "folder-open-symbolic",
                _("Instalados"),
            ),
            (
                "diagnostico",
                _("Diagnostico de Log"),
                "text-x-generic-symbolic",
                _("Diagnostico"),
            ),
        ]

        for _view_id, _title, icon_name, label in self._views:
            self._nav.append(self._nav_row(icon_name, label))

        self._nav.connect("row-selected", self._on_nav_select)
        body.append(self._nav)
        body.append(Gtk.Separator())

        cfg_nav = Gtk.ListBox()
        cfg_nav.add_css_class("navigation-sidebar")
        cfg_nav.set_selection_mode(Gtk.SelectionMode.NONE)
        cfg_nav.append(self._nav_row("preferences-system-symbolic", _("Configurações")))
        cfg_nav.connect("row-activated", lambda *_: on_settings())
        body.append(cfg_nav)

        toolbar.set_content(body)
        self.set_child(toolbar)

    def select_first(self):
        self._nav.select_row(self._nav.get_row_at_index(0))

    def _on_nav_select(self, _listbox, row):
        if row is None:
            return
        view_id, title, _, _ = self._views[row.get_index()]
        self._on_view_select(view_id, title)

    def _nav_row(self, icon_name: str, label_text: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(7)
        box.set_margin_bottom(7)
        box.append(Gtk.Image.new_from_icon_name(icon_name))
        box.append(Gtk.Label(label=label_text, halign=Gtk.Align.START, hexpand=True))
        row.set_child(box)
        return row
