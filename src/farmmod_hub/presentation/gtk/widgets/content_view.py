from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from farmmod_hub.presentation.gtk.widgets.drop_zone import DropZone
from farmmod_hub.presentation.gtk.widgets.installed_mods_view import InstalledModsView
from farmmod_hub.presentation.gtk.widgets.log_diagnostics_view import LogDiagnosticsView
from farmmod_hub.presentation.i18n import _

InstallHandler = Callable[[list[Path]], None]
RemoveHandler = Callable[[Path], None]
SimpleActionHandler = Callable[[], None]


class ContentPage(Adw.NavigationPage):
    def __init__(
        self,
        on_install: InstallHandler,
        on_pick_log: SimpleActionHandler,
        on_copy_log_diagnostic: SimpleActionHandler,
        on_export_log_diagnostic: SimpleActionHandler,
    ):
        super().__init__(title=_("Instalar Mods"))

        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        self._page_title = Adw.WindowTitle(title=_("Instalar Mods"), subtitle="")
        header.set_title_widget(self._page_title)
        toolbar.add_top_bar(header)

        self._content_stack = Gtk.Stack()
        self._drop_zone = DropZone(on_install=on_install)
        self._installed_mods_view = InstalledModsView()
        self._log_view = LogDiagnosticsView(
            on_pick_log,
            on_copy_log_diagnostic,
            on_export_log_diagnostic,
        )
        self._content_stack.add_named(self._drop_zone, "instalar")
        self._content_stack.add_named(self._installed_mods_view, "instalados")
        self._content_stack.add_named(self._log_view, "diagnostico")

        toolbar.set_content(self._content_stack)
        self.set_child(toolbar)

    def show_view(self, view_id: str, title: str):
        self._content_stack.set_visible_child_name(view_id)
        self._page_title.set_title(title)

    def set_install_busy(self, busy: bool):
        self._drop_zone.set_busy(busy)

    def refresh_installed(self, mods: list[Path], on_remove: RemoveHandler):
        self._installed_mods_view.refresh(mods, on_remove)

    def show_log_report(self, report):
        self._log_view.show_report(report)
