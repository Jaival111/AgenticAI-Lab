from pathlib import Path

from aaj.devagent import parse_action
from aaj.judges import parse_paths, parse_verdict
from aaj.workspace import resolve_workspace_path


def test_parse_verdict():
    assert parse_verdict("<SATISFIED> the file exists") is True
    assert parse_verdict("Verdict: <UNSATISFIED> missing") is False
    assert parse_verdict("< unsatisfied >") is False
    assert parse_verdict("I think it is fine") is None


def test_parse_paths_dedup_and_limit():
    t = "$/workspace/src/a.py$\n$/workspace/src/a.py$\n$/workspace/b.txt$"
    assert parse_paths(t, 5) == ["/workspace/src/a.py", "/workspace/b.txt"]
    assert parse_paths(t, 1) == ["/workspace/src/a.py"]


def test_resolve_workspace_path(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("x = 1")
    assert resolve_workspace_path(tmp_path, "/workspace/src/m.py") == (tmp_path / "src" / "m.py").resolve()
    assert resolve_workspace_path(tmp_path, "/project/src/m.py") is not None
    assert resolve_workspace_path(tmp_path, "../../etc/passwd") is None
    assert resolve_workspace_path(tmp_path, "/workspace/missing.py") is None


def test_parse_action():
    kind, header, body = parse_action("thought\n```write path=src/x.py\nprint(1)\n```")
    assert kind == "write" and "src/x.py" in header and body == "print(1)\n"
    assert parse_action("no block here") is None
