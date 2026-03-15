from .filesystem_repository import FilesystemModsRepository
from farmmod_hub.infrastructure.config import get_settings_store

_DEFAULT_MODS_REPOSITORY = FilesystemModsRepository(get_settings_store())


def get_mods_repository() -> FilesystemModsRepository:
    return _DEFAULT_MODS_REPOSITORY


__all__ = ["FilesystemModsRepository", "get_mods_repository"]
