from datetime import datetime, timezone
import json
import re
from pathlib import Path
import zipfile

from farmmod_hub.infrastructure.steam import SUPPORTED_GAMES, find_mods_dir, get_game_spec

DEFAULT_PROFILE_NAME = "Default"
DEFAULT_GAME_ID = "fs19"


class JsonSettingsStore:
    def __init__(self, config_dir: Path | None = None):
        base_dir = config_dir or (Path.home() / ".config" / "farmmod_hub")
        if config_dir is None:
            legacy_dir = Path.home() / ".config" / "mod_fs19"
            legacy_file = legacy_dir / "config.json"
            new_file = base_dir / "config.json"
            if not new_file.exists() and legacy_file.exists():
                base_dir.mkdir(parents=True, exist_ok=True)
                new_file.write_bytes(legacy_file.read_bytes())
        self._config_dir = base_dir
        self._config_file = base_dir / "config.json"
        self._default_mods_dirs = {
            game_id: find_mods_dir(game_id) for game_id in SUPPORTED_GAMES
        }

    @property
    def default_mods_dir(self) -> Path:
        return self.get_default_mods_dir()

    def _load(self) -> dict:
        if not self._config_file.exists():
            return {}
        try:
            return json.loads(self._config_file.read_text())
        except Exception:
            return {}

    def _save(self, data: dict):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file.write_text(json.dumps(data, indent=2))

    def _normalize_game_id(self, game_id: str) -> str:
        key = game_id.strip().lower()
        if key not in SUPPORTED_GAMES:
            raise ValueError("Jogo nao suportado")
        return key

    def _resolve_game_id(self, cfg: dict, game_id: str | None) -> str:
        wanted = game_id or cfg["active_game"]
        return self._normalize_game_id(wanted)

    def _normalize_game_profiles(self, game_id: str, source_cfg: dict) -> dict:
        profiles = source_cfg.get("profiles")
        normalized_profiles: list[dict[str, str]] = []
        seen_names: set[str] = set()

        if isinstance(profiles, list):
            for profile in profiles:
                if not isinstance(profile, dict):
                    continue

                name = str(profile.get("name", "")).strip()
                path = str(profile.get("path", "")).strip()
                if not name or not path:
                    continue

                folded_name = name.casefold()
                if folded_name in seen_names:
                    continue

                normalized_profiles.append({"name": name, "path": path})
                seen_names.add(folded_name)

        default_path = self._default_mods_dirs[game_id]
        if not normalized_profiles:
            legacy_path = source_cfg.get("mods_dir")
            profile_path = str(legacy_path) if legacy_path else str(default_path)
            normalized_profiles = [{"name": DEFAULT_PROFILE_NAME, "path": profile_path}]

        active_profile = str(source_cfg.get("active_profile", "")).strip()

        has_default_name = any(
            profile["name"].casefold() == DEFAULT_PROFILE_NAME.casefold()
            for profile in normalized_profiles
        )
        if not has_default_name:
            same_path_idx = next(
                (
                    idx
                    for idx, profile in enumerate(normalized_profiles)
                    if Path(profile["path"]) == default_path
                ),
                None,
            )
            if same_path_idx is not None:
                old_name = normalized_profiles[same_path_idx]["name"]
                normalized_profiles[same_path_idx]["name"] = DEFAULT_PROFILE_NAME
                if active_profile.casefold() == old_name.casefold():
                    active_profile = DEFAULT_PROFILE_NAME
            else:
                normalized_profiles.insert(
                    0,
                    {"name": DEFAULT_PROFILE_NAME, "path": str(default_path)},
                )

        canonical_active = next(
            (
                profile["name"]
                for profile in normalized_profiles
                if profile["name"].casefold() == active_profile.casefold()
            ),
            None,
        )
        if canonical_active is None:
            active_profile = normalized_profiles[0]["name"]
        else:
            active_profile = canonical_active

        return {
            "profiles": normalized_profiles,
            "active_profile": active_profile,
        }

    def _sync_legacy_fields(self, cfg: dict):
        active_game_cfg = cfg["games"][cfg["active_game"]]
        cfg["mods_dir"] = str(self._active_profile_path(active_game_cfg))
        cfg["profiles"] = active_game_cfg["profiles"]
        cfg["active_profile"] = active_game_cfg["active_profile"]

    def _normalize_settings(self, cfg: dict) -> dict:
        active_game = str(cfg.get("active_game", DEFAULT_GAME_ID)).strip().lower()
        if active_game not in SUPPORTED_GAMES:
            active_game = DEFAULT_GAME_ID

        games_cfg = cfg.get("games")
        normalized_games: dict[str, dict] = {}

        for game_id in SUPPORTED_GAMES:
            source_cfg: dict = {}

            if isinstance(games_cfg, dict) and isinstance(games_cfg.get(game_id), dict):
                source_cfg = dict(games_cfg[game_id])
            elif game_id == DEFAULT_GAME_ID:
                source_cfg = {
                    "profiles": cfg.get("profiles"),
                    "active_profile": cfg.get("active_profile", ""),
                    "mods_dir": cfg.get("mods_dir"),
                }

            normalized_games[game_id] = self._normalize_game_profiles(game_id, source_cfg)

        cfg["active_game"] = active_game
        cfg["games"] = normalized_games
        self._sync_legacy_fields(cfg)
        return cfg

    def _load_normalized(self) -> dict:
        raw_cfg = self._load()
        normalized_cfg = self._normalize_settings(dict(raw_cfg))
        changed_from_raw = normalized_cfg != raw_cfg
        changed_links = self._sync_game_mods_links(normalized_cfg)
        if changed_from_raw or changed_links:
            self._save(normalized_cfg)
        return normalized_cfg

    def _find_profile_index(self, game_cfg: dict, name: str) -> int | None:
        wanted = name.strip().casefold()
        for idx, profile in enumerate(game_cfg["profiles"]):
            if profile["name"].casefold() == wanted:
                return idx
        return None

    def _active_profile_path(self, game_cfg: dict) -> Path:
        active_name = game_cfg["active_profile"]
        for profile in game_cfg["profiles"]:
            if profile["name"] == active_name:
                return Path(profile["path"])

        first_profile = game_cfg["profiles"][0]
        game_cfg["active_profile"] = first_profile["name"]
        return Path(first_profile["path"])

    def _build_profile_path(self, game_id: str, game_cfg: dict, name: str) -> Path:
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "perfil"
        base_name = f"mods_{slug}"
        parent_dir = self._default_mods_dirs[game_id].parent
        used_paths = {Path(profile["path"]) for profile in game_cfg["profiles"]}

        candidate = parent_dir / base_name
        suffix = 2
        while candidate in used_paths or candidate.exists():
            candidate = parent_dir / f"{base_name}_{suffix}"
            suffix += 1

        return candidate

    def _build_unique_profile_name(self, game_cfg: dict, base_name: str) -> str:
        clean = base_name.strip() or "Perfil Importado"
        used = {profile["name"].casefold() for profile in game_cfg["profiles"]}
        if clean.casefold() not in used:
            return clean

        idx = 2
        while True:
            candidate = f"{clean} ({idx})"
            if candidate.casefold() not in used:
                return candidate
            idx += 1

    def _resolve_path_safe(self, path: Path) -> Path:
        try:
            return path.resolve()
        except OSError:
            return path

    def _build_backup_path(self, path: Path) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        candidate = path.with_name(f"{path.name}_backup_{stamp}")
        idx = 2
        while candidate.exists() or candidate.is_symlink():
            candidate = path.with_name(f"{path.name}_backup_{stamp}_{idx}")
            idx += 1
        return candidate

    def _sync_game_mods_mount(self, game_id: str, game_cfg: dict) -> bool:
        changed = False
        game_mods_dir = self._default_mods_dirs[game_id]
        game_mods_dir.parent.mkdir(parents=True, exist_ok=True)

        active_path = self._active_profile_path(game_cfg)
        if active_path == game_mods_dir:
            active_path.mkdir(parents=True, exist_ok=True)
            return changed

        for idx, profile in enumerate(game_cfg["profiles"]):
            profile_path = Path(profile["path"])
            if profile_path != game_mods_dir:
                continue

            if game_mods_dir.is_symlink():
                detached_path = self._resolve_path_safe(game_mods_dir)
            else:
                detached_path = self._build_profile_path(game_id, game_cfg, profile["name"])
                if game_mods_dir.exists():
                    detached_path.parent.mkdir(parents=True, exist_ok=True)
                    game_mods_dir.rename(detached_path)
                else:
                    detached_path.mkdir(parents=True, exist_ok=True)

            game_cfg["profiles"][idx]["path"] = str(detached_path)
            changed = True

        active_path = self._active_profile_path(game_cfg)
        active_path.mkdir(parents=True, exist_ok=True)

        if game_mods_dir.is_symlink():
            current_target = self._resolve_path_safe(game_mods_dir)
            if current_target == self._resolve_path_safe(active_path):
                return changed
            game_mods_dir.unlink()
            changed = True
        elif game_mods_dir.exists():
            if game_mods_dir.is_dir():
                try:
                    has_entries = any(game_mods_dir.iterdir())
                except OSError:
                    has_entries = True
                if has_entries:
                    game_mods_dir.rename(self._build_backup_path(game_mods_dir))
                else:
                    game_mods_dir.rmdir()
            else:
                game_mods_dir.rename(self._build_backup_path(game_mods_dir))
            changed = True

        game_mods_dir.symlink_to(active_path, target_is_directory=True)
        return True

    def _sync_game_mods_links(self, cfg: dict) -> bool:
        changed = False
        for game_id, game_cfg in cfg["games"].items():
            if self._sync_game_mods_mount(game_id, game_cfg):
                changed = True

        if changed:
            self._sync_legacy_fields(cfg)
        return changed

    def _save_with_sync(self, cfg: dict):
        self._sync_game_mods_links(cfg)
        self._sync_legacy_fields(cfg)
        self._save(cfg)

    def list_games(self) -> list[tuple[str, str]]:
        return [
            (game_id, get_game_spec(game_id).label)
            for game_id in SUPPORTED_GAMES
        ]

    def get_active_game(self) -> str:
        cfg = self._load_normalized()
        return cfg["active_game"]

    def set_active_game(self, game_id: str):
        cfg = self._load_normalized()
        resolved_game_id = self._normalize_game_id(game_id)
        if resolved_game_id == cfg["active_game"]:
            return

        cfg["active_game"] = resolved_game_id
        self._save_with_sync(cfg)

    def get_default_mods_dir(self, game_id: str | None = None) -> Path:
        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        return self._default_mods_dirs[resolved_game_id]

    def get_mods_dir(self, game_id: str | None = None) -> Path:
        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        game_cfg = cfg["games"][resolved_game_id]
        return self._active_profile_path(game_cfg)

    def set_mods_dir(self, path: Path, game_id: str | None = None):
        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        game_cfg = cfg["games"][resolved_game_id]
        active_idx = self._find_profile_index(game_cfg, game_cfg["active_profile"])
        if active_idx is None:
            active_idx = 0
        game_cfg["profiles"][active_idx]["path"] = str(path)
        self._save_with_sync(cfg)

    def list_profiles(self, game_id: str | None = None) -> list[tuple[str, Path]]:
        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        game_cfg = cfg["games"][resolved_game_id]
        return [(profile["name"], Path(profile["path"])) for profile in game_cfg["profiles"]]

    def get_active_profile(self, game_id: str | None = None) -> str:
        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        return cfg["games"][resolved_game_id]["active_profile"]

    def set_active_profile(self, name: str, game_id: str | None = None):
        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        game_cfg = cfg["games"][resolved_game_id]
        profile_idx = self._find_profile_index(game_cfg, name)
        if profile_idx is None:
            raise ValueError("Perfil inexistente")

        game_cfg["active_profile"] = game_cfg["profiles"][profile_idx]["name"]
        self._save_with_sync(cfg)

    def create_profile(self, name: str, game_id: str | None = None) -> tuple[str, Path]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Nome de perfil vazio")

        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        game_cfg = cfg["games"][resolved_game_id]

        if self._find_profile_index(game_cfg, clean_name) is not None:
            raise ValueError("Perfil ja existe")

        profile_path = self._build_profile_path(resolved_game_id, game_cfg, clean_name)
        profile_path.mkdir(parents=True, exist_ok=True)
        game_cfg["profiles"].append({"name": clean_name, "path": str(profile_path)})
        game_cfg["active_profile"] = clean_name
        self._save_with_sync(cfg)
        return clean_name, profile_path

    def delete_profile(self, name: str, game_id: str | None = None):
        cfg = self._load_normalized()
        resolved_game_id = self._resolve_game_id(cfg, game_id)
        game_cfg = cfg["games"][resolved_game_id]
        profile_idx = self._find_profile_index(game_cfg, name)
        if profile_idx is None:
            raise ValueError("Perfil inexistente")

        if game_cfg["profiles"][profile_idx]["name"].casefold() == DEFAULT_PROFILE_NAME.casefold():
            raise ValueError("Nao e possivel remover o perfil padrao")

        if len(game_cfg["profiles"]) == 1:
            raise ValueError("Nao e possivel remover o ultimo perfil")

        removed = game_cfg["profiles"].pop(profile_idx)
        if removed["name"] == game_cfg["active_profile"]:
            game_cfg["active_profile"] = game_cfg["profiles"][0]["name"]
        self._save_with_sync(cfg)

    def export_active_profile_bundle(self, destination: Path) -> dict[str, str | int]:
        cfg = self._load_normalized()
        game_id = cfg["active_game"]
        game_cfg = cfg["games"][game_id]
        profile_name = game_cfg["active_profile"]
        profile_path = self._active_profile_path(game_cfg)

        if destination.suffix.lower() != ".zip":
            destination = destination.with_suffix(".zip")
        destination.parent.mkdir(parents=True, exist_ok=True)

        files_count = 0
        manifest = {
            "schema": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "game_id": game_id,
            "profile_name": profile_name,
        }

        with zipfile.ZipFile(destination, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            if profile_path.exists():
                for file_path in profile_path.rglob("*"):
                    if not file_path.is_file():
                        continue
                    rel = file_path.relative_to(profile_path)
                    archive.write(file_path, arcname=str(Path("mods") / rel))
                    files_count += 1

        return {
            "game_id": game_id,
            "profile_name": profile_name,
            "archive": str(destination),
            "files": files_count,
        }

    def import_profile_bundle(self, bundle_path: Path) -> dict[str, str | int]:
        cfg = self._load_normalized()

        with zipfile.ZipFile(bundle_path) as archive:
            manifest_raw = archive.read("manifest.json")
            manifest = json.loads(manifest_raw.decode("utf-8", errors="replace"))

            manifest_game = str(manifest.get("game_id", cfg["active_game"])).strip().lower()
            target_game = manifest_game if manifest_game in SUPPORTED_GAMES else cfg["active_game"]
            game_cfg = cfg["games"][target_game]

            base_name = str(manifest.get("profile_name", "Perfil Importado")).strip() or "Perfil Importado"
            profile_name = self._build_unique_profile_name(game_cfg, base_name)
            profile_path = self._build_profile_path(target_game, game_cfg, profile_name)
            profile_path.mkdir(parents=True, exist_ok=True)

            imported_files = 0
            try:
                for member in archive.infolist():
                    if member.is_dir() or not member.filename.startswith("mods/"):
                        continue

                    rel = Path(member.filename).relative_to("mods")
                    if any(part in {"", ".", ".."} for part in rel.parts):
                        continue

                    target = (profile_path / rel).resolve()
                    if not str(target).startswith(str(profile_path.resolve())):
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member, mode="r") as source, target.open("wb") as dest:
                        dest.write(source.read())
                    imported_files += 1
            except Exception:
                for child in profile_path.rglob("*"):
                    if child.is_file():
                        child.unlink(missing_ok=True)
                for child in sorted(profile_path.rglob("*"), reverse=True):
                    if child.is_dir():
                        child.rmdir()
                profile_path.rmdir()
                raise

        game_cfg["profiles"].append({"name": profile_name, "path": str(profile_path)})
        game_cfg["active_profile"] = profile_name
        cfg["active_game"] = target_game
        self._save_with_sync(cfg)

        return {
            "game_id": target_game,
            "profile_name": profile_name,
            "mods_dir": str(profile_path),
            "files": imported_files,
        }

    def get_language(self) -> str:
        cfg = self._load()
        return cfg.get("language", "pt_BR")

    def set_language(self, lang: str):
        cfg = self._load()
        cfg["language"] = lang
        self._save(cfg)

    def get_confirm_delete(self) -> bool:
        cfg = self._load()
        return cfg.get("confirm_delete", True)

    def set_confirm_delete(self, value: bool):
        cfg = self._load()
        cfg["confirm_delete"] = value
        self._save(cfg)
