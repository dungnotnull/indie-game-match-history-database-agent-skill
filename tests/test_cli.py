"""Tests for the ``imh`` CLI."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from indie_match_history.cli import main
from indie_match_history.replay import ReplayConfig


def _run(args, db: Path, replay_root: Path | None = None) -> tuple[int, str, str]:
    base = ["--db", str(db)]
    if replay_root:
        base += ["--replay-root", str(replay_root)]
    import io, contextlib
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(base + args)
    return code, out.getvalue(), err.getvalue()


def test_cli_player_match_leaderboard(tmp_path: Path):
    db = tmp_path / "cli.db"
    code, out, _ = _run(["player-add", "--handle", "alice"], db)
    assert code == 0
    alice = json.loads(out)["player_id"]

    code, out, _ = _run(["player-add", "--handle", "bob"], db)
    bob = json.loads(out)["player_id"]

    spec = {
        "game_id": "pong", "season": "s1", "mode": "ranked",
        "results": [
            {"player_id": alice, "outcome": "win"},
            {"player_id": bob, "outcome": "loss"},
        ],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    code, out, _ = _run(["match-add", "--spec", str(spec_path)], db)
    assert code == 0
    payload = json.loads(out)
    assert payload["match_id"].startswith("mt_")
    assert payload["rating_deltas"][alice][1] > payload["rating_deltas"][alice][0]

    code, out, _ = _run(["leaderboard", "--game-id", "pong", "--season", "s1", "--top", "5"], db)
    lb = json.loads(out)
    assert lb[0]["player_id"] == alice

    code, out, _ = _run(["rating", "--player-id", alice], db)
    assert json.loads(out)["value"] > 1200

    code, out, _ = _run(["history", "--player-id", alice], db)
    assert len(json.loads(out)) == 1

    code, out, _ = _run(["stats"], db)
    assert json.loads(out)["matches"] == 1


def test_cli_replay_attach(tmp_path: Path):
    db = tmp_path / "cli.db"
    rp = tmp_path / "rp"
    _, out, _ = _run(["player-add", "--handle", "alice"], db)
    alice = json.loads(out)["player_id"]
    _, out, _ = _run(["player-add", "--handle", "bob"], db)
    bob = json.loads(out)["player_id"]
    spec = {"game_id": "pong", "season": "s1",
            "results": [{"player_id": alice, "outcome": "win"},
                        {"player_id": bob, "outcome": "loss"}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    _, out, _ = _run(["match-add", "--spec", str(spec_path)], db)
    match_id = json.loads(out)["match_id"]
    blob = ReplayConfig().magic + b"replay" * 200
    blob_path = tmp_path / "replay.bin"
    blob_path.write_bytes(blob)
    code, out, _ = _run(["replay-attach", "--match-id", match_id, "--file", str(blob_path)],
                       db, replay_root=rp)
    assert code == 0
    assert json.loads(out)["size_bytes"] == len(blob)


def test_cli_erase(tmp_path: Path):
    db = tmp_path / "cli.db"
    _, out, _ = _run(["player-add", "--handle", "alice"], db)
    alice = json.loads(out)["player_id"]
    _, out, _ = _run(["player-add", "--handle", "bob"], db)
    bob = json.loads(out)["player_id"]
    spec = {"game_id": "pong", "season": "s1",
            "results": [{"player_id": alice, "outcome": "win"},
                        {"player_id": bob, "outcome": "loss"}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    _run(["match-add", "--spec", str(spec_path)], db)
    code, out, _ = _run(["erase", "--player-id", alice], db)
    assert code == 0
    assert json.loads(out)["players"] == 1
    # alice is gone now; rating should error
    code, _, _ = _run(["rating", "--player-id", alice], db)
    assert code == 2


def test_cli_retention(tmp_path: Path):
    db = tmp_path / "cli.db"
    code, out, _ = _run(["retention"], db)
    assert code == 0
    report = json.loads(out)
    assert "errors" in report