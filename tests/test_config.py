from pathlib import Path

from ntc_code_map.config import create_default_config, load_config


def test_load_config_from_nested_directory(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    repo.mkdir()

    (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    create_default_config(repo / ".ntc-code-map.toml", name="demo")

    nested = repo / "src" / "pkg"
    nested.mkdir(parents=True)

    cfg = load_config(nested)

    assert cfg.root == repo.resolve()
    assert cfg.name == "demo"
    assert ".py" in cfg.include_exts
    assert ".git" in cfg.ignore_dirs
    assert cfg.config_file == repo / ".ntc-code-map.toml"
