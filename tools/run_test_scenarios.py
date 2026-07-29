"""run_test_scenarios.py - Skill 263: indie-game-match-history-database

Production-grade structural & content validator. Verifies:
  1. The 8-File Contract (skill harness files).
  2. Sub-skill content, knowledge base, test scenarios, quality-gate coverage.
  3. The indie_match_history engine package layout + public API.
  4. A live smoke run of the engine (register -> match -> leaderboard).

Exit code 0 = all checks pass, non-zero = failures.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
PKG = ROOT / "indie_match_history"
TESTS = ROOT / "tests"

GATES = ["U1", "U2", "U3", "U4", "U5", "U6", "G1", "G2", "G3", "G4"]
VERDICTS = ["Scalable Schema", "Conditional (scale)", "Unscalable/Non-private", "Inconclusive"]

_checks_passed = 0
_checks_failed = 0
_failures: list[str] = []


def ok(label: str, detail: str = "") -> None:
    global _checks_passed
    _checks_passed += 1


def fail(label: str, detail: str = "") -> None:
    global _checks_failed
    _checks_failed += 1
    _failures.append(f"{label}: {detail}")


def require(cond: bool, label: str, detail: str = "") -> None:
    (ok if cond else fail)(label, detail)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ---- 1. Skill harness file structure --------------------------------------
REQUIRED_FILES = [
    "CLAUDE.md", "PROJECT-detail.md", "PROJECT-DEVELOPMENT-PHASE-TRACKING.md",
    "README.md", "SECOND-KNOWLEDGE-BRAIN.md", "skills/main.md",
    "tools/knowledge_updater.py", "tools/test_knowledge_updater.py",
    "tools/run_test_scenarios.py", "tests/test-scenarios.md", "tests/TEST_RESULTS.md",
    "pyproject.toml", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
]
for f in REQUIRED_FILES:
    require((ROOT / f).exists(), f"file present: {f}")

subs = sorted(SKILLS.glob("sub-*.md"))
require(len(subs) >= 5, "at least 5 sub-skills", f"found {len(subs)}")
expected_subs = {
    "sub-gather-requirements", "sub-evidence-collector", "sub-core-analysis",
    "sub-knowledge-updater", "sub-advisor",
}
got_subs = {s.stem for s in subs}
require(got_subs == expected_subs, "sub-skill set", f"got {got_subs}")

# ---- 2. Frontmatter + sections --------------------------------------------
FM = re.compile(r"^---\s*\n(.*?\n)---", re.S)
for s in subs:
    txt = read(s)
    m = FM.search(txt)
    require(bool(m), f"{s.name}: frontmatter")
    if m:
        require("name:" in m.group(1) and "description:" in m.group(1),
                f"{s.name}: name+description")
    for sec in ["Role & Persona", "Workflow", "Output Format", "Quality Gates"]:
        require(sec in txt, f"{s.name}: section {sec}")

main_txt = read(ROOT / "skills" / "main.md")
for sec in ["Role & Persona", "Quality Gates", "Graceful Degradation"]:
    require(sec in main_txt, f"main.md: section {sec}")
require(("Harness Execution Protocol" in main_txt) or ("Workflow" in main_txt),
        "main.md: harness workflow heading")
require("Pre-Flight" in main_txt, "main.md: pre-flight language detection")
require("limitation" in main_txt.lower(), "main.md: limitation banner")

# ---- 3. Quality gate coverage ---------------------------------------------
for g in GATES:
    require(g in main_txt, f"main.md: gate {g} present")
adv = read(ROOT / "skills" / "sub-advisor.md")
for v in VERDICTS:
    require(v in adv or v in main_txt, f"advisor/verdict {v} present")

# ---- 4. Knowledge base -----------------------------------------------------
brain = read(ROOT / "SECOND-KNOWLEDGE-BRAIN.md")
require("Tier 1" in brain and "Tier 4" in brain, "brain: evidence hierarchy tiers")
dois = re.findall(r"10\.\d{4,9}/[^\s|]+", brain)
require(len(dois) >= 2, "brain: >=2 DOI-cited references", f"found {len(dois)}")
require("## 4. Authoritative Data Sources" in brain, "brain: data sources section")
require("## 6. Self-Update Protocol" in brain, "brain: self-update protocol")

# ---- 5. test-scenarios -----------------------------------------------------
sc = read(ROOT / "tests" / "test-scenarios.md")
require(sc.count("Scenario") >= 5, "scenarios: >=5")
require("degraded" in sc.lower() or "missing" in sc.lower(), "scenarios: degraded case")
require("conflict" in sc.lower() or "compar" in sc.lower(), "scenarios: comparison/conflict case")
for g in ["G1", "G2", "G3"]:
    require(g in sc, f"scenarios: gate {g} referenced")

# ---- 6. knowledge_updater.py ----------------------------------------------
ku = read(ROOT / "tools" / "knowledge_updater.py")
require("KNOWLEDGE_CONFIG" in ku, "knowledge_updater: KNOWLEDGE_CONFIG")
require("sha256" in ku, "knowledge_updater: SHA256 dedup")
require("score_entry" in ku, "knowledge_updater: scoring")
require("--dry-run" in ku and "--list" in ku, "knowledge_updater: dry-run + list flags")

# ---- 7. PDPT + README + PROJECT-detail ------------------------------------
pdpt = read(ROOT / "PROJECT-DEVELOPMENT-PHASE-TRACKING.md")
require("100%" in pdpt, "PDPT: 100% markers")
require("Phase 5" in pdpt, "PDPT: Phase 5")
readme = read(ROOT / "README.md")
require(("Quick start" in readme) or ("Usage" in readme), "README: usage/quick-start")
pd = read(ROOT / "PROJECT-detail.md")
require("Idea (Vietnamese)" in pd, "PROJECT-detail: Idea (Vietnamese)")
require("Harness Architecture" in pd, "PROJECT-detail: harness architecture")

# ---- 8. Engine package layout + public API --------------------------------
required_pkg = [
    "__init__.py", "errors.py", "utils.py", "logging_utils.py", "config.py",
    "schema.py", "models.py", "ratings.py", "leaderboard.py", "replay.py",
    "privacy.py", "engine.py", "cli.py",
    "storage/__init__.py", "storage/base.py", "storage/memory.py",
    "storage/sqlite.py", "storage/tiered.py",
]
for f in required_pkg:
    require((PKG / f).exists(), f"package: {f}")

required_tests = [
    "conftest.py", "test_models.py", "test_ratings.py", "test_storage.py",
    "test_leaderboard.py", "test_replay.py", "test_privacy.py",
    "test_engine.py", "test_cli.py", "test_schema.py",
]
for f in required_tests:
    require((TESTS / f).exists(), f"tests: {f}")

# Import the package and verify public API symbols.
sys.path.insert(0, str(ROOT))
try:
    import indie_match_history as imh  # noqa: E402
    api_ok = all(
        hasattr(imh, name) for name in [
            "MatchHistoryEngine", "Player", "Match", "MatchResult", "MatchEvent",
            "MatchOutcome", "Rating", "RatingSystem", "EloEngine", "Glicko2Engine",
            "Leaderboard", "ReplayStore", "PrivacyPipeline", "RetentionPolicy",
            "InMemoryStorage", "SQLiteStorage", "TieredStorage", "StorageBackend",
            "StorageTier", "EngineConfig", "SCHEMA_VERSION", "migrate", "__version__",
        ]
    )
    require(api_ok, "package: public API surface")
    require(isinstance(imh.__version__, str) and imh.__version__, "package: version string")
except Exception as ex:  # noqa: BLE001
    fail("package: import", str(ex))

# ---- 9. Live engine smoke run ---------------------------------------------
try:
    eng = imh.MatchHistoryEngine()  # in-memory, ELO
    a = eng.register_player("alice")
    b = eng.register_player("bob")
    res = eng.record_match(
        "pong",
        [imh.MatchResult(a.player_id, imh.MatchOutcome.WIN),
         imh.MatchResult(b.player_id, imh.MatchOutcome.LOSS)],
        season="s1",
    )
    require(res.match.match_id.startswith("mt_"), "smoke: match recorded")
    require(res.rating_deltas[a.player_id][1] > 1200, "smoke: winner rating up")
    lb = eng.leaderboard("pong", "s1", top=5)
    require(len(lb) == 2 and lb[0].member == a.player_id, "smoke: leaderboard ordered")
    eng.close()
except Exception as ex:  # noqa: BLE001
    fail("smoke: engine run", str(ex))

# ---- report ----------------------------------------------------------------
total = _checks_passed + _checks_failed
print(f"[run_test_scenarios] {_checks_passed}/{total} checks passed")
if _failures:
    for f in _failures:
        print("  - FAIL " + f)
    sys.exit(1)
print("[OK] all checks passed")
sys.exit(0)