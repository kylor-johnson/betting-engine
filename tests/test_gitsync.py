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
    monkeypatch.setattr(config, "DATA", tmp_path / "data.nosync")
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


def test_skips_while_a_session_holds_the_lock(tmp_path, monkeypatch):
    from engine import session_lock
    _repo(tmp_path, monkeypatch)
    (tmp_path / "docs" / "cards" / "c.md").write_text("card\n")
    assert session_lock.take("test session").startswith("Lock taken")
    assert session_lock.take("second session").startswith("REFUSED")
    assert gitsync.commit_generated().startswith("Auto-commit skipped: a session holds")
    session_lock.release()
    assert "scheduled-run outputs committed" in gitsync.commit_generated()


def test_a_stale_lock_does_not_block(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from engine import session_lock
    _repo(tmp_path, monkeypatch)
    session_lock.take("old", now=datetime.now(timezone.utc) - timedelta(hours=session_lock.STALE_HOURS + 1))
    assert session_lock.held() is None
    assert session_lock.take("new").startswith("Lock taken")
