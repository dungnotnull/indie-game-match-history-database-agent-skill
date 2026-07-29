"""Tests for the privacy / retention pipeline."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from indie_match_history import (
    EngineConfig, MatchHistoryEngine, MatchOutcome, MatchResult,
    PrivacyPipeline, RetentionPolicy, ReplayStore,
)
from indie_match_history.config import RetentionConfig
from indie_match_history.errors import PrivacyError
from indie_match_history.storage import InMemoryStorage, SQLiteStorage, TieredStorage


def _engine_with_replays(tmp_path):
    cfg = EngineConfig(sqlite_path=tmp_path / "t.db", replay_root=tmp_path / "rp")
    return MatchHistoryEngine(config=cfg)


def test_tier_for_age_thresholds():
    from indie_match_history.storage import StorageTier
    tiered = TieredStorage(InMemoryStorage(), RetentionConfig(hot_days=10, warm_days=30, cold_days=60))
    assert tiered.tier_for_age(5) == StorageTier.HOT
    assert tiered.tier_for_age(20) == StorageTier.WARM
    assert tiered.tier_for_age(45) == StorageTier.COLD
    assert tiered.tier_for_age(90) == StorageTier.ARCHIVED


def test_refresh_tier_promotes_to_cold(tmp_path):
    eng = _engine_with_replays(tmp_path)
    a = eng.register_player("alice")
    b = eng.register_player("bob")
    old = datetime.utcnow() - timedelta(days=400)
    res = eng.record_match("pong", [
        MatchResult(a.player_id, MatchOutcome.WIN),
        MatchResult(b.player_id, MatchOutcome.LOSS),
    ], season="s1", started_at=old)
    from indie_match_history.storage import StorageTier
    tier = eng.tiered.refresh_tier(res.match.match_id)
    assert tier == StorageTier.COLD
    eng.close()


def test_retention_expires_old_replays(tmp_path):
    eng = _engine_with_replays(tmp_path)
    a = eng.register_player("alice")
    b = eng.register_player("bob")
    old = datetime.utcnow() - timedelta(days=400)
    res = eng.record_match("pong", [
        MatchResult(a.player_id, MatchOutcome.WIN),
        MatchResult(b.player_id, MatchOutcome.LOSS),
    ], season="s1", started_at=old)
    cfg = eng.config.replay
    blob = cfg.magic + b"oldreplay" * 200
    ref = eng.attach_replay(res.match.match_id, blob)
    report = eng.run_retention()
    assert report.replays_expired >= 1
    # Replay ref should now be gone.
    from indie_match_history.errors import NotFoundError
    with pytest.raises(NotFoundError):
        eng.storage.get_replay(ref.replay_id)
    eng.close()


def test_erase_player_removes_data(tmp_path):
    eng = _engine_with_replays(tmp_path)
    a = eng.register_player("alice")
    b = eng.register_player("bob")
    res = eng.record_match("pong", [
        MatchResult(a.player_id, MatchOutcome.WIN),
        MatchResult(b.player_id, MatchOutcome.LOSS),
    ], season="s1")
    summary = eng.erase_player(a.player_id)
    assert summary["players"] == 1
    from indie_match_history.errors import NotFoundError
    with pytest.raises(NotFoundError):
        eng.get_player(a.player_id)
    # bob still exists; the 1v1 match is gone
    assert eng.get_player(b.player_id).handle == "bob"
    assert eng.storage.count_matches() == 0
    eng.close()


def test_erase_minor_hard_delete(tmp_path):
    eng = _engine_with_replays(tmp_path)
    a = eng.register_player("alice", is_minor=True)
    summary = eng.erase_player(a.player_id)
    assert summary["players"] == 1
    eng.close()


def test_policy_validation_replay_window():
    bad = RetentionPolicy(
        config=RetentionConfig(hot_days=30, warm_days=60, cold_days=100, replay_max_age_days=1000),
    )
    eng = MatchHistoryEngine(storage=InMemoryStorage())
    eng.privacy.policy = bad
    with pytest.raises(PrivacyError):
        eng.privacy.validate_policy()
    eng.close()


def test_policy_validation_minors_requires_gdpr():
    bad = RetentionPolicy(
        config=RetentionConfig(default_gdpr_deletion=False),
        minors_force_delete=True,
    )
    eng = MatchHistoryEngine(storage=InMemoryStorage())
    eng.privacy.policy = bad
    with pytest.raises(PrivacyError):
        eng.privacy.validate_policy()
    eng.close()