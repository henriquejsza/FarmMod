"""Testes para instalacao de mods (sem dependencia de GTK)."""

import zipfile
import pytest
from pathlib import Path

from farmmod_hub.domain import MOD_DESC_XML
from farmmod_hub.infrastructure.mods.filesystem_repository import FilesystemModsRepository


class FakeSettings:
    def __init__(self, mods_dir: Path, active_game: str = "fs19"):
        self._mods_dir = mods_dir
        self._active_game = active_game

    def get_mods_dir(self) -> Path:
        return self._mods_dir

    def get_active_game(self) -> str:
        return self._active_game


@pytest.fixture
def repository(mods_dir):
    return FilesystemModsRepository(FakeSettings(mods_dir))


@pytest.fixture
def mods_dir(tmp_path):
    target = tmp_path / "mods"
    target.mkdir()
    return target


def make_zip(path: Path, name="FS19_TestMod.zip", with_desc=True) -> Path:
    zip_path = path / name
    with zipfile.ZipFile(zip_path, "w") as zf:
        if with_desc:
            zf.writestr(MOD_DESC_XML, "<modDesc/>")
    return zip_path


def make_nested_zip(path: Path, name="FS19_Nested.zip") -> Path:
    zip_path = path / name
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"FS19_Nested/{MOD_DESC_XML}", "<modDesc/>")
    return zip_path


def make_folder(path: Path, with_desc=True) -> Path:
    folder = path / "FS19_TestMod"
    folder.mkdir()
    if with_desc:
        (folder / MOD_DESC_XML).write_text("<modDesc/>")
    return folder


def make_nested_folder(path: Path) -> Path:
    outer = path / "FS19_Nested"
    inner = outer / "inner"
    inner.mkdir(parents=True)
    (inner / MOD_DESC_XML).write_text("<modDesc/>")
    return outer


class TestInstallZip:
    def test_valid_zip_is_installed(self, tmp_path, mods_dir, repository):
        src = make_zip(tmp_path)
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == ["FS19_TestMod.zip"]
        assert updated == []
        assert errors == []
        assert (mods_dir / "FS19_TestMod.zip").exists()

    def test_zip_without_moddesc_is_rejected(self, tmp_path, repository):
        src = make_zip(tmp_path, with_desc=False)
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == []
        assert any(MOD_DESC_XML in e for e in errors)

    def test_zip_with_moddesc_not_at_root_is_rejected(self, tmp_path, repository):
        src = make_nested_zip(tmp_path)
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == []
        assert updated == []
        assert any("não está na raiz" in e for e in errors)

    def test_zip_from_other_game_version_emits_warning_and_installs(self, tmp_path, mods_dir, repository):
        src = make_zip(tmp_path, name="FS22_TestMod.zip")
        report = repository.install([src])
        installed, updated, errors = report.as_tuple()
        assert installed == ["FS22_TestMod.zip"]
        assert updated == []
        assert errors == []
        assert any("nome indica mod de FS22" in w for w in report.warnings)
        assert (mods_dir / "FS22_TestMod.zip").exists()

    def test_zip_matching_active_game_does_not_warn(self, tmp_path, mods_dir):
        repository = FilesystemModsRepository(FakeSettings(mods_dir, active_game="fs22"))
        src = make_zip(tmp_path, name="FS22_TestMod.zip")

        report = repository.install([src])
        installed, updated, errors = report.as_tuple()

        assert installed == ["FS22_TestMod.zip"]
        assert updated == []
        assert errors == []
        assert report.warnings == []


class TestInstallFolder:
    def test_valid_folder_is_installed(self, tmp_path, mods_dir, repository):
        src = make_folder(tmp_path)
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == ["FS19_TestMod"]
        assert updated == []
        assert errors == []
        assert (mods_dir / "FS19_TestMod").is_dir()

    def test_folder_without_moddesc_is_rejected(self, tmp_path, repository):
        src = make_folder(tmp_path, with_desc=False)
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == []
        assert any(MOD_DESC_XML in e for e in errors)

    def test_folder_with_nested_moddesc_is_rejected(self, tmp_path, repository):
        src = make_nested_folder(tmp_path)
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == []
        assert updated == []
        assert any("subpasta" in e for e in errors)


class TestInstallUpdate:
    def test_reinstall_zip_goes_to_updated(self, tmp_path, repository):
        src = make_zip(tmp_path)
        repository.install([src])
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == []
        assert updated == ["FS19_TestMod.zip"]
        assert errors == []

    def test_reinstall_folder_goes_to_updated(self, tmp_path, repository):
        src = make_folder(tmp_path)
        repository.install([src])
        installed, updated, errors = repository.install([src]).as_tuple()
        assert installed == []
        assert updated == ["FS19_TestMod"]
        assert errors == []

    def test_mixed_new_and_updated(self, tmp_path, repository):
        src_a = make_zip(tmp_path, name="FS19_A.zip")
        src_b = make_zip(tmp_path, name="FS19_B.zip")
        repository.install([src_a])
        installed, updated, errors = repository.install([src_a, src_b]).as_tuple()
        assert "FS19_A.zip" in updated
        assert "FS19_B.zip" in installed
        assert errors == []

    def test_same_mod_as_zip_and_folder_in_batch_is_rejected(self, tmp_path, repository):
        zip_mod = make_zip(tmp_path, name="FS19_Same.zip")
        folder_mod = tmp_path / "FS19_Same"
        folder_mod.mkdir()
        (folder_mod / MOD_DESC_XML).write_text("<modDesc/>")

        installed, updated, errors = repository.install([zip_mod, folder_mod]).as_tuple()
        assert installed == []
        assert updated == []
        assert len(errors) == 2
        assert all("ZIP e pasta" in e for e in errors)

    def test_rejects_zip_when_folder_counterpart_already_installed(self, tmp_path, mods_dir, repository):
        existing_folder = mods_dir / "FS19_Already"
        existing_folder.mkdir()
        (existing_folder / MOD_DESC_XML).write_text("<modDesc/>")
        incoming_zip = make_zip(tmp_path, name="FS19_Already.zip")

        installed, updated, errors = repository.install([incoming_zip]).as_tuple()
        assert installed == []
        assert updated == []
        assert any("já existe versão ZIP/pasta" in e for e in errors)

    def test_rejects_unsupported_file_type(self, tmp_path, repository):
        invalid = tmp_path / "FS19_Invalid.rar"
        invalid.write_text("not-a-zip")

        installed, updated, errors = repository.install([invalid]).as_tuple()
        assert installed == []
        assert updated == []
        assert any("formato não suportado" in e for e in errors)


class TestCountInstalled:
    def test_counts_zips_and_folders(self, mods_dir, repository):
        (mods_dir / "FS19_A.zip").write_text("")
        (mods_dir / "FS19_B").mkdir()
        assert repository.count_installed() == 2

    def test_returns_zero_when_dir_missing(self, tmp_path):
        missing = tmp_path / "nonexistent"
        repository = FilesystemModsRepository(FakeSettings(missing))
        assert repository.count_installed() == 0
