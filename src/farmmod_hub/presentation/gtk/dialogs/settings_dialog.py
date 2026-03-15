from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk

from farmmod_hub.infrastructure.config import get_settings_store
from farmmod_hub.infrastructure.config.json_store import DEFAULT_PROFILE_NAME
from farmmod_hub.presentation.i18n import _


class SettingsDialog(Adw.PreferencesDialog):
    def __init__(self, parent_window, on_mods_dir_changed=None, on_language_changed=None):
        super().__init__()
        self.set_title(_("Configurações"))
        self._parent = parent_window
        self._on_mods_dir_changed = on_mods_dir_changed
        self._on_language_changed = on_language_changed
        self._settings = get_settings_store()
        self._game_ids: list[str] = []
        self._profile_names: list[str] = []
        self._updating_game_selection = False
        self._updating_profile_selection = False
        self._remove_profile_btn: Gtk.Button | None = None

        page = Adw.PreferencesPage()
        page.set_title(_("Geral"))
        page.set_icon_name("preferences-system-symbolic")

        page.add(self._build_game_group())
        page.add(self._build_dir_group())
        page.add(self._build_profiles_group())
        page.add(self._build_profile_backup_group())
        page.add(self._build_lang_group())
        page.add(self._build_behavior_group())

        self.add(page)

    def _build_game_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title(_("Jogo"))
        group.set_description(_("Escolha qual Farming Simulator voce quer gerenciar"))

        self._game_row = Adw.ComboRow()
        self._game_row.set_title(_("Jogo ativo"))
        self._game_row.add_prefix(Gtk.Image.new_from_icon_name("applications-games-symbolic"))
        self._refresh_game_row()
        self._game_row.connect("notify::selected", self._on_game_selected)
        group.add(self._game_row)

        return group

    def _refresh_game_row(self):
        games = self._settings.list_games()
        self._game_ids = [game_id for game_id, _label in games]
        game_labels = [self._display_game_name(game_id, label) for game_id, label in games]
        model = Gtk.StringList.new(game_labels)

        selected_idx = 0
        active_game = self._settings.get_active_game()
        if active_game in self._game_ids:
            selected_idx = self._game_ids.index(active_game)

        self._updating_game_selection = True
        self._game_row.set_model(model)
        self._game_row.set_selected(selected_idx)
        self._updating_game_selection = False

    def _display_game_name(self, game_id: str, default_label: str) -> str:
        short_map = {
            "fs19": "FS19",
            "fs22": "FS22",
            "fs25": "FS25",
        }
        return short_map.get(game_id, default_label)

    def _on_game_selected(self, row, _pspec):
        if self._updating_game_selection:
            return

        selected_idx = row.get_selected()
        if selected_idx < 0 or selected_idx >= len(self._game_ids):
            return

        game_id = self._game_ids[selected_idx]
        self._settings.set_active_game(game_id)
        self._refresh_profile_row()
        current_dir = self._settings.get_mods_dir()
        self._dir_row.set_subtitle(str(current_dir))
        if self._on_mods_dir_changed:
            self._on_mods_dir_changed(current_dir)

    def _build_dir_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title(_("Diretório de Mods"))
        group.set_description(_("Pasta onde os mods do jogo selecionado sao instalados"))

        self._dir_row = Adw.ActionRow()
        self._dir_row.set_title(_("Pasta"))
        self._dir_row.set_subtitle(str(self._settings.get_mods_dir()))
        self._dir_row.set_subtitle_selectable(True)
        self._dir_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))

        choose_btn = Gtk.Button(icon_name="document-open-symbolic")
        choose_btn.add_css_class("flat")
        choose_btn.set_valign(Gtk.Align.CENTER)
        choose_btn.set_tooltip_text(_("Escolher pasta"))
        choose_btn.connect("clicked", self._on_choose_folder)
        self._dir_row.add_suffix(choose_btn)

        reset_btn = Gtk.Button(icon_name="edit-undo-symbolic")
        reset_btn.add_css_class("flat")
        reset_btn.set_valign(Gtk.Align.CENTER)
        reset_btn.set_tooltip_text(_("Restaurar padrão"))
        reset_btn.connect("clicked", self._on_reset)
        self._dir_row.add_suffix(reset_btn)

        group.add(self._dir_row)
        return group

    def _build_profiles_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title(_("Perfis"))
        group.set_description(_("Coleções separadas para cada mapa/sessão"))

        self._profile_row = Adw.ComboRow()
        self._profile_row.set_title(_("Perfil ativo"))
        self._profile_row.add_prefix(Gtk.Image.new_from_icon_name("view-grid-symbolic"))
        group.add(self._profile_row)

        manage_row = Adw.ActionRow()
        manage_row.set_title(_("Gerenciar perfis"))

        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.set_tooltip_text(_("Novo perfil"))
        add_btn.connect("clicked", self._on_add_profile)
        manage_row.add_suffix(add_btn)

        remove_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        remove_btn.add_css_class("flat")
        remove_btn.set_valign(Gtk.Align.CENTER)
        remove_btn.set_tooltip_text(_("Remover perfil"))
        remove_btn.connect("clicked", self._on_remove_profile)
        manage_row.add_suffix(remove_btn)
        self._remove_profile_btn = remove_btn

        self._refresh_profile_row()
        self._profile_row.connect("notify::selected", self._on_profile_selected)

        group.add(manage_row)
        return group

    def _build_profile_backup_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title(_("Backup de perfil"))

        row = Adw.ActionRow()
        row.set_title(_("Gerenciar perfis"))
        row.set_subtitle(_("Exportar perfil ativo"))

        export_btn = Gtk.Button.new_from_icon_name("document-save-symbolic")
        export_btn.add_css_class("flat")
        export_btn.set_tooltip_text(_("Exportar perfil ativo"))
        export_btn.connect("clicked", self._on_export_profile)
        row.add_suffix(export_btn)

        import_btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
        import_btn.add_css_class("flat")
        import_btn.set_tooltip_text(_("Importar backup"))
        import_btn.connect("clicked", self._on_import_profile)
        row.add_suffix(import_btn)

        group.add(row)
        return group

    def _refresh_profile_row(self, selected_name: str | None = None):
        profiles = self._settings.list_profiles()
        self._profile_names = [name for name, profile_path in profiles]
        model = Gtk.StringList.new(self._profile_names)

        target = selected_name or self._settings.get_active_profile()
        selected_idx = 0
        if target in self._profile_names:
            selected_idx = self._profile_names.index(target)

        self._updating_profile_selection = True
        self._profile_row.set_model(model)
        self._profile_row.set_selected(selected_idx)
        self._updating_profile_selection = False
        self._update_profile_actions(selected_idx)

    def _on_profile_selected(self, row, _pspec):
        if self._updating_profile_selection:
            return

        selected_idx = row.get_selected()
        if selected_idx < 0 or selected_idx >= len(self._profile_names):
            return

        self._update_profile_actions(selected_idx)

        name = self._profile_names[selected_idx]
        try:
            self._settings.set_active_profile(name)
        except ValueError as exc:
            self._show_error(_("Não foi possível alterar perfil."), str(exc))
            self._refresh_profile_row()
            return

        current_dir = self._settings.get_mods_dir()
        self._dir_row.set_subtitle(str(current_dir))
        if self._on_mods_dir_changed:
            self._on_mods_dir_changed(current_dir)

    def _on_add_profile(self, *args):
        existing_names = {name.casefold() for name in self._profile_names}
        idx = 2
        while True:
            candidate = f"{_('Perfil')} {idx}"
            if candidate.casefold() not in existing_names:
                break
            idx += 1

        try:
            name, path = self._settings.create_profile(candidate)
        except ValueError as exc:
            self._show_error(_("Não foi possível criar perfil."), str(exc))
            return

        self._refresh_profile_row(name)
        self._dir_row.set_subtitle(str(path))
        if self._on_mods_dir_changed:
            self._on_mods_dir_changed(path)

    def _on_remove_profile(self, *args):
        selected_idx = self._profile_row.get_selected()
        if selected_idx < 0 or selected_idx >= len(self._profile_names):
            return

        selected_name = self._profile_names[selected_idx]
        try:
            self._settings.delete_profile(selected_name)
        except ValueError as exc:
            self._show_error(_("Não foi possível remover perfil."), str(exc))
            return

        self._refresh_profile_row()
        current_dir = self._settings.get_mods_dir()
        self._dir_row.set_subtitle(str(current_dir))
        if self._on_mods_dir_changed:
            self._on_mods_dir_changed(current_dir)

    def _update_profile_actions(self, selected_idx: int):
        if self._remove_profile_btn is None:
            return

        is_valid = 0 <= selected_idx < len(self._profile_names)
        if not is_valid:
            self._remove_profile_btn.set_sensitive(False)
            return

        selected_name = self._profile_names[selected_idx]
        can_remove = selected_name.casefold() != DEFAULT_PROFILE_NAME.casefold()
        self._remove_profile_btn.set_sensitive(can_remove)

    def _show_error(self, heading: str, detail: str):
        dialog = Adw.AlertDialog(heading=heading, body=detail)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)

    def _show_info(self, heading: str, detail: str):
        dialog = Adw.AlertDialog(heading=heading, body=detail)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)

    def _on_export_profile(self, *args):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Salvar backup de perfil"))
        active_profile = self._settings.get_active_profile()
        active_game = self._settings.get_active_game().upper()
        file_name = f"{active_game}_{active_profile}.zip"
        dialog.set_initial_name(file_name)
        dialog.save(self._parent, None, self._on_export_profile_done)

    def _on_export_profile_done(self, dialog, result):
        try:
            output_file = dialog.save_finish(result)
        except Exception:
            return
        if output_file is None or not output_file.get_path():
            return

        try:
            info = self._settings.export_active_profile_bundle(Path(output_file.get_path()))
        except Exception as exc:
            self._show_error(_("Nao foi possivel exportar perfil."), str(exc))
            return

        self._show_info(
            _("Backup exportado com sucesso."),
            _("Arquivo de backup")
            + f": {info['archive']}\n"
            + f"Mods: {info['files']}",
        )

    def _on_import_profile(self, *args):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Importar backup"))

        filter_zip = Gtk.FileFilter()
        filter_zip.set_name(_("Arquivo de backup"))
        filter_zip.add_pattern("*.zip")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_zip)
        dialog.set_filters(filters)

        dialog.open(self._parent, None, self._on_import_profile_done)

    def _on_import_profile_done(self, dialog, result):
        try:
            selected_file = dialog.open_finish(result)
        except Exception:
            return
        if selected_file is None or not selected_file.get_path():
            return

        try:
            info = self._settings.import_profile_bundle(Path(selected_file.get_path()))
        except Exception as exc:
            self._show_error(_("Nao foi possivel importar backup."), str(exc))
            return

        self._refresh_game_row()
        imported_profile_name = str(info["profile_name"])
        imported_game_id = str(info["game_id"])
        imported_mods_dir = str(info["mods_dir"])

        self._refresh_profile_row(imported_profile_name)
        current_dir = self._settings.get_mods_dir()
        self._dir_row.set_subtitle(str(current_dir))
        if self._on_mods_dir_changed:
            self._on_mods_dir_changed(current_dir)

        self._show_info(
            _("Backup importado com sucesso."),
            f"{imported_game_id.upper()} - {imported_profile_name}\n"
            + _("Pasta")
            + f": {imported_mods_dir}\nMods: {info['files']}",
        )

    def _build_lang_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title(_("Idioma"))
        group.set_description(_("Idioma da interface"))

        lang_row = Adw.ComboRow()
        lang_row.set_title(_("Idioma"))
        lang_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-desktop-locale-symbolic"))

        model = Gtk.StringList.new(["Português (Brasil)", "English"])
        lang_row.set_model(model)

        current = self._settings.get_language()
        lang_row.set_selected(0 if current == "pt_BR" else 1)
        lang_row.connect("notify::selected", self._on_lang_selected)

        group.add(lang_row)
        return group

    def _build_behavior_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title(_("Comportamento"))

        confirm_row = Adw.SwitchRow()
        confirm_row.set_title(_("Confirmar exclusão"))
        confirm_row.set_subtitle(_("Pedir confirmação antes de excluir um mod"))
        confirm_row.add_prefix(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        confirm_row.set_active(self._settings.get_confirm_delete())
        confirm_row.connect(
            "notify::active",
            lambda row, pspec: self._settings.set_confirm_delete(row.get_active()),
        )

        group.add(confirm_row)
        return group

    def _on_choose_folder(self, *args):
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Escolher pasta de mods"))

        mods_dir = self._settings.get_mods_dir()
        initial = mods_dir if mods_dir.exists() else mods_dir.parent if mods_dir.parent.exists() else Path.home()
        dialog.set_initial_folder(Gio.File.new_for_path(str(initial)))

        dialog.select_folder(self._parent, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except Exception:
            return
        if folder is None:
            return
        self._apply_dir(Path(folder.get_path()))

    def _on_reset(self, *args):
        self._apply_dir(self._settings.default_mods_dir)

    def _apply_dir(self, path: Path):
        self._settings.set_mods_dir(path)
        self._dir_row.set_subtitle(str(path))
        if self._on_mods_dir_changed:
            self._on_mods_dir_changed(path)

    def _on_lang_selected(self, row, _pspec):
        lang = "pt_BR" if row.get_selected() == 0 else "en"
        if lang == self._settings.get_language():
            return
        self._settings.set_language(lang)
        if self._on_language_changed:
            self._on_language_changed(lang)
