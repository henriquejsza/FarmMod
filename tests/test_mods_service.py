from pathlib import Path

from farmmod_hub.application.mods_service import ModsService
from farmmod_hub.domain import InstallReport


class FakeRepository:
    def __init__(self):
        self.installed_count = 0
        self.mods: list[Path] = []
        self.removed: list[Path] = []

    def install(self, paths: list[Path]) -> InstallReport:
        report = InstallReport()
        report.installed = [p.name for p in paths]
        self.installed_count += len(paths)
        self.mods.extend(paths)
        return report

    def count_installed(self) -> int:
        return self.installed_count

    def list_installed(self) -> list[Path]:
        return self.mods

    def remove(self, mod_path: Path):
        self.removed.append(mod_path)


def test_install_returns_expected_tuple(tmp_path):
    repo = FakeRepository()
    service = ModsService(repo)
    mod_path = tmp_path / "FS19_Test.zip"

    installed, updated, errors, warnings = service.install([mod_path])

    assert installed == ["FS19_Test.zip"]
    assert updated == []
    assert errors == []
    assert warnings == []


def test_count_and_list_are_forwarded_to_repository(tmp_path):
    repo = FakeRepository()
    service = ModsService(repo)
    mod_path = tmp_path / "FS19_Test.zip"
    service.install([mod_path])

    assert service.count_installed() == 1
    assert service.list_installed() == [mod_path]


def test_remove_is_forwarded_to_repository(tmp_path):
    repo = FakeRepository()
    service = ModsService(repo)
    mod_path = tmp_path / "FS19_Test.zip"

    service.remove(mod_path)

    assert repo.removed == [mod_path]
