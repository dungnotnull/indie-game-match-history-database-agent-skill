"""knowledge_updater.py - Skill 263: indie-game-match-history-database

Living knowledge-base crawl pipeline for SECOND-KNOWLEDGE-BRAIN.md.

Fetches candidate academic + news items from ArXiv, Semantic Scholar, and RSS
feeds, deduplicates by SHA-256 of DOI/URL, scores each candidate
(recency + keyword relevance + citation count), and appends the top-N to the
knowledge base. Optional dependencies (requests, feedparser, python-dateutil)
are imported lazily so the script degrades gracefully when only the stdlib is
available.

Usage:
    python tools/knowledge_updater.py [--dry-run] [--news-only] [--keywords ...] [--list]

Exit codes: 0 success, 1 misconfiguration / IO error, 2 partial failure.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore

try:
    import feedparser  # type: ignore
except ImportError:
    feedparser = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
BRAIN_PATH = ROOT / "SECOND-KNOWLEDGE-BRAIN.md"
LOG_PATH = ROOT / "logs" / "knowledge_update.log"

KNOWLEDGE_CONFIG: dict[str, Any] = {
    "domain": "Indie Game Match-History Data Engineering",
    "keywords": [
        "game match history database",
        "time series leaderboard",
        "ELO rating storage",
        "replay blob storage",
        "match data schema",
        "GDPR retention game analytics",
        "Glicko rating system",
        "scoreboard sharding",
    ],
    "arxiv_categories": ["cs.DB", "cs.GT"],
    "arxiv_base": "https://export.arxiv.org/api/query",
    "semantic_scholar_base": "https://api.semanticscholar.org/graph/v1/paper/search",
    "rss_feeds": [
        "https://www.postgresql.org/about/newsrss.xml",
        "https://redis.io/news/rss",
    ],
    "authoritative_docs": [
        "Proceedings of the VLDB Endowment",
        "IEEE Transactions on Games",
        "Information Systems - Elsevier",
        "Entertainment Computing - Elsevier",
        "Journal of Systems and Software - Elsevier",
        "Computers in Human Behavior - Elsevier",
    ],
    "scoring_weights": {"recency": 0.4, "keyword_relevance": 0.4, "citation_count": 0.2},
    "max_results_per_source": 10,
    "max_new_entries_per_run": 20,
}


@dataclass
class Candidate:
    title: str
    authors: list[str]
    year: int
    venue: str
    doi_or_url: str
    abstract: str
    published_date: datetime | None
    citation_count: int
    source: str
    score: float = 0.0

    def to_log(self) -> dict[str, Any]:
        return {
            "title": self.title, "source": self.source,
            "doi_or_url": self.doi_or_url, "score": self.score,
        }


def log(msg: str, **fields: Any) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    extras = " " + " ".join(f"{k}={v}" for k, v in fields.items()) if fields else ""
    line = f"[{ts}] {msg}{extras}"
    print(line, file=sys.stderr, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def compute_hash(identifier: str) -> str:
    return hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()


def load_existing_hashes() -> set[str]:
    if not BRAIN_PATH.exists():
        return set()
    hashes: set[str] = set()
    text = BRAIN_PATH.read_text(encoding="utf-8")
    for m in re.finditer(r"\*\*DOI/URL:\*\*\s*(\S+)", text):
        hashes.add(compute_hash(m.group(1)))
    # also catch bare DOI/URL lines from the seeded table
    for m in re.finditer(r"https?://\S+|10\.\d{4,9}/\S+", text):
        hashes.add(compute_hash(m.group(0).rstrip("|")))
    return hashes


def score_entry(entry: Candidate, keywords: list[str], now: datetime) -> float:
    recency = 0.0
    if entry.published_date is not None:
        days = (now - entry.published_date).days
        recency = max(0.0, 1.0 - days / 730.0)
    text = (entry.title + " " + entry.abstract).lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    relevance = min(hits / max(len(keywords), 1), 1.0)
    cit = entry.citation_count or 0
    cit_score = min(math.log1p(cit) / math.log1p(1000), 1.0)
    w = KNOWLEDGE_CONFIG["scoring_weights"]
    return round((recency * w["recency"] + relevance * w["keyword_relevance"]
                  + cit_score * w["citation_count"]) * 10.0, 2)


def fetch_with_retry(url: str, params: dict | None = None,
                     max_retries: int = 3, base_delay: float = 2.0):
    if requests is None:
        return None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(base_delay * (2 ** attempt))
            resp = requests.get(url, params=params or {}, timeout=30)
            if resp.status_code == 429 or resp.status_code >= 500:
                log("retryable status", url=url, status=resp.status_code, attempt=attempt + 1)
                if attempt < max_retries - 1:
                    continue
                return None
            resp.raise_for_status()
            return resp
        except Exception as ex:  # noqa: BLE001 - network errors are non-fatal
            log("request failed", url=url, error=str(ex), attempt=attempt + 1)
            if attempt >= max_retries - 1:
                return None
    return None


def fetch_arxiv(keywords: list[str]) -> list[Candidate]:
    if requests is None or not KNOWLEDGE_CONFIG["arxiv_categories"]:
        return []
    cats = KNOWLEDGE_CONFIG["arxiv_categories"]
    q = ("(" + " OR ".join("cat:" + c for c in cats) + ") AND ("
         + " OR ".join('"' + k + '"' for k in keywords[:5]) + ")")
    resp = fetch_with_retry(KNOWLEDGE_CONFIG["arxiv_base"], {
        "search_query": q, "sortBy": "submittedDate", "sortOrder": "descending",
        "max_results": KNOWLEDGE_CONFIG["max_results_per_source"],
    })
    if resp is None:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return []
    out: list[Candidate] = []
    for entry in root.findall("atom:entry", ns):
        t = entry.find("atom:title", ns)
        s = entry.find("atom:summary", ns)
        i = entry.find("atom:id", ns)
        p = entry.find("atom:published", ns)
        title = (t.text or "").strip().replace("\n", " ") if t is not None else ""
        url = (i.text or "").strip() if i is not None else ""
        if not title or not url:
            continue
        pub = _parse_date(p.text) if p is not None and p.text else None
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)
                   if a.find("atom:name", ns) is not None][:3]
        out.append(Candidate(
            title=title, authors=authors,
            year=pub.year if pub else datetime.now().year,
            venue="ArXiv", doi_or_url=url,
            abstract=(s.text or "")[:300] if s is not None else "",
            published_date=pub, citation_count=0, source="arxiv",
        ))
    log("arxiv fetched", count=len(out))
    return out


def fetch_semantic_scholar(keywords: list[str]) -> list[Candidate]:
    if requests is None:
        return []
    resp = fetch_with_retry(KNOWLEDGE_CONFIG["semantic_scholar_base"], {
        "query": " ".join(keywords[:4]),
        "fields": "title,authors,year,venue,externalIds,abstract,citationCount",
        "limit": KNOWLEDGE_CONFIG["max_results_per_source"],
    })
    if resp is None:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    out: list[Candidate] = []
    for p in data.get("data", []):
        title = p.get("title") or ""
        if not title:
            continue
        year = p.get("year") or datetime.now().year
        ext = p.get("externalIds", {}) or {}
        doi = ext.get("DOI") or (f"https://arxiv.org/abs/{ext['ArXiv']}" if ext.get("ArXiv") else "")
        if not doi:
            doi = "https://www.semanticscholar.org/paper/" + str(p.get("paperId", ""))
        out.append(Candidate(
            title=title,
            authors=[a.get("name", "") for a in p.get("authors", [])[:3]],
            year=year, venue=p.get("venue") or "Unknown", doi_or_url=doi,
            abstract=(p.get("abstract") or "")[:300],
            published_date=datetime(year, 1, 1),
            citation_count=p.get("citationCount", 0) or 0,
            source="semantic_scholar",
        ))
    log("semantic_scholar fetched", count=len(out))
    return out


def fetch_rss() -> list[Candidate]:
    if feedparser is None or not KNOWLEDGE_CONFIG["rss_feeds"]:
        return []
    out: list[Candidate] = []
    for url in KNOWLEDGE_CONFIG["rss_feeds"]:
        try:
            feed = feedparser.parse(url)
        except Exception as ex:  # noqa: BLE001
            log("rss failed", url=url, error=str(ex))
            continue
        for item in feed.entries[:10]:
            title = item.get("title", "")
            link = item.get("link", "")
            if not title or not link:
                continue
            pp = item.get("published_parsed")
            pub = datetime(*pp[:6]) if pp else datetime.now()
            out.append(Candidate(
                title=title, authors=["Editorial"], year=pub.year, venue="RSS",
                doi_or_url=link, abstract=(item.get("summary", ""))[:200],
                published_date=pub, citation_count=0, source="rss",
            ))
    log("rss fetched", count=len(out))
    return out


def _parse_date(value: str) -> datetime | None:
    try:
        from dateutil import parser as dp  # type: ignore
        return dp.parse(value).replace(tzinfo=None)
    except Exception:  # noqa: BLE001
        try:
            return datetime.fromisoformat(value.rstrip("Z"))
        except ValueError:
            return None


def format_entry(entry: Candidate) -> str:
    d = datetime.now().strftime("%Y-%m-%d")
    authors = ", ".join(entry.authors) or "Unknown"
    return (
        "\n### " + d + " - " + entry.title + "\n"
        "- **Authors:** " + authors + "\n"
        "- **Year:** " + str(entry.year) + "\n"
        "- **Venue:** " + entry.venue + "\n"
        "- **DOI/URL:** " + entry.doi_or_url + "\n"
        "- **Relevance Score:** " + str(entry.score) + "/10\n"
        "- **Key Finding:** " + (entry.abstract or "No abstract available.") + "\n"
    )


def append_to_brain(entries: list[Candidate], dry_run: bool = False) -> int:
    if not BRAIN_PATH.exists():
        log("brain not found", path=str(BRAIN_PATH))
        return 0
    existing = load_existing_hashes()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new: list[Candidate] = []
    for e in entries:
        if not e.doi_or_url:
            continue
        h = compute_hash(e.doi_or_url)
        if h in existing:
            continue
        existing.add(h)
        e.score = score_entry(e, KNOWLEDGE_CONFIG["keywords"], now)
        new.append(e)
    if not new:
        log("no new entries")
        return 0
    new.sort(key=lambda x: x.score, reverse=True)
    new = new[: KNOWLEDGE_CONFIG["max_new_entries_per_run"]]
    text = "".join(format_entry(e) for e in new)
    if dry_run:
        log("dry-run would append", count=len(new))
        return len(new)
    content = BRAIN_PATH.read_text(encoding="utf-8")
    if "## 7. Knowledge Update Log" in content:
        content += text
    else:
        content += "\n## 7. Knowledge Update Log\n" + text
    BRAIN_PATH.write_text(content, encoding="utf-8")
    log("appended", count=len(new))
    return len(new)


def list_brain_entries() -> int:
    import json
    if not BRAIN_PATH.exists():
        print("[]")
        return 0
    text = BRAIN_PATH.read_text(encoding="utf-8")
    entries: list[dict[str, str]] = []
    current_title: str | None = None
    for line in text.splitlines():
        m_title = re.match(r"^###\s+(.+)$", line)
        if m_title:
            current_title = m_title.group(1).strip()
            continue
        m_doi = re.match(r"^-\s*\*\*DOI/URL:\*\*\s*(\S+)", line)
        if m_doi and current_title:
            entries.append({"title": current_title, "doi_or_url": m_doi.group(1)})
            current_title = None
    print(json.dumps(entries, ensure_ascii=False, indent=2))
    return len(entries)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="knowledge-base crawl pipeline")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--news-only", action="store_true")
    ap.add_argument("--keywords", nargs="+", default=KNOWLEDGE_CONFIG["keywords"])
    ap.add_argument("--list", action="store_true", help="list brain entries and exit")
    args = ap.parse_args(argv)

    if args.list:
        return 0 if list_brain_entries() >= 0 else 1

    log("start", dry=args.dry_run, news=args.news_only)
    candidates: list[Candidate] = []
    if not args.news_only:
        candidates += fetch_arxiv(args.keywords)
        time.sleep(1)
        candidates += fetch_semantic_scholar(args.keywords)
        time.sleep(1)
    candidates += fetch_rss()
    log("candidates", count=len(candidates))
    appended = append_to_brain(candidates, args.dry_run)
    log("done", appended=appended)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())