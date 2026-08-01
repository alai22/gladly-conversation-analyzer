"""Unit tests for labeling data parsers and analyzer."""

from pathlib import Path

import pytest

from backend.services.labeling_data_analyzer import (
    LabelingDataAnalyzer,
    canonicalize_activity_label,
    format_ui_summary,
    parse_collar_collected,
    parse_duration_to_seconds,
    parse_durations,
    parse_filename,
    parse_rel_path,
    parse_user_reported,
    sanitize_collar_sn,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "labeling"
TREE = Path(__file__).resolve().parents[1] / "fixtures" / "labeling_tree"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestParsers:
    def test_parse_filename(self):
        parsed = parse_filename(
            "activity_session_2026-04-21T18:38:31_0_collar_collected.txt"
        )
        assert parsed == {
            "timestamp": "2026-04-21T18:38:31",
            "index": 0,
            "kind": "collar_collected",
        }
        assert parse_filename("random.txt") is None

    def test_parse_rel_path_nested_and_legacy(self):
        nested = parse_rel_path(
            "laura@x.com/24h4290312rt/activity_session_2026-04-21T18:38:31_0_durations.txt"
        )
        assert nested["user"] == "laura@x.com"
        assert nested["collar_sn"] == "24h4290312rt"
        assert nested["kind"] == "durations"

        legacy = parse_rel_path(
            "laura@x.com/activity_session_2026-04-21T18:38:31_0_durations.txt"
        )
        assert legacy["user"] == "laura@x.com"
        assert legacy["collar_sn"] is None
        assert sanitize_collar_sn(" 24h4290312rt ") == "24h4290312rt"

    def test_parse_duration_to_seconds(self):
        assert parse_duration_to_seconds("00:00:00") == 0.0
        assert parse_duration_to_seconds("00:00:01.5000000") == pytest.approx(1.5)
        assert parse_duration_to_seconds("00:01:24.2000000") == pytest.approx(84.2)

    def test_canonicalize_activity_label(self):
        assert canonicalize_activity_label("Standing (10)") == "Standing"
        assert canonicalize_activity_label("Standing") == "Standing"
        assert canonicalize_activity_label("RunningPlaying (4)") == "RunningPlaying"
        assert canonicalize_activity_label("  Sedentary  ") == "Sedentary"

    def test_parse_collar_collected(self):
        text = _read("activity_session_2026-04-21T18:38:31_0_collar_collected.txt")
        parsed = parse_collar_collected(text)
        assert parsed.dog_name == "Diamond"
        assert parsed.dog_breed == "Mixed"
        assert parsed.collar_sn == "24h4290312rt"
        assert parsed.session_started is True
        assert parsed.session_ended is True
        labels = [e["label"] for e in parsed.activity_events]
        assert labels == ["OnShelf (12)", "Standing (10)", "OnShelf (12)"]
        assert parsed.activity_events[0]["note"] == "initial state"

    def test_parse_durations(self):
        text = _read("activity_session_2026-04-21T18:38:31_0_durations.txt")
        durations = parse_durations(text)
        assert durations["Standing (10)"] == pytest.approx(1.5)
        assert durations["OnShelf (12)"] == 0.0

    def test_parse_user_reported(self):
        text = _read("activity_session_2026-04-21T18:38:31_0_user_reported.txt")
        parsed = parse_user_reported(text)
        assert len(parsed.events) == 2
        assert parsed.events[0]["label"] == "Standing (10)"
        assert parsed.events[0]["event"] == "touch start"
        assert parsed.events[1]["event"] == "touch end"


class TestLocalAnalyze:
    def test_analyze_local_tree(self):
        assert TREE.exists(), f"missing fixture tree {TREE}"
        analyzer = LabelingDataAnalyzer(bucket_name="local", prefix="extracted-txt/")
        summary = analyzer.analyze_local(str(TREE))
        assert summary["total_users"] >= 1
        assert summary["total_files"] >= 3
        assert summary["files_by_kind"]["collar_collected"] >= 1
        assert summary["files_by_kind"]["durations"] >= 1
        assert "Standing" in summary["activity_duration_seconds"]
        assert "Standing (10)" not in summary["activity_duration_seconds"]
        assert summary["activity_duration_seconds"]["Standing"] > 0
        assert summary["collar_activity_events"].get("Standing", 0) >= 1
        assert summary["user_reported_events"].get("Standing", 0) >= 1
        assert summary["by_date"]
        assert summary["by_date"][0]["date"] == "2026-04-21"
        assert summary["by_date"][0]["duration_seconds"] > 0
        assert summary["by_date"][0]["sessions"] >= 1

    def test_format_ui_summary(self):
        analyzer = LabelingDataAnalyzer(bucket_name="local", prefix="extracted-txt/")
        ui = format_ui_summary(analyzer.analyze_local(str(TREE)))
        assert ui["totals"]["users"] >= 1
        assert ui["totals"]["duration_seconds"] > 0
        assert any(a["name"] == "Standing" and a["label"] == "Standing" for a in ui["activities"])
        assert ui["by_date"]
        assert ui["by_date"][0]["date"] == "2026-04-21"
        assert ui["users"][0]["email"]
        assert ui["users"][0]["total_duration_seconds"] > 0
        assert ui["users"][0]["collar_sns"]
        assert ui["users"][0]["collars"]
        assert ui["users"][0]["collars"][0]["collar_sn"] == "24h4290312rt"

    def test_merges_bare_and_id_duration_labels(self, tmp_path: Path):
        user_dir = tmp_path / "labeler@x.com" / "collar1"
        user_dir.mkdir(parents=True)
        (user_dir / "activity_session_2026-04-21T18:38:31_0_durations.txt").write_text(
            '{\n  "Standing (10)": "00:00:10.0000000",\n  "Walking (1)": "00:00:05.0000000"\n}\n',
            encoding="utf-8",
        )
        (user_dir / "activity_session_2026-04-21T18:39:26_2_durations.txt").write_text(
            '{\n  "Standing": "00:00:03.0000000",\n  "Walking": "00:00:02.0000000"\n}\n',
            encoding="utf-8",
        )
        analyzer = LabelingDataAnalyzer(bucket_name="local", prefix="extracted-txt/")
        summary = analyzer.analyze_local(str(tmp_path))
        assert summary["activity_duration_seconds"]["Standing"] == pytest.approx(13.0)
        assert summary["activity_duration_seconds"]["Walking"] == pytest.approx(7.0)
        assert len(summary["activity_duration_seconds"]) == 2
