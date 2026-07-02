from pathlib import Path

from ntc_code_map.agents import MARKER_END, MARKER_START, init_agents


def test_init_agents_creates_agents_file(tmp_path: Path) -> None:
    result = init_agents(tmp_path)

    assert result["changed"] is True
    assert result["action"] == "created"

    agents = tmp_path / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")

    assert MARKER_START in text
    assert MARKER_END in text
    assert "ntc_code_map.repo_map" in text
    assert "Serena" in text


def test_init_agents_is_idempotent(tmp_path: Path) -> None:
    first = init_agents(tmp_path)
    second = init_agents(tmp_path)

    assert first["changed"] is True
    assert second["changed"] is False
    assert second["action"] == "unchanged"

    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert text.count(MARKER_START) == 1
    assert text.count(MARKER_END) == 1


def test_init_agents_appends_to_existing_file(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Existing Rules\n\nKeep this line.\n", encoding="utf-8")

    result = init_agents(tmp_path)

    assert result["changed"] is True
    assert result["action"] == "appended"

    text = agents.read_text(encoding="utf-8")
    assert "Keep this line." in text
    assert MARKER_START in text
    assert MARKER_END in text
