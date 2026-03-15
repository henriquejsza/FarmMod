import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from gi.repository import GLib

from farmmod_hub.application import ModsService
from farmmod_hub.infrastructure.logs import (
    LogAnalysisReport,
    analyze_log_file,
    export_log_report_text,
    format_log_report_text,
)
from farmmod_hub.infrastructure.steam import get_game_spec

InstallCallback = Callable[[list[str], list[str], list[str], list[str]], None]


class SettingsStore(Protocol):
    def get_mods_dir(self) -> Path:
        ...

    def get_confirm_delete(self) -> bool:
        ...

    def get_active_game(self) -> str:
        ...


class MainController:
    def __init__(self, mods_service: ModsService, settings: SettingsStore):
        self._mods_service = mods_service
        self._settings = settings

    def list_installed(self) -> list[Path]:
        return self._mods_service.list_installed()

    def count_installed(self) -> int:
        return self._mods_service.count_installed()

    def remove_mod(self, mod_path: Path):
        self._mods_service.remove(mod_path)

    def get_mods_dir(self) -> Path:
        return self._settings.get_mods_dir()

    def get_active_game(self) -> str:
        return self._settings.get_active_game()

    def get_active_game_label(self) -> str:
        game_id = self._settings.get_active_game()
        return get_game_spec(game_id).label

    def analyze_log(self, log_path: Path) -> LogAnalysisReport:
        return analyze_log_file(log_path)

    def build_log_report_text(
        self,
        report: LogAnalysisReport,
        game_id: str | None = None,
        game_label: str | None = None,
    ) -> str:
        resolved_game_id = game_id or self.get_active_game()
        resolved_game_label = game_label or get_game_spec(resolved_game_id).label
        return format_log_report_text(report, resolved_game_id, resolved_game_label)

    def export_log_report(
        self,
        report: LogAnalysisReport,
        destination: Path,
        game_id: str | None = None,
        game_label: str | None = None,
    ) -> Path:
        resolved_game_id = game_id or self.get_active_game()
        resolved_game_label = game_label or get_game_spec(resolved_game_id).label
        return export_log_report_text(report, destination, resolved_game_id, resolved_game_label)

    def get_confirm_delete(self) -> bool:
        return self._settings.get_confirm_delete()

    def install_async(self, paths: list[Path], on_done: InstallCallback):
        threading.Thread(
            target=self._install_thread,
            args=(paths, on_done),
            daemon=True,
        ).start()

    def _install_thread(self, paths: list[Path], on_done: InstallCallback):
        try:
            installed, updated, errors, warnings = self._mods_service.install(paths)
        except Exception as exc:  # pragma: no cover
            installed, updated, errors, warnings = [], [], [str(exc)], []
        GLib.idle_add(on_done, installed, updated, errors, warnings)
