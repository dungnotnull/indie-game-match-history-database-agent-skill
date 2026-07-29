# Contributing

Thank you for considering a contribution to `indie-game-match-history-database`.

## Development setup
```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1   # Windows PowerShell
pip install -e ".[dev]"
```

## Running tests
```bash
pytest -q
python tools/run_test_scenarios.py
python tools/test_knowledge_updater.py
```

## Code style
- Python 3.10+, fully type-hinted, no `Any` in public APIs.
- Functions and modules have docstrings; public symbols are exported via `__init__.py`.
- No dummy/commented-out code; production logic only.
- Keep the harness skill files (markdown) in sync with the engine package.

## Pull request checklist
- [ ] Tests pass (`pytest -q`)
- [ ] Structural validators pass (`python tools/run_test_scenarios.py`)
- [ ] New public API is documented in README + docstring
- [ ] CHANGELOG.md entry added under "Unreleased" or the new version

## Knowledge base contributions
Append candidate references to `SECOND-KNOWLEDGE-BRAIN.md` Section 7 only via
`tools/knowledge_updater.py` (dedup by SHA-256 of DOI/URL). Manual edits to
Sections 1-6 should be proposed via PR with at least one Tier 1-2 source.