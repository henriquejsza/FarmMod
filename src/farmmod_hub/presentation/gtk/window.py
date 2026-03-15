import os
import sys
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from farmmod_hub.presentation.gtk.controller import MainController
from farmmod_hub.presentation.gtk.dialogs.settings_dialog import SettingsDialog
from farmmod_hub.presentation.gtk.widgets import ContentPage, SidebarPage, StatusBar
from farmmod_hub.presentation.i18n import _, installed_result, updated_result


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app, controller: MainController):
        super().__init__(application=app)
        self.set_title("FarmMod")
        self.set_icon_name("io.github.henriquejsza.farmmod-hub")
        self.set_default_size(920, 640)
        self.set_size_request(700, 500)

        self._controller = controller
        self._last_log_report = None
        self._last_log_game_id = None
        self._last_log_game_label = None

        self._sidebar = SidebarPage(self._on_view_select, self._on_settings)
        self._content = ContentPage(
            self._on_install,
            self._on_pick_log,
            self._on_copy_log_diagnostic,
            self._on_export_log_diagnostic,
        )

        split = Adw.NavigationSplitView()
        split.set_sidebar_width_fraction(0.22)
        split.set_min_sidebar_width(168)
        split.set_max_sidebar_width(256)
        split.set_sidebar(self._sidebar)
        split.set_content(self._content)
        split.set_vexpand(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(split)
        self._status_bar = StatusBar(
            self._controller.get_mods_dir(),
            self._controller.get_active_game_label(),
        )
        outer.append(self._status_bar)

        self.set_content(outer)
        self._sidebar.select_first()
        self._refresh_count()

    def _on_view_select(self, view_id: str, title: str):
        self._content.show_view(view_id, title)
        if view_id == "instalados":
            self._refresh_instalados()

    def _on_pick_log(self):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Selecionar log.txt"))

        log_default = self._controller.get_mods_dir().parent / "log.txt"
        if log_default.exists():
            dialog.set_initial_file(Gio.File.new_for_path(str(log_default)))
        else:
            dialog.set_initial_folder(Gio.File.new_for_path(str(self._controller.get_mods_dir().parent)))

        filter_txt = Gtk.FileFilter()
        filter_txt.set_name(_("Arquivos de log (.txt)"))
        filter_txt.add_pattern("*.txt")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_txt)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_pick_log_done)

    def _on_pick_log_done(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except Exception:
            return

        if gfile is None or not gfile.get_path():
            return

        log_path = Path(gfile.get_path())
        try:
            report = self._controller.analyze_log(log_path)
        except Exception as exc:
            error_dialog = Adw.AlertDialog(
                heading=_("Nao foi possivel analisar o log"),
                body=str(exc),
            )
            error_dialog.add_response("ok", "OK")
            error_dialog.present(self)
            return

        self._last_log_report = report
        self._last_log_game_id = self._controller.get_active_game()
        self._last_log_game_label = self._controller.get_active_game_label()
        self._content.show_log_report(report)
        self._content.show_view("diagnostico", _("Diagnostico de Log"))

    def _on_copy_log_diagnostic(self):
        if self._last_log_report is None:
            return

        game_id = self._last_log_game_id or self._controller.get_active_game()
        game_label = self._last_log_game_label or self._controller.get_active_game_label()
        report_text = self._controller.build_log_report_text(
            self._last_log_report,
            game_id=game_id,
            game_label=game_label,
        )

        display = self.get_display()
        if display is None:
            return
        display.get_clipboard().set(report_text)

        dialog = Adw.AlertDialog(
            heading=_("Diagnostico copiado"),
            body=_("O diagnostico foi copiado para a area de transferencia."),
        )
        dialog.add_response("ok", "OK")
        dialog.present(self)

    def _on_export_log_diagnostic(self):
        if self._last_log_report is None:
            return

        dialog = Gtk.FileDialog()
        dialog.set_title(_("Exportar diagnostico"))

        game_id = (self._last_log_game_id or self._controller.get_active_game()).upper()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dialog.set_initial_name(f"diagnostico_{game_id}_{stamp}.txt")
        dialog.save(self, None, self._on_export_log_done)

    def _on_export_log_done(self, dialog, result):
        if self._last_log_report is None:
            return

        try:
            output_file = dialog.save_finish(result)
        except Exception:
            return

        if output_file is None or not output_file.get_path():
            return

        game_id = self._last_log_game_id or self._controller.get_active_game()
        game_label = self._last_log_game_label or self._controller.get_active_game_label()
        try:
            written = self._controller.export_log_report(
                self._last_log_report,
                Path(output_file.get_path()),
                game_id=game_id,
                game_label=game_label,
            )
        except Exception as exc:
            error_dialog = Adw.AlertDialog(
                heading=_("Nao foi possivel exportar diagnostico"),
                body=str(exc),
            )
            error_dialog.add_response("ok", "OK")
            error_dialog.present(self)
            return

        info_dialog = Adw.AlertDialog(
            heading=_("Diagnostico exportado"),
            body=str(written),
        )
        info_dialog.add_response("ok", "OK")
        info_dialog.present(self)

    def _refresh_instalados(self):
        mods = self._controller.list_installed()
        self._content.refresh_installed(mods, self._on_remove)

    def _on_remove(self, mod_path: Path):
        if not self._controller.get_confirm_delete():
            self._do_remove(mod_path)
            return

        dialog = Adw.AlertDialog(
            heading=_("Excluir mod?"),
            body=f'"{mod_path.name}" {_("será excluído permanentemente.")}',
        )
        dialog.add_response("cancel", _("Cancelar"))
        dialog.add_response("delete", _("Excluir"))
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: self._do_remove(mod_path) if r == "delete" else None)
        dialog.present(self)

    def _do_remove(self, mod_path: Path):
        self._controller.remove_mod(mod_path)
        self._refresh_count()
        self._refresh_instalados()

    def _on_install(self, paths: list[Path]):
        self._content.set_install_busy(True)
        self._controller.install_async(paths, self._on_install_done)

    def _on_install_done(
        self,
        installed: list[str],
        updated: list[str],
        errors: list[str],
        warnings: list[str],
    ):
        self._content.set_install_busy(False)
        self._refresh_count()
        self._refresh_instalados()
        self._show_result(installed, updated, errors, warnings)
        return GLib.SOURCE_REMOVE

    def _refresh_count(self):
        self._status_bar.set_count(self._controller.count_installed())

    def _on_settings(self, *_):
        SettingsDialog(
            self,
            on_mods_dir_changed=self._on_mods_dir_changed,
            on_language_changed=self._on_language_changed,
        ).present(self)

    def _on_mods_dir_changed(self, path: Path):
        self._status_bar.set_game_label(self._controller.get_active_game_label())
        self._status_bar.set_mods_dir(path)
        self._refresh_count()
        self._refresh_instalados()

    def _on_language_changed(self, _lang: str):
        dialog = Adw.AlertDialog(
            heading=_("Reiniciar o app"),
            body=_("O idioma será aplicado após reiniciar o app."),
        )
        dialog.add_response("later", _("Agora não"))
        dialog.add_response("restart", _("Reiniciar"))
        dialog.set_default_response("restart")
        dialog.set_close_response("later")

        def _on_response(_dialog, response):
            if response == "restart":
                os.execv(sys.executable, [sys.executable] + sys.argv)

        dialog.connect("response", _on_response)
        dialog.present(self)

    def _show_result(
        self,
        installed: list[str],
        updated: list[str],
        errors: list[str],
        warnings: list[str],
    ):
        parts = []
        if installed:
            parts.append(installed_result(len(installed)))
        if updated:
            parts.append(updated_result(len(updated)))
        if warnings:
            parts.append(_("Avisos:") + "\n" + "\n".join(f"- {w}" for w in warnings))
        if errors:
            parts.append(_("Erros:") + "\n" + "\n".join(f"- {e}" for e in errors))

        dialog = Adw.AlertDialog(
            heading=_("Resultado"),
            body="\n".join(parts) or _("Nenhum mod processado."),
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)
