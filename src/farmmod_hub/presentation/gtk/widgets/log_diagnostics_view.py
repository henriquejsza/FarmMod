from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from farmmod_hub.infrastructure.logs import LogAnalysisReport
from farmmod_hub.presentation.i18n import _

PickLogCallback = Callable[[], None]
CopyDiagnosticCallback = Callable[[], None]
ExportDiagnosticCallback = Callable[[], None]


class LogDiagnosticsView(Gtk.Box):
    def __init__(
        self,
        on_pick_log: PickLogCallback,
        on_copy_diagnostic: CopyDiagnosticCallback,
        on_export_diagnostic: ExportDiagnosticCallback,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_spacing(10)
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(12)
        self.set_margin_bottom(12)

        self._status = Adw.StatusPage()
        self._status.set_icon_name("text-x-generic-symbolic")
        self._status.set_title(_("Diagnostico de Log"))
        self._status.set_description(_("Abra o log.txt para encontrar mods suspeitos"))

        pick_btn = Gtk.Button(label=_("Selecionar log.txt"))
        pick_btn.add_css_class("suggested-action")
        pick_btn.add_css_class("pill")
        pick_btn.connect("clicked", lambda *_: on_pick_log())
        self._status.set_child(pick_btn)
        self.append(self._status)

        self._summary = Adw.PreferencesGroup()
        self._summary.set_title(_("Resumo"))

        self._actions_row = Adw.ActionRow()
        self._actions_row.set_title(_("Acoes"))

        self._copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        self._copy_btn.add_css_class("flat")
        self._copy_btn.set_tooltip_text(_("Copiar diagnostico"))
        self._copy_btn.set_sensitive(False)
        self._copy_btn.connect("clicked", lambda *_: on_copy_diagnostic())
        self._actions_row.add_suffix(self._copy_btn)

        self._export_btn = Gtk.Button.new_from_icon_name("document-save-symbolic")
        self._export_btn.add_css_class("flat")
        self._export_btn.set_tooltip_text(_("Exportar diagnostico"))
        self._export_btn.set_sensitive(False)
        self._export_btn.connect("clicked", lambda *_: on_export_diagnostic())
        self._actions_row.add_suffix(self._export_btn)

        self._summary.add(self._actions_row)

        self._summary_row = Adw.ActionRow()
        self._summary_row.set_title(_("Nenhum log analisado"))
        self._summary_row.set_subtitle("")
        self._summary.add(self._summary_row)
        self.append(self._summary)

        self._mods_group = Adw.PreferencesGroup()
        self._mods_group.set_title(_("Mods suspeitos"))
        self.append(self._mods_group)
        self._mod_rows: list[Adw.ActionRow] = []

        self._generic_group = Adw.PreferencesGroup()
        self._generic_group.set_title(_("Problemas gerais"))
        self.append(self._generic_group)
        self._generic_rows: list[Adw.ActionRow] = []

    def show_report(self, report: LogAnalysisReport):
        self._summary_row.set_title(
            _("{errors} erros, {warnings} avisos").format(
                errors=report.total_errors,
                warnings=report.total_warnings,
            )
        )
        self._summary_row.set_subtitle(str(report.path))
        self._copy_btn.set_sensitive(True)
        self._export_btn.set_sensitive(True)

        self._clear_rows(self._mods_group, self._mod_rows)
        self._clear_rows(self._generic_group, self._generic_rows)

        if report.mod_summaries:
            for summary in report.mod_summaries[:20]:
                row = Adw.ActionRow()
                row.set_title(summary.mod_name)
                category_list = ", ".join(
                    f"{name}:{count}" for name, count in sorted(summary.categories.items())
                )
                row.set_subtitle(
                    _("{errors} erros, {warnings} avisos").format(
                        errors=summary.errors,
                        warnings=summary.warnings,
                    )
                    + (f" | {category_list}" if category_list else "")
                )
                if summary.sample_lines:
                    details_btn = Gtk.Button.new_from_icon_name("dialog-information-symbolic")
                    details_btn.add_css_class("flat")
                    details_btn.set_tooltip_text(_("Ver exemplos"))
                    details_btn.connect(
                        "clicked",
                        self._show_samples,
                        summary.mod_name,
                        summary.sample_lines,
                    )
                    row.add_suffix(details_btn)
                self._mods_group.add(row)
                self._mod_rows.append(row)
        else:
            row = Adw.ActionRow()
            row.set_title(_("Nenhum mod suspeito encontrado"))
            self._mods_group.add(row)
            self._mod_rows.append(row)

        if report.generic_issues:
            for issue in report.generic_issues:
                row = Adw.ActionRow()
                row.set_title(issue)
                self._generic_group.add(row)
                self._generic_rows.append(row)
        else:
            row = Adw.ActionRow()
            row.set_title(_("Sem problemas gerais relevantes"))
            self._generic_group.add(row)
            self._generic_rows.append(row)

    def _show_samples(self, _button, mod_name: str, samples: list[str]):
        dialog = Adw.AlertDialog(
            heading=_("Exemplos para") + f" {mod_name}",
            body="\n\n".join(samples),
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self.get_root())

    def _clear_rows(self, group: Adw.PreferencesGroup, rows: list[Adw.ActionRow]):
        for row in rows:
            group.remove(row)
        rows.clear()
