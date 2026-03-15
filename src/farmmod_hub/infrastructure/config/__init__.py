from .json_store import JsonSettingsStore

_DEFAULT_SETTINGS_STORE = JsonSettingsStore()


def get_settings_store() -> JsonSettingsStore:
    return _DEFAULT_SETTINGS_STORE


__all__ = ["JsonSettingsStore", "get_settings_store"]
