from dataclasses import dataclass, field
from pathlib import Path

MOD_DESC_XML = "modDesc.xml"


def is_supported_mod_path(path: Path) -> bool:
    return path.suffix.lower() == ".zip" or path.is_dir()


@dataclass(slots=True)
class InstallReport:
    installed: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_tuple(self) -> tuple[list[str], list[str], list[str]]:
        return self.installed, self.updated, self.errors

    def as_detailed_tuple(
        self,
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        return self.installed, self.updated, self.errors, self.warnings
