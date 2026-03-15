from datetime import datetime

from farmmod_hub.infrastructure.logs import (
    analyze_log_file,
    export_log_report_text,
    format_log_report_text,
)


def test_analyzer_groups_issues_by_mod(tmp_path):
    log_path = tmp_path / "log.txt"
    log_path.write_text(
        "\n".join(
            [
                "2024-03-12 Error: Unsupported mod description version in mod FS19_impala67",
                "2024-03-12 Error: Invalid mod name 'FS22_BigDisplay (1)'!",
                "2024-03-12 Warning: Missing l10n 'input_IC_SPACE' in mod 'FS22_BetterContracts'",
                "2024-03-12 Error: Specialization 'x' already exists for vehicle type 'FS22_BetterContracts.vehicle'!",
                "2024-03-12 Warning: Performance warning outside mod context",
            ]
        )
    )

    report = analyze_log_file(log_path)

    assert report.total_errors == 3
    assert report.total_warnings == 2
    assert report.mod_summaries[0].mod_name == "FS22_BetterContracts"
    assert report.mod_summaries[0].errors == 1
    assert report.mod_summaries[0].warnings == 1
    assert any(item.mod_name == "FS19_impala67" for item in report.mod_summaries)
    assert any("Performance warning" in line for line in report.generic_issues)


def test_analyzer_extracts_mod_from_mods_path(tmp_path):
    log_path = tmp_path / "log.txt"
    log_path.write_text(
        "Error: Failed to open xml file 'C:/Users/test/Documents/My Games/FarmingSimulator2022/mods/FS22_MyPack/modDesc.xml'"
    )

    report = analyze_log_file(log_path)

    assert report.total_errors == 1
    assert report.mod_summaries[0].mod_name == "FS22_MyPack"
    assert report.mod_summaries[0].categories["xml_open_failed"] == 1


def test_format_and_export_log_report_text(tmp_path):
    log_path = tmp_path / "log.txt"
    log_path.write_text("Error: Unsupported mod description version in mod FS19_Test")
    report = analyze_log_file(log_path)

    text = format_log_report_text(
        report,
        game_id="fs19",
        game_label="Farming Simulator 19",
        generated_at=datetime(2026, 1, 2, 3, 4, 5),
    )

    assert "Farming Simulator 19 (FS19)" in text
    assert "Gerado em: 2026-01-02T03:04:05" in text
    assert "FS19_Test" in text

    written = export_log_report_text(
        report,
        destination=tmp_path / "diag",
        game_id="fs19",
        game_label="Farming Simulator 19",
    )

    assert written.suffix == ".txt"
    assert written.exists()
    assert "Diagnostico de Mods" in written.read_text()
