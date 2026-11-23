import subprocess

from engine import config, gitsync


def _repo(tmp_path, monkeypatch):
    run = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    run("init", "-q")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    (tmp_path / "docs" / "cards").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n")
    (tmp_path / "config.yaml").write_text("timezone_display: America/Denver\n")
    run("add", "-A")
    run("commit", "-qm", "init")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return run


def test_commits_only_generated_paths_and_leaves_a_persons_edit_alone(tmp_path, monkeypatch):
    run = _repo(tmp_path, monkeypatch)
    (tmp_path / "docs" / "cards" / "c.md").write_text("card\n")
    (tmp_path / "src" / "a.py").write_text("x=2\n")          # a person's unfinished edit
    assert "committed" in gitsync.commit_generated("NFL")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=tmp_path, capture_output=True, text=True).stdout
    assert " M src/a.py" in status and "cards" not in status
    assert "nothing new" in gitsync.commit_generated()


def test_skips_while_git_is_busy(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    (tmp_path / ".git" / "index.lock").write_text("")
    assert "skipped" in gitsync.commit_generated()
