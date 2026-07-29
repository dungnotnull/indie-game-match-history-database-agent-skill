"""SQLite storage backend - durable, file-based, zero-dependency default.

Uses the stdlib :mod:`sqlite3` module. All statements are parameterized.
Connection is opened with `check_same_thread=False` and guarded by an RLock so
the backend can be shared across request-handling threads in a small server.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..errors import ConflictError, NotFoundError, StorageError
from ..models import Match, MatchEvent, MatchOutcome, MatchResult, Player, Rating, RatingSystem, ReplayRef
from ..schema import SCHEMA_VERSION, migrate
from ..utils import isoformat, parse_iso, utcnow
from .base import PlayerRatingRecord, StorageBackend, StorageTier

_PURGED = "<purged>"


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class SQLiteStorage(StorageBackend):
    """File-backed SQLite storage. Auto-migrates to the current schema."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._lock = threading.RLock()
        try:
            self._conn = sqlite3.connect(
                self._path, check_same_thread=False, isolation_level=None
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
        except sqlite3.Error as ex:
            raise StorageError(f"cannot open sqlite at {self._path}: {ex}") from ex
        try:
            migrate(self._conn, SCHEMA_VERSION)
        except Exception as ex:
            self._conn.close()
            raise StorageError(f"schema migration failed: {ex}") from ex

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass

    def __enter__(self) -> "SQLiteStorage":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- helpers -----------------------------------------------------------
    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            return self._conn.execute(sql, params)
        except sqlite3.IntegrityError as ex:
            raise ConflictError(str(ex)) from ex
        except sqlite3.Error as ex:
            raise StorageError(str(ex)) from ex

    def _one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._exec(sql, params).fetchone()

    @staticmethod
    def _require(row: sqlite3.Row | None, kind: str, key: str):
        if row is None:
            raise NotFoundError(f"{kind} {key!r} not found")
        return row

    # -- players -----------------------------------------------------------
    def upsert_player(self, player: Player) -> None:
        with self._lock:
            self._exec(
                "INSERT INTO players(player_id, handle, display_name, region, "
                "created_at, is_minor, deleted, metadata) "
                "VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(player_id) DO UPDATE SET "
                "handle=excluded.handle, display_name=excluded.display_name, "
                "region=excluded.region, is_minor=excluded.is_minor, "
                "deleted=excluded.deleted, metadata=excluded.metadata",
                (
                    player.player_id, player.handle, player.display_name,
                    player.region, isoformat(player.created_at),
                    int(player.is_minor), int(player.deleted), _json(player.metadata),
                ),
            )

    def get_player(self, player_id: str) -> Player:
        row = self._one(
            "SELECT * FROM players WHERE player_id = ?", (player_id,)
        )
        return self._row_to_player(self._require(row, "player", player_id))

    def get_player_by_handle(self, handle: str) -> Player | None:
        row = self._one("SELECT * FROM players WHERE handle = ?", (handle,))
        return self._row_to_player(row) if row else None

    def list_players(self, limit: int = 100, offset: int = 0) -> list[Player]:
        with self._lock:
            rows = self._exec(
                "SELECT * FROM players WHERE deleted = 0 "
                "ORDER BY created_at LIMIT ? OFFSET ?",
                (int(limit), int(offset)),
            ).fetchall()
        return [self._row_to_player(r) for r in rows]

    def mark_player_deleted(self, player_id: str) -> None:
        with self._lock:
            cur = self._exec(
                "UPDATE players SET deleted = 1 WHERE player_id = ?", (player_id,)
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"player {player_id!r} not found")

    @staticmethod
    def _row_to_player(row: sqlite3.Row) -> Player:
        return Player(
            player_id=row["player_id"], handle=row["handle"],
            display_name=row["display_name"], region=row["region"],
            created_at=parse_iso(row["created_at"]),
            is_minor=bool(row["is_minor"]), deleted=bool(row["deleted"]),
            metadata=json.loads(row["metadata"] or "{}"),
        )

    # -- matches -----------------------------------------------------------
    def insert_match(self, match: Match) -> None:
        with self._lock:
            if self._one("SELECT 1 FROM matches WHERE match_id = ?",
                         (match.match_id,)) is not None:
                raise ConflictError(f"match {match.match_id!r} already exists")
            self._exec(
                "INSERT INTO matches(match_id, game_id, mode, season, started_at, "
                "ended_at, duration_ms, region, replay_id, metadata) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    match.match_id, match.game_id, match.mode, match.season,
                    isoformat(match.started_at),
                    isoformat(match.ended_at) if match.ended_at else None,
                    match.duration_ms, match.region, match.replay_id,
                    _json(match.metadata),
                ),
            )
            for r in match.results:
                self._exec(
                    "INSERT INTO match_results(match_id, player_id, team, outcome, "
                    "score, rating_before, rating_after) VALUES(?,?,?,?,?,?,?)",
                    (
                        match.match_id, r.player_id, r.team, r.outcome.value,
                        r.score, r.rating_before, r.rating_after,
                    ),
                )
            for ev in match.events:
                self._insert_event_row(ev)
            self.set_match_tier(match.match_id, StorageTier.HOT)

    def _insert_event_row(self, ev: MatchEvent) -> None:
        self._exec(
            "INSERT INTO match_events(event_id, match_id, player_id, kind, ts, payload) "
            "VALUES(?,?,?,?,?,?)",
            (ev.event_id, ev.match_id, ev.player_id, ev.kind,
             isoformat(ev.ts), _json(ev.payload)),
        )

    def get_match(self, match_id: str) -> Match:
        row = self._one("SELECT * FROM matches WHERE match_id = ?", (match_id,))
        self._require(row, "match", match_id)
        return self._row_to_match(row)

    def _row_to_match(self, row: sqlite3.Row) -> Match:
        results = [
            MatchResult(
                player_id=r["player_id"],
                outcome=MatchOutcome.parse(r['outcome']),
                team=r["team"], score=r["score"],
                rating_before=r["rating_before"], rating_after=r["rating_after"],
            )
            for r in self._exec(
                "SELECT * FROM match_results WHERE match_id = ?", (row["match_id"],)
            ).fetchall()
        ]
        events = [
            MatchEvent(
                event_id=e["event_id"], match_id=e["match_id"],
                player_id=e["player_id"], kind=e["kind"],
                ts=parse_iso(e["ts"]),
                payload=json.loads(e["payload"] or "{}"),
            )
            for e in self._exec(
                "SELECT * FROM match_events WHERE match_id = ? ORDER BY ts",
                (row["match_id"],),
            ).fetchall()
        ]
        return Match(
            match_id=row["match_id"], game_id=row["game_id"], mode=row["mode"],
            season=row["season"], started_at=parse_iso(row["started_at"]),
            results=tuple(results), events=tuple(events),
            ended_at=parse_iso(row["ended_at"]) if row["ended_at"] else None,
            duration_ms=row["duration_ms"], region=row["region"],
            replay_id=row["replay_id"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def list_matches(
        self,
        game_id: str | None = None,
        player_id: str | None = None,
        season: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Match]:
        sql = "SELECT DISTINCT m.* FROM matches m"
        params: list = []
        joins: list[str] = []
        where: list[str] = []
        if player_id is not None:
            joins.append("JOIN match_results r ON r.match_id = m.match_id")
            where.append("r.player_id = ?")
            params.append(player_id)
        if game_id is not None:
            where.append("m.game_id = ?")
            params.append(game_id)
        if season is not None:
            where.append("m.season = ?")
            params.append(season)
        if joins:
            sql += " " + " ".join(joins)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.started_at DESC LIMIT ? OFFSET ?"
        params += [int(limit), int(offset)]
        with self._lock:
            rows = self._exec(sql, tuple(params)).fetchall()
        return [self._row_to_match(r) for r in rows]

    def player_history(
        self, player_id: str, limit: int = 100, offset: int = 0
    ) -> list[Match]:
        return self.list_matches(player_id=player_id, limit=limit, offset=offset)

    # -- events ------------------------------------------------------------
    def insert_events(self, events: Iterable[MatchEvent]) -> int:
        events = list(events)
        with self._lock:
            for ev in events:
                if self._one("SELECT 1 FROM matches WHERE match_id = ?",
                             (ev.match_id,)) is None:
                    raise NotFoundError(f"match {ev.match_id!r} not found")
                self._insert_event_row(ev)
            return len(events)

    def list_events(self, match_id: str) -> list[MatchEvent]:
        if self._one("SELECT 1 FROM matches WHERE match_id = ?",
                     (match_id,)) is None:
            raise NotFoundError(f"match {match_id!r} not found")
        with self._lock:
            rows = self._exec(
                "SELECT * FROM match_events WHERE match_id = ? ORDER BY ts",
                (match_id,),
            ).fetchall()
        return [
            MatchEvent(
                event_id=e["event_id"], match_id=e["match_id"],
                player_id=e["player_id"], kind=e["kind"],
                ts=parse_iso(e["ts"]),
                payload=json.loads(e["payload"] or "{}"),
            )
            for e in rows
        ]

    # -- ratings -----------------------------------------------------------
    def save_rating(self, record: PlayerRatingRecord) -> None:
        with self._lock:
            self._exec(
                "INSERT INTO rating_snapshots(player_id, match_id, system, "
                "rating, rd, vol, ts) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(player_id, match_id, system) DO UPDATE SET "
                "rating=excluded.rating, rd=excluded.rd, vol=excluded.vol, "
                "ts=excluded.ts",
                (
                    record.player_id, record.match_id, record.rating.system.value,
                    record.rating.value, record.rating.rd, record.rating.vol,
                    isoformat(record.ts),
                ),
            )

    def latest_rating(self, player_id: str) -> Rating | None:
        row = self._one(
            "SELECT * FROM rating_snapshots WHERE player_id = ? "
            "ORDER BY ts DESC LIMIT 1",
            (player_id,),
        )
        if row is None:
            return None
        return Rating(
            value=row["rating"], rd=row["rd"], vol=row["vol"],
            system=RatingSystem.parse(row['system']),
        )

    def rating_history(
        self, player_id: str, limit: int = 100
    ) -> list[PlayerRatingRecord]:
        with self._lock:
            rows = self._exec(
                "SELECT * FROM rating_snapshots WHERE player_id = ? "
                "ORDER BY ts DESC LIMIT ?",
                (player_id, int(limit)),
            ).fetchall()
        return [
            PlayerRatingRecord(
                player_id=r["player_id"],
                rating=Rating(
                    value=r["rating"], rd=r["rd"], vol=r["vol"],
                    system=RatingSystem.parse(r['system']),
                ),
                match_id=r["match_id"], ts=parse_iso(r["ts"]),
            )
            for r in rows
        ]

    # -- replays -----------------------------------------------------------
    def upsert_replay(self, replay: ReplayRef) -> None:
        with self._lock:
            self._exec(
                "INSERT INTO replays(replay_id, match_id, game_id, blob_path, "
                "size_bytes, sha256, created_at) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(replay_id) DO UPDATE SET "
                "match_id=excluded.match_id, blob_path=excluded.blob_path, "
                "size_bytes=excluded.size_bytes, sha256=excluded.sha256",
                (
                    replay.replay_id, replay.match_id, replay.game_id,
                    replay.blob_path, replay.size_bytes, replay.sha256,
                    isoformat(replay.created_at),
                ),
            )

    def get_replay(self, replay_id: str) -> ReplayRef:
        row = self._one("SELECT * FROM replays WHERE replay_id = ?", (replay_id,))
        self._require(row, "replay", replay_id)
        return ReplayRef(
            replay_id=row["replay_id"], match_id=row["match_id"],
            game_id=row["game_id"], blob_path=row["blob_path"],
            size_bytes=row["size_bytes"], sha256=row["sha256"],
            created_at=parse_iso(row["created_at"]),
        )

    def delete_replay(self, replay_id: str) -> None:
        with self._lock:
            cur = self._exec("DELETE FROM replays WHERE replay_id = ?", (replay_id,))
            if cur.rowcount == 0:
                raise NotFoundError(f"replay {replay_id!r} not found")

    def link_replay(self, match_id: str, replay_id: str) -> None:
        with self._lock:
            cur = self._exec(
                "UPDATE matches SET replay_id = ? WHERE match_id = ?",
                (replay_id, match_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"match {match_id!r} not found")

    # -- tiering -----------------------------------------------------------
    def set_match_tier(self, match_id: str, tier: StorageTier) -> None:
        with self._lock:
            self._exec(
                "INSERT INTO schema_meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (f"tier:{match_id}", tier.value),
            )

    def get_match_tier(self, match_id: str) -> StorageTier:
        row = self._one(
            "SELECT value FROM schema_meta WHERE key = ?", (f"tier:{match_id}",)
        )
        if row is None:
            return StorageTier.HOT
        return StorageTier(row["value"])

    def count_matches(self, game_id: str | None = None) -> int:
        if game_id is None:
            row = self._one("SELECT COUNT(*) AS c FROM matches")
        else:
            row = self._one(
                "SELECT COUNT(*) AS c FROM matches WHERE game_id = ?", (game_id,)
            )
        return int(row["c"]) if row else 0

    # -- privacy -----------------------------------------------------------
    def purge_player_data(self, player_id: str) -> dict[str, int]:
        summary = {"players": 0, "matches": 0, "events": 0, "ratings": 0, "replays": 0}
        with self._lock:
            player = self._one(
                "SELECT * FROM players WHERE player_id = ?", (player_id,)
            )
            if player is None:
                raise NotFoundError(f"player {player_id!r} not found")

            # 1v1 matches the player was in: drop entirely (match + results + events)
            solo_rows = self._exec(
                "SELECT m.match_id, (SELECT COUNT(*) FROM match_results "
                "WHERE match_id = m.match_id) AS n "
                "FROM matches m JOIN match_results r ON r.match_id = m.match_id "
                "WHERE r.player_id = ?",
                (player_id,),
            ).fetchall()
            drop_ids = [r["match_id"] for r in solo_rows if r["n"] <= 2]
            for mid in drop_ids:
                summary["events"] += int(
                    self._exec(
                        "SELECT COUNT(*) AS c FROM match_events WHERE match_id = ?",
                        (mid,),
                    ).fetchone()["c"]
                )
                self._exec("DELETE FROM match_events WHERE match_id = ?", (mid,))
                self._exec("DELETE FROM match_results WHERE match_id = ?", (mid,))
                self._exec("DELETE FROM matches WHERE match_id = ?", (mid,))
                self._exec(
                    "DELETE FROM schema_meta WHERE key = ?", (f"tier:{mid}",)
                )
                summary["matches"] += 1

            # Team matches (>2): anonymize the player's result rows
            team_rows = self._exec(
                "SELECT match_id FROM match_results WHERE player_id = ?",
                (player_id,),
            ).fetchall()
            for r in team_rows:
                self._exec(
                    "UPDATE match_results SET player_id = ?, rating_before = NULL, "
                    "rating_after = NULL WHERE match_id = ? AND player_id = ?",
                    (_PURGED, r["match_id"], player_id),
                )

            summary["ratings"] = int(
                self._exec(
                    "DELETE FROM rating_snapshots WHERE player_id = ?",
                    (player_id,),
                ).rowcount
            )
            self._exec("DELETE FROM players WHERE player_id = ?", (player_id,))
            summary["players"] = 1
        return summary