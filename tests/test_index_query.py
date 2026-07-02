from pathlib import Path
import sqlite3

from ntc_code_map.config import create_default_config
from ntc_code_map.indexer import index_repo, index_status
from ntc_code_map.query import find_symbols_text, module_map_text, repo_map_text


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-repo"
    repo.mkdir()

    create_default_config(repo / ".ntc-code-map.toml", name="sample-repo")

    src = repo / "src"
    src.mkdir()

    (src / "app.py").write_text(
        '''
class UserService:
    def create_user(self, name: str) -> dict:
        return {"name": name}

def main() -> None:
    service = UserService()
    service.create_user("bao")
'''.strip()
        + "\n",
        encoding="utf-8",
    )

    (src / "config.py").write_text(
        '''
def load_settings() -> dict:
    return {"debug": True}
'''.strip()
        + "\n",
        encoding="utf-8",
    )

    ignored = repo / ".venv"
    ignored.mkdir()
    (ignored / "ignored.py").write_text("def should_not_index(): pass\n", encoding="utf-8")

    return repo


def test_index_repo_and_status(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)

    result = index_repo(repo)

    assert result["indexed_files"] >= 3
    assert result["symbols"] > 0
    assert result["symbol_source"] in {"ctags-json", "fallback-regex"}

    status = index_status(repo)

    assert status["indexed"] is True
    assert status["files"] >= 3
    assert status["symbols"] > 0


def test_ignored_dirs_are_not_indexed(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    index_repo(repo)

    conn = sqlite3.connect(repo / ".ntc-code-map" / "index.db")
    rows = conn.execute("SELECT path FROM files WHERE path LIKE '.venv/%'").fetchall()
    conn.close()

    assert rows == []


def test_find_symbols_and_maps(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    index_repo(repo)

    symbols = find_symbols_text("UserService", repo)
    assert "UserService" in symbols
    assert "src/app.py" in symbols

    module_map = module_map_text("src", repo, token_budget=800)
    assert "src/app.py" in module_map
    assert "UserService" in module_map

    repo_map = repo_map_text("How user creation flow starts", repo, token_budget=800)
    assert "# NTC Code Map" in repo_map
    assert "src/app.py" in repo_map
