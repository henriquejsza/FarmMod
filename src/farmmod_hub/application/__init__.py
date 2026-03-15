from .mods_service import ModsService
from farmmod_hub.infrastructure.mods import get_mods_repository

_DEFAULT_MODS_SERVICE = ModsService(get_mods_repository())


def get_mods_service() -> ModsService:
    return _DEFAULT_MODS_SERVICE


__all__ = ["ModsService", "get_mods_service"]
