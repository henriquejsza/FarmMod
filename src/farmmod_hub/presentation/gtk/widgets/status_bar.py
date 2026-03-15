import re
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from farmmod_hub.presentation.i18n import count_label


def _abbrev_path(path: Path, keep_tail: int = 2) -> str:
    try:
        parts = path.relative_to(Path.home()).parts
    except ValueError:
        return str(path)
    if len(parts) <= keep_tail + 1:
        return "~/" + "/".join(parts)
    return f"~/{parts[0]}/.../{'/'.join(parts[-keep_tail:])}"


def _short_game_label(game_label: str) -> str:
    match = re.search(r"(\d{2})$", game_label)
    if match:
        return f"FS{match.group(1)}"
    return game_label


class StatusBar(Gtk.Box):
    def __init__(self, mods_dir: Path, game_label: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.append(Gtk.Separator())

        bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            valign=Gtk.Align.CENTER,
            spacing=6,
            margin_start=12,
            margin_end=12,
            margin_top=7,
            margin_bottom=7,
        )

        folder_img = Gtk.Image.new_from_icon_name("folder-symbolic")
        folder_img.set_valign(Gtk.Align.CENTER)
        folder_img.add_css_class("dim-label")
        bar.append(folder_img)

        self._game_lbl = Gtk.Label(
            label=_short_game_label(game_label),
            valign=Gtk.Align.CENTER,
        )
        self._game_lbl.add_css_class("dim-label")
        bar.append(self._game_lbl)

        self._path_lbl = Gtk.Label(
            label=_abbrev_path(mods_dir),
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
            hexpand=True,
        )
        self._path_lbl.add_css_class("dim-label")
        bar.append(self._path_lbl)

        self._count_lbl = Gtk.Label(label=count_label(0), valign=Gtk.Align.CENTER)
        self._count_lbl.add_css_class("dim-label")
        bar.append(self._count_lbl)

        self.append(bar)

    def set_mods_dir(self, path: Path):
        self._path_lbl.set_label(_abbrev_path(path))

    def set_game_label(self, game_label: str):
        self._game_lbl.set_label(_short_game_label(game_label))

    def set_count(self, count: int):
        self._count_lbl.set_label(count_label(count))
