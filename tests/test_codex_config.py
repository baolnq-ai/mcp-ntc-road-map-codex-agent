from pathlib import Path

from ntc_code_map.codex_config import upsert_mcp_block


def test_upsert_codex_config_adds_single_block(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    command = tmp_path / "bin" / "ntc-code-map"

    result = upsert_mcp_block(
        config_path=config,
        command=str(command),
        dry_run=False,
    )

    assert result["changed"] is True
    assert result["action"] == "added"
    assert config.exists()

    text = config.read_text(encoding="utf-8")
    assert text.count("[mcp_servers.ntc_code_map]") == 1
    assert 'args = ["serve"]' in text

    result2 = upsert_mcp_block(
        config_path=config,
        command=str(command),
        dry_run=False,
    )

    assert result2["changed"] is False
    assert config.read_text(encoding="utf-8").count("[mcp_servers.ntc_code_map]") == 1
