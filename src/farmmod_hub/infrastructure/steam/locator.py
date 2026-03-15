"""Deteccao automatica dos diretorios de mods via Steam/Proton."""

from dataclasses import dataclass
import re
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GameSpec:
    id: str
    label: str
    steam_app_id: str
    docs_folder: str


SUPPORTED_GAMES: dict[str, GameSpec] = {
    "fs19": GameSpec(
        id="fs19",
        label="Farming Simulator 19",
        steam_app_id="787860",
        docs_folder="FarmingSimulator2019",
    ),
    "fs22": GameSpec(
        id="fs22",
        label="Farming Simulator 22",
        steam_app_id="1248130",
        docs_folder="FarmingSimulator2022",
    ),
    "fs25": GameSpec(
        id="fs25",
        label="Farming Simulator 25",
        steam_app_id="2300320",
        docs_folder="FarmingSimulator2025",
    ),
}

STEAM_CANDIDATES = [
    Path.home() / ".local/share/Steam",
    Path.home() / ".steam/steam",
    Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
]


def _parse_library_paths(vdf_path: Path) -> list[Path]:
    try:
        text = vdf_path.read_text(errors="replace")
        return [Path(m) for m in re.findall(r'"path"\s+"([^"]+)"', text)]
    except OSError:
        return []


def _steam_libraries(steam_base: Path) -> list[Path]:
    vdf = steam_base / "steamapps/libraryfolders.vdf"
    paths = _parse_library_paths(vdf)
    if steam_base not in paths:
        paths.insert(0, steam_base)
    return paths


def get_game_spec(game_id: str) -> GameSpec:
    key = game_id.strip().lower()
    if key not in SUPPORTED_GAMES:
        raise ValueError("Jogo não suportado")
    return SUPPORTED_GAMES[key]


def mods_subpath_for_game(game_id: str) -> str:
    game = get_game_spec(game_id)
    return (
        "steamapps/compatdata/"
        + game.steam_app_id
        + "/pfx/drive_c/users/steamuser/Documents/My Games/"
        + game.docs_folder
        + "/mods"
    )


def fallback_mods_dir(game_id: str) -> Path:
    return STEAM_CANDIDATES[0] / mods_subpath_for_game(game_id)


def find_mods_dir(game_id: str = "fs19") -> Path:
    subpath = mods_subpath_for_game(game_id)
    seen: set[Path] = set()

    for candidate in STEAM_CANDIDATES:
        if not candidate.exists():
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)

        for lib in _steam_libraries(candidate):
            mods_dir = lib / subpath
            if mods_dir.exists():
                return mods_dir

    return fallback_mods_dir(game_id)
