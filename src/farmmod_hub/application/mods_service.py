from pathlib import Path
from typing import Protocol

from farmmod_hub.domain import InstallReport


class ModsRepository(Protocol):
    def install(self, paths: list[Path]) -> InstallReport:
        ...

    def count_installed(self) -> int:
        ...

    def list_installed(self) -> list[Path]:
        ...

    def remove(self, mod_path: Path):
        ...


class ModsService:
    def __init__(self, repository: ModsRepository):
        self._repository = repository

    def install(
        self,
        paths: list[Path],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        return self._repository.install(paths).as_detailed_tuple()

    def count_installed(self) -> int:
        return self._repository.count_installed()

    def list_installed(self) -> list[Path]:
        return self._repository.list_installed()

    def remove(self, mod_path: Path):
        self._repository.remove(mod_path)
