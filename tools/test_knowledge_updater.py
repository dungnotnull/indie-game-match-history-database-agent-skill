"""test_knowledge_updater.py - Skill 263: indie-game-match-history-database

Validation: hash dedup, scoring, entry formatting. Run with:
    python tools/test_knowledge_updater.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knowledge_updater as ku  # noqa: E402


def assert_true(cond, label):
    if not cond:
        raise AssertionError(label)
    print("[OK] " + label)


def test_hash():
    a = ku.compute_hash("https://x.com/1")
    b = ku.compute_hash("https://x.com/1")
    c = ku.compute_hash("https://x.com/2")
    assert_true(a == b, "dedup hash stable")
    assert_true(a != c, "dedup hash distinct")
    assert_true(a == ku.compute_hash("  HTTPS://X.COM/1 "), "dedup hash case/space insensitive")


def test_score():
    cand = ku.Candidate(
        title=ku.KNOWLEDGE_CONFIG["domain"],
        authors=["A"], year=2026, venue="V",
        doi_or_url="https://x", abstract=ku.KNOWLEDGE_CONFIG["domain"],
        published_date=datetime.now(), citation_count=10, source="test",
    )
    s = ku.score_entry(cand, ku.KNOWLEDGE_CONFIG["keywords"], datetime.now())
    assert_true(0 <= s <= 10, "score in [0,10] (got %s)" % s)


def test_score_zero_for_old_no_keyword():
    cand = ku.Candidate(
        title="unrelated", authors=["A"], year=2000, venue="V",
        doi_or_url="https://x", abstract="nothing relevant",
        published_date=datetime(2000, 1, 1), citation_count=0, source="test",
    )
    s = ku.score_entry(cand, ku.KNOWLEDGE_CONFIG["keywords"], datetime.now())
    assert_true(s < 1.0, "old irrelevant entry scores low (got %s)" % s)


def test_format():
    cand = ku.Candidate(
        title="T", authors=["A"], year=2026, venue="V",
        doi_or_url="https://x", abstract="ab",
        published_date=datetime.now(), citation_count=0, source="test",
        score=5.0,
    )
    txt = ku.format_entry(cand)
    assert_true("DOI/URL:" in txt, "format has DOI/URL")
    assert_true("Relevance Score:" in txt, "format has relevance score")
    assert_true("### " in txt, "format has heading")


def test_config_sanity():
    cfg = ku.KNOWLEDGE_CONFIG
    assert_true(isinstance(cfg["keywords"], list) and len(cfg["keywords"]) >= 4,
                "config has >=4 keywords")
    w = cfg["scoring_weights"]
    assert_true(abs(sum(w.values()) - 1.0) < 1e-6, "scoring weights sum to 1.0")


if __name__ == "__main__":
    test_hash()
    test_score()
    test_score_zero_for_old_no_keyword()
    test_format()
    test_config_sanity()
    print("all knowledge_updater tests passed")