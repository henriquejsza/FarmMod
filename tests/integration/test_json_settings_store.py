import farmmod_hub.infrastructure.config.json_store as json_store_module


def test_returns_defaults_when_config_is_missing(tmp_path, monkeypatch):
    default_mods_dir = tmp_path / "mods-default"
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": default_mods_dir,
    )

    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")

    assert store.get_active_game() == "fs19"
    assert [game_id for game_id, _ in store.list_games()] == ["fs19", "fs22", "fs25"]
    assert store.get_mods_dir() == default_mods_dir
    assert store.get_language() == "pt_BR"
    assert store.get_confirm_delete() is True


def test_setters_persist_data_between_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": tmp_path / "mods-default",
    )
    config_dir = tmp_path / "config"

    first = json_store_module.JsonSettingsStore(config_dir=config_dir)
    first.set_mods_dir(tmp_path / "mods-custom")
    first.set_language("en")
    first.set_confirm_delete(False)

    second = json_store_module.JsonSettingsStore(config_dir=config_dir)

    assert second.get_mods_dir() == tmp_path / "mods-custom"
    assert second.get_language() == "en"
    assert second.get_confirm_delete() is False


def test_profiles_and_paths_are_isolated_per_game(tmp_path, monkeypatch):
    defaults = {
        "fs19": tmp_path / "mods-fs19",
        "fs22": tmp_path / "mods-fs22",
        "fs25": tmp_path / "mods-fs25",
    }

    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": defaults[game_id],
    )

    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")
    assert store.get_mods_dir() == defaults["fs19"]

    store.create_profile("Mapa 19")
    fs19_mods_dir = store.get_mods_dir()

    store.set_active_game("fs22")
    assert store.get_mods_dir() == defaults["fs22"]
    assert store.get_active_profile() == "Default"
    assert all(name != "Mapa 19" for name, _ in store.list_profiles())

    store.create_profile("Mapa 22")
    fs22_mods_dir = store.get_mods_dir()

    store.set_active_game("fs19")
    assert store.get_mods_dir() == fs19_mods_dir
    assert any(name == "Mapa 19" for name, _ in store.list_profiles())
    assert all(name != "Mapa 22" for name, _ in store.list_profiles())

    store.set_active_game("fs22")
    assert store.get_mods_dir() == fs22_mods_dir


def test_switching_profile_updates_live_game_mods_mount(tmp_path, monkeypatch):
    default_mods_dir = tmp_path / "mods-default"
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": default_mods_dir,
    )

    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")
    store.get_mods_dir().mkdir(parents=True, exist_ok=True)
    (store.get_mods_dir() / "default_mod.zip").write_text("ok")

    _name, second_profile_path = store.create_profile("Perfil 2")
    assert default_mods_dir.is_symlink()
    assert default_mods_dir.resolve() == second_profile_path.resolve()

    store.set_active_profile("Default")
    default_profile_path = store.get_mods_dir()
    assert default_mods_dir.is_symlink()
    assert default_mods_dir.resolve() == default_profile_path.resolve()
    assert (default_profile_path / "default_mod.zip").exists()


def test_migrates_legacy_config_to_games_structure(tmp_path, monkeypatch):
    defaults = {
        "fs19": tmp_path / "mods-fs19",
        "fs22": tmp_path / "mods-fs22",
        "fs25": tmp_path / "mods-fs25",
    }
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": defaults[game_id],
    )

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    legacy_mods_dir = tmp_path / "mods-legacy"
    (config_dir / "config.json").write_text(
        '{\n'
        f'  "mods_dir": "{legacy_mods_dir}",\n'
        '  "profiles": [{"name": "Perfil Antigo", "path": "' + str(legacy_mods_dir) + '"}],\n'
        '  "active_profile": "Perfil Antigo"\n'
        '}'
    )

    store = json_store_module.JsonSettingsStore(config_dir=config_dir)

    assert store.get_active_game() == "fs19"
    assert any(name == "Perfil Antigo" for name, _ in store.list_profiles())

    migrated = json_store_module.JsonSettingsStore(config_dir=config_dir)
    migrated_cfg = migrated._load()
    assert "games" in migrated_cfg
    assert "fs22" in migrated_cfg["games"]
    assert "fs25" in migrated_cfg["games"]


def test_export_and_import_profile_bundle_roundtrip(tmp_path, monkeypatch):
    defaults = {
        "fs19": tmp_path / "mods-fs19",
        "fs22": tmp_path / "mods-fs22",
        "fs25": tmp_path / "mods-fs25",
    }
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": defaults[game_id],
    )

    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")
    mods_dir = store.get_mods_dir()
    mods_dir.mkdir(parents=True, exist_ok=True)
    (mods_dir / "FS19_A.zip").write_text("a")
    (mods_dir / "FS19_B" / "modDesc.xml").parent.mkdir(parents=True)
    (mods_dir / "FS19_B" / "modDesc.xml").write_text("<modDesc/>")

    exported = store.export_active_profile_bundle(tmp_path / "backup.zip")
    assert exported["files"] == 2

    store.set_active_game("fs22")
    imported = store.import_profile_bundle(tmp_path / "backup.zip")

    assert imported["game_id"] == "fs19"
    assert store.get_active_game() == "fs19"
    assert store.get_active_profile().startswith("Default")
    imported_dir = store.get_mods_dir()
    assert (imported_dir / "FS19_A.zip").exists()
    assert (imported_dir / "FS19_B" / "modDesc.xml").exists()


def test_invalid_json_falls_back_to_defaults(tmp_path, monkeypatch):
    default_mods_dir = tmp_path / "mods-default"
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": default_mods_dir,
    )

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{invalid json")

    store = json_store_module.JsonSettingsStore(config_dir=config_dir)

    assert store.get_mods_dir() == default_mods_dir
    assert store.get_language() == "pt_BR"
    assert store.get_confirm_delete() is True


def test_profiles_are_created_and_activated(tmp_path, monkeypatch):
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": tmp_path / "mods-default",
    )
    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")

    created_name, created_path = store.create_profile("Servidor")

    assert created_name == "Servidor"
    assert created_path.exists()
    assert store.get_active_profile() == "Servidor"
    assert store.get_mods_dir() == created_path


def test_profile_switch_and_delete_updates_mods_dir(tmp_path, monkeypatch):
    default_mods_dir = tmp_path / "mods-default"
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": default_mods_dir,
    )
    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")
    original_name = store.get_active_profile()
    original_path = store.get_mods_dir()
    original_path.mkdir(parents=True, exist_ok=True)
    (original_path / "A.zip").write_text("a")

    created_name, created_path = store.create_profile("Mapa X")
    assert store.get_mods_dir() == created_path
    assert default_mods_dir.is_symlink()
    assert default_mods_dir.resolve() == created_path.resolve()

    store.set_active_profile(original_name)
    restored_default_path = store.get_mods_dir()
    assert restored_default_path != created_path
    assert restored_default_path.exists()
    assert (restored_default_path / "A.zip").exists()
    assert default_mods_dir.is_symlink()
    assert default_mods_dir.resolve() == restored_default_path.resolve()

    store.delete_profile(created_name)
    assert all(name != created_name for name, _ in store.list_profiles())
    assert store.get_active_profile() == original_name


def test_cannot_remove_last_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": tmp_path / "mods-default",
    )
    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")

    try:
        store.delete_profile(store.get_active_profile())
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "perfil padrao" in str(exc)


def test_cannot_remove_default_profile_when_other_profiles_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": tmp_path / "mods-default",
    )
    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")
    default_name = store.get_active_profile()
    store.create_profile("Servidor")

    try:
        store.delete_profile(default_name)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "perfil padrao" in str(exc)


def test_create_profile_avoids_existing_directory_name(tmp_path, monkeypatch):
    default_mods_dir = tmp_path / "mods-default"
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": default_mods_dir,
    )
    store = json_store_module.JsonSettingsStore(config_dir=tmp_path / "config")

    existing = default_mods_dir.parent / "mods_teste"
    existing.mkdir(parents=True)

    _, created_path = store.create_profile("Teste")

    assert created_path.name != "mods_teste"
    assert created_path.name.startswith("mods_teste")


def test_active_profile_case_is_normalized_to_real_profile_name(tmp_path, monkeypatch):
    default_mods_dir = tmp_path / "mods-default"
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": default_mods_dir,
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        '{\n'
        '  "profiles": [{"name": "Default", "path": "' + str(default_mods_dir) + '"}],\n'
        '  "active_profile": "default"\n'
        '}'
    )

    store = json_store_module.JsonSettingsStore(config_dir=config_dir)

    assert store.get_active_profile() == "Default"
    assert store.get_mods_dir() == default_mods_dir


def test_profile_using_default_path_is_renamed_to_default(tmp_path, monkeypatch):
    default_mods_dir = tmp_path / "mods-default"
    monkeypatch.setattr(
        json_store_module,
        "find_mods_dir",
        lambda game_id="fs19": default_mods_dir,
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        '{\n'
        '  "profiles": [\n'
        '    {"name": "Perfil 6", "path": "' + str(default_mods_dir) + '"},\n'
        '    {"name": "Perfil 2", "path": "' + str(tmp_path / "mods_perfil_2") + '"}\n'
        '  ],\n'
        '  "active_profile": "Perfil 6"\n'
        '}'
    )

    store = json_store_module.JsonSettingsStore(config_dir=config_dir)

    assert store.get_active_profile() == "Default"
    assert store.get_mods_dir() == default_mods_dir
    assert any(name == "Default" for name, _path in store.list_profiles())
