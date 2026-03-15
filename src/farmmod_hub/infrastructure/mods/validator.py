from dataclasses import dataclass, field
import re
import zipfile
from pathlib import Path

from farmmod_hub.domain import MOD_DESC_XML


class BatchValidationState:
    def __init__(
        self,
        kind_by_mod_id: dict[str, set[str]],
        count_by_name: dict[str, int],
        active_game: str,
    ):
        self.kind_by_mod_id = kind_by_mod_id
        self.count_by_name = count_by_name
        self.active_game = active_game


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _mod_kind(path: Path) -> str:
    if path.suffix.lower() == ".zip":
        return "zip"
    if path.is_dir():
        return "folder"
    return "other"


def _mod_id(path: Path) -> str:
    return path.stem if path.suffix.lower() == ".zip" else path.name


def build_batch_validation_state(paths: list[Path], active_game: str) -> BatchValidationState:
    kind_by_mod_id: dict[str, set[str]] = {}
    count_by_name: dict[str, int] = {}

    for src in paths:
        mod_id = _mod_id(src)
        kind_by_mod_id.setdefault(mod_id.casefold(), set()).add(_mod_kind(src))
        key = src.name.casefold()
        count_by_name[key] = count_by_name.get(key, 0) + 1

    return BatchValidationState(kind_by_mod_id, count_by_name, active_game)


def validate_source(src: Path, mods_dir: Path, state: BatchValidationState) -> ValidationResult:
    result = ValidationResult()
    kind = _mod_kind(src)

    if kind == "other":
        result.errors.append("formato não suportado (use .zip ou pasta)")
        return result

    name_game_hint = _guess_game_from_name(src.name)
    if name_game_hint and name_game_hint != state.active_game:
        result.warnings.append(
            f"nome indica mod de {name_game_hint.upper()}, mas o perfil ativo e {state.active_game.upper()}"
        )

    if state.count_by_name.get(src.name.casefold(), 0) > 1:
        result.errors.append("item duplicado na seleção")

    mod_id = _mod_id(src)
    kinds = state.kind_by_mod_id.get(mod_id.casefold(), set())
    if "zip" in kinds and "folder" in kinds:
        result.errors.append("há ZIP e pasta do mesmo mod na seleção")

    counterpart = mods_dir / (mod_id if kind == "zip" else f"{mod_id}.zip")
    if counterpart.exists():
        result.errors.append("já existe versão ZIP/pasta do mesmo mod instalada")

    if kind == "zip":
        result.errors.extend(_validate_zip(src))
    else:
        result.errors.extend(_validate_folder(src))

    if not result.errors:
        desc_version = _extract_desc_version(src, kind)
        version_game_hint = _guess_game_from_desc_version(desc_version)
        if version_game_hint and version_game_hint != state.active_game:
            result.warnings.append(
                "descVersion "
                + str(desc_version)
                + f" indica {version_game_hint.upper()}, mas o perfil ativo e {state.active_game.upper()}"
            )

    return result


def _validate_zip(src: Path) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(src) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile:
        return ["arquivo ZIP corrompido"]
    except OSError as exc:
        return [f"falha ao abrir ZIP: {exc}"]

    mod_desc_entries = [name for name in names if Path(name).name == MOD_DESC_XML]
    if not mod_desc_entries:
        errors.append(f"sem {MOD_DESC_XML}")
        return errors

    root_entries = [name for name in mod_desc_entries if Path(name).as_posix() == MOD_DESC_XML]
    if not root_entries:
        errors.append(f"{MOD_DESC_XML} não está na raiz do ZIP")
        return errors

    top_level_holders: set[str] = set()
    for entry in mod_desc_entries:
        parts = Path(entry).parts
        top_level_holders.add(parts[0] if len(parts) > 1 else "")

    non_root_holders = {holder for holder in top_level_holders if holder}
    if len(non_root_holders) > 1:
        errors.append("parece modpack com múltiplos mods no mesmo ZIP")

    return errors


def _validate_folder(src: Path) -> list[str]:
    errors: list[str] = []
    if (src / MOD_DESC_XML).exists():
        return errors

    nested = list(src.glob(f"*/{MOD_DESC_XML}"))
    if nested:
        errors.append(f"{MOD_DESC_XML} está em subpasta (extraia a pasta correta)")
    else:
        errors.append(f"sem {MOD_DESC_XML}")

    return errors


def _guess_game_from_name(name: str) -> str | None:
    match = re.search(r"FS(19|22|25)", name.upper())
    if match is None:
        return None
    return f"fs{match.group(1)}"


def _extract_desc_version(src: Path, kind: str) -> int | None:
    if kind == "zip":
        try:
            with zipfile.ZipFile(src) as zf:
                xml_bytes = zf.read(MOD_DESC_XML)
        except Exception:
            return None
    else:
        xml_path = src / MOD_DESC_XML
        try:
            xml_bytes = xml_path.read_bytes()
        except OSError:
            return None

    match = re.search(rb'<modDesc\s+descVersion="(\d+)"', xml_bytes)
    if match is None:
        return None
    return int(match.group(1))


def _guess_game_from_desc_version(desc_version: int | None) -> str | None:
    if desc_version is None:
        return None
    if desc_version < 60:
        return "fs19"
    if desc_version < 90:
        return "fs22"
    return "fs25"
