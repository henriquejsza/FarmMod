import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from farmmod_hub.application import get_mods_service
from farmmod_hub.infrastructure.config import get_settings_store
from .controller import MainController
from .window import MainWindow

DATA_DIR = Path(__file__).resolve().parents[4] / "data"
APP_ID = "io.github.henriquejsza.farmmod-hub"

GLib.set_prgname(APP_ID)
GLib.set_application_name("FarmMod")
Gtk.Window.set_default_icon_name(APP_ID)


class FarmModHubApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._settings = get_settings_store()
        self._controller = MainController(get_mods_service(), self._settings)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        self._load_css()
        MainWindow(app, self._controller).present()

    def _load_css(self):
        display = Gdk.Display.get_default()

        provider = Gtk.CssProvider()
        provider.load_from_path(str(DATA_DIR / "style.css"))
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_theme.add_search_path(str(DATA_DIR / "logo"))


def main() -> int:
    return FarmModHubApp().run(sys.argv)
