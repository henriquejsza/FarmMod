from dataclasses import dataclass, field
from datetime import datetime
import re
from pathlib import Path


@dataclass(slots=True)
class ModLogSummary:
    mod_name: str
    errors: int = 0
    warnings: int = 0
    categories: dict[str, int] = field(default_factory=dict)
    sample_lines: list[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        return self.errors * 3 + self.warnings


@dataclass(slots=True)
class LogAnalysisReport:
    path: Path
    total_errors: int
    total_warnings: int
    mod_summaries: list[ModLogSummary]
    generic_issues: list[str]


def format_log_report_text(
    report: LogAnalysisReport,
    game_id: str,
    game_label: str,
    generated_at: datetime | None = None,
) -> str:
    timestamp = (generated_at or datetime.now()).isoformat(timespec="seconds")

    lines = [
        f"Diagnostico de Mods - {game_label} ({game_id.upper()})",
        f"Gerado em: {timestamp}",
        f"Arquivo: {report.path}",
        f"Total: {report.total_errors} erros | {report.total_warnings} avisos",
        "",
        "Mods suspeitos:",
    ]

    if report.mod_summaries:
        for index, summary in enumerate(report.mod_summaries[:20], start=1):
            lines.append(
                f"{index}. {summary.mod_name} | erros:{summary.errors} avisos:{summary.warnings} score:{summary.score}"
            )
            if summary.categories:
                categories = ", ".join(
                    f"{name}:{count}" for name, count in sorted(summary.categories.items())
                )
                lines.append(f"   categorias: {categories}")
            for sample in summary.sample_lines[:2]:
                lines.append(f"   - {sample}")
    else:
        lines.append("(nenhum mod suspeito)")

    lines.append("")
    lines.append("Problemas gerais:")
    if report.generic_issues:
        for issue in report.generic_issues:
            lines.append(f"- {issue}")
    else:
        lines.append("(sem problemas gerais relevantes)")

    return "\n".join(lines)


def export_log_report_text(
    report: LogAnalysisReport,
    destination: Path,
    game_id: str,
    game_label: str,
) -> Path:
    output = destination.with_suffix(".txt") if destination.suffix.lower() != ".txt" else destination
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(format_log_report_text(report, game_id, game_label), encoding="utf-8")
    return output


def analyze_log_file(log_path: Path) -> LogAnalysisReport:
    lines = log_path.read_text(errors="replace").splitlines()

    by_mod: dict[str, ModLogSummary] = {}
    generic_issues: list[str] = []
    total_errors = 0
    total_warnings = 0

    for raw_line in lines:
        level = _extract_level(raw_line)
        if level is None:
            continue

        if level == "error":
            total_errors += 1
        else:
            total_warnings += 1

        category = _categorize_issue(raw_line)
        mod_name = _extract_mod_name(raw_line)
        normalized_line = raw_line.strip()

        if mod_name is None:
            generic_issues.append(normalized_line)
            continue

        summary = by_mod.get(mod_name)
        if summary is None:
            summary = ModLogSummary(mod_name=mod_name)
            by_mod[mod_name] = summary

        if level == "error":
            summary.errors += 1
        else:
            summary.warnings += 1

        summary.categories[category] = summary.categories.get(category, 0) + 1
        if len(summary.sample_lines) < 3:
            summary.sample_lines.append(normalized_line)

    sorted_summaries = sorted(
        by_mod.values(),
        key=lambda item: (-item.score, -item.errors, item.mod_name.casefold()),
    )

    return LogAnalysisReport(
        path=log_path,
        total_errors=total_errors,
        total_warnings=total_warnings,
        mod_summaries=sorted_summaries,
        generic_issues=generic_issues[:12],
    )


def _extract_level(line: str) -> str | None:
    lower = line.lower()
    if "error:" in lower:
        return "error"
    if "warning:" in lower or "warning (" in lower:
        return "warning"
    return None


def _extract_mod_name(line: str) -> str | None:
    patterns = [
        r"in mod\s+([A-Za-z0-9_\-\.]+)",
        r"mod\s+'([^']+)'",
        r"mod\s+\"([^\"]+)\"",
        r"/mods/([^/\\']+)",
        r"\\mods\\([^/\\']+)",
        r"vehicle type\s+'([^']+)'",
    ]

    for pattern in patterns:
        match = re.search(pattern, line, flags=re.IGNORECASE)
        if match is None:
            continue

        token = match.group(1)
        if token.endswith(".zip"):
            token = token[:-4]
        if "." in token and pattern.endswith("vehicle type\\s+'([^']+)'"):
            token = token.split(".", 1)[0]

        token = token.strip()
        if token:
            return token

    return None


def _categorize_issue(line: str) -> str:
    lower = line.lower()

    rules = [
        ("unsupported_desc", "unsupported mod description version"),
        ("invalid_name", "invalid mod name"),
        ("xml_open_failed", "failed to open xml file"),
        ("missing_moddesc", "moddesc.xml"),
        ("missing_l10n", "missing l10n"),
        ("specialization_conflict", "specialization"),
        ("lua_runtime", "warning (script)"),
    ]

    for code, needle in rules:
        if needle in lower:
            return code

    return "other"
