import shutil
import zipfile
from pathlib import Path
from typing import Protocol

from farmmod_hub.domain import MOD_DESC_XML, InstallReport, is_supported_mod_path
from farmmod_hub.infrastructure.mods.validator import build_batch_validation_state, validate_source


class ModsSettings(Protocol):
    def get_mods_dir(self) -> Path:
        ...

    def get_active_game(self) -> str:
        ...


class FilesystemModsRepository:
    def __init__(self, settings: ModsSettings):
        self._settings = settings

    def install(self, paths: list[Path]) -> InstallReport:
        mods_dir = self._settings.get_mods_dir()
        mods_dir.mkdir(parents=True, exist_ok=True)

        report = InstallReport()
        validation_state = build_batch_validation_state(
            paths,
            active_game=self._settings.get_active_game(),
        )

        for src in paths:
            try:
                validation = validate_source(src, mods_dir, validation_state)
                if validation.warnings:
                    report.warnings.extend(f"{src.name}: {warn}" for warn in validation.warnings)

                if validation.errors:
                    report.errors.extend(f"{src.name}: {err}" for err in validation.errors)
                    continue

                if src.suffix.lower() == ".zip":
                    self._install_zip(src, mods_dir, report)
                else:
                    self._install_folder(src, mods_dir, report)
            except Exception as exc:
                report.errors.append(f"{src.name}: {exc}")

        return report

    def count_installed(self) -> int:
        mods_dir = self._settings.get_mods_dir()
        if not mods_dir.exists():
            return 0
        return sum(1 for p in mods_dir.iterdir() if is_supported_mod_path(p))

    def list_installed(self) -> list[Path]:
        mods_dir = self._settings.get_mods_dir()
        if not mods_dir.exists():
            return []
        return sorted(
            (p for p in mods_dir.iterdir() if is_supported_mod_path(p)),
            key=lambda p: p.name.lower(),
        )

    def remove(self, mod_path: Path):
        if mod_path.is_dir():
            shutil.rmtree(mod_path)
        else:
            mod_path.unlink()

    def _install_zip(self, src: Path, mods_dir: Path, report: InstallReport):
        with zipfile.ZipFile(src) as zf:
            has_desc = any(
                n == MOD_DESC_XML or n.endswith(f"/{MOD_DESC_XML}")
                for n in zf.namelist()
            )
            if not has_desc:
                report.errors.append(f"{src.name}: sem {MOD_DESC_XML} na raiz")
                return

        dest = mods_dir / src.name
        was_updated = dest.exists()
        shutil.copy2(src, dest)
        (report.updated if was_updated else report.installed).append(src.name)

    def _install_folder(self, src: Path, mods_dir: Path, report: InstallReport):
        if not (src / MOD_DESC_XML).exists():
            report.errors.append(f"{src.name}: sem {MOD_DESC_XML}")
            return

        dest = mods_dir / src.name
        was_updated = dest.exists()
        if was_updated:
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        (report.updated if was_updated else report.installed).append(src.name)
