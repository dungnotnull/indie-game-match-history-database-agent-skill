"""``imh`` command-line interface.

A focused, dependency-free CLI built on :mod:`argparse`. It exposes the engine
facade for local development, ops scripts, and CI smoke tests without pulling
in a web framework. Subcommands:

    imh init            create / migrate a SQLite database file
    imh player-add      register a pseudonymous player
    imh match-add       record a ranked 1v1 match from a JSON spec
    imh history         show a player's match history
    imh rating          show a player's latest rating
    imh leaderboard     print the top-N leaderboard for a season
    imh replay-attach   attach a replay blob file to a match
    imh retention       run the retention/tier-aging pipeline
    imh erase           erase a player (GDPR/COPPA)
    imh stats           print engine stats
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from .config import EngineConfig
from .engine import MatchHistoryEngine
from .errors import MatchHistoryError
from .models import MatchOutcome, MatchResult, RatingSystem
from .replay import ReplayStore
from .storage.sqlite import SQLiteStorage


def _build_engine(args: argparse.Namespace) -> MatchHistoryEngine:
    config = EngineConfig(
        rating_system=args.rating_system,
        sqlite_path=Path(args.db) if args.db else None,
        replay_root=Path(args.replay_root) if args.replay_root else None,
    )
    return MatchHistoryEngine(config=config)


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _coerce_results(spec: list[dict[str, Any]]) -> list[MatchResult]:
    out: list[MatchResult] = []
    for r in spec:
        out.append(
            MatchResult(
                player_id=r["player_id"],
                outcome=MatchOutcome.parse(r["outcome"]),
                team=r.get("team"),
                score=r.get("score"),
            )
        )
    return out


def cmd_init(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    # Opening the engine already migrates the schema; report the result.
    _print_json({"db": args.db or "<memory>", "migrated": True,
                 "version": engine.config.rating_system})
    return 0


def cmd_player_add(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    player = engine.register_player(
        args.handle, display_name=args.display_name, region=args.region,
        is_minor=args.minor,
    )
    _print_json(player.to_dict())
    return 0


def cmd_match_add(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    results = _coerce_results(spec["results"])
    result = engine.record_match(
        game_id=spec["game_id"], results=results, mode=spec.get("mode"),
        season=spec.get("season"), region=spec.get("region"),
    )
    _print_json({
        "match_id": result.match.match_id,
        "rating_deltas": {k: list(v) for k, v in result.rating_deltas.items()},
        "leaderboard_updates": result.leaderboard_updates,
    })
    return 0


def cmd_history(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    matches = engine.player_history(args.player_id, limit=args.limit)
    _print_json([m.to_dict() for m in matches])
    return 0


def cmd_rating(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    rating = engine.player_rating(args.player_id)
    _print_json(rating.to_dict())
    return 0


def cmd_leaderboard(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    entries = engine.leaderboard(args.game_id, args.season, top=args.top)
    _print_json([
        {"rank": e.position, "player_id": e.member, "rating": e.score}
        for e in entries
    ])
    return 0


def cmd_replay_attach(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    data = Path(args.file).read_bytes()
    ref = engine.attach_replay(args.match_id, data)
    _print_json(ref.to_dict())
    return 0


def cmd_retention(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    report = engine.run_retention()
    _print_json(report.to_dict())
    return 0


def cmd_erase(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    summary = engine.erase_player(args.player_id)
    _print_json(summary)
    return 0


def cmd_stats(engine: MatchHistoryEngine, args: argparse.Namespace) -> int:
    _print_json(engine.stats())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="imh", description="indie match-history CLI")
    p.add_argument("--db", default=None, help="SQLite database path (default: memory)")
    p.add_argument("--rating-system", default="elo", choices=("elo", "glicko2"))
    p.add_argument("--replay-root", default=None, help="replay blob root directory")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="create/migrate the database")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("player-add", help="register a player")
    sp.add_argument("--handle", required=True)
    sp.add_argument("--display-name")
    sp.add_argument("--region")
    sp.add_argument("--minor", action="store_true")
    sp.set_defaults(func=cmd_player_add)

    sp = sub.add_parser("match-add", help="record a match from a JSON spec file")
    sp.add_argument("--spec", required=True, help="path to JSON match spec")
    sp.set_defaults(func=cmd_match_add)

    sp = sub.add_parser("history", help="player match history")
    sp.add_argument("--player-id", required=True)
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_history)

    sp = sub.add_parser("rating", help="player latest rating")
    sp.add_argument("--player-id", required=True)
    sp.set_defaults(func=cmd_rating)

    sp = sub.add_parser("leaderboard", help="season leaderboard")
    sp.add_argument("--game-id", required=True)
    sp.add_argument("--season", required=True)
    sp.add_argument("--top", type=int, default=10)
    sp.set_defaults(func=cmd_leaderboard)

    sp = sub.add_parser("replay-attach", help="attach a replay blob to a match")
    sp.add_argument("--match-id", required=True)
    sp.add_argument("--file", required=True)
    sp.set_defaults(func=cmd_replay_attach)

    sp = sub.add_parser("retention", help="run retention/tier-aging")
    sp.set_defaults(func=cmd_retention)

    sp = sub.add_parser("erase", help="erase a player (GDPR/COPPA)")
    sp.add_argument("--player-id", required=True)
    sp.set_defaults(func=cmd_erase)

    sp = sub.add_parser("stats", help="engine stats")
    sp.set_defaults(func=cmd_stats)

    return p


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    engine = _build_engine(args)
    try:
        with engine:
            return args.func(engine, args)
    except MatchHistoryError as ex:
        print(f"[imh] error: {ex.code}: {ex}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError) as ex:
        print(f"[imh] error: {type(ex).__name__}: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())