# Tasks

- [x] Implement **Prize listing enforces class-scoped authorization**: in `list_prizes` load the class (404 if absent), manager → all prizes, member → visible only, non-member → 403 (`src/gamification/prizes/router.py`)
- [x] Regression tests for **Prize listing enforces class-scoped authorization**: member sees visible, non-member → 403, manager sees all (`tests/test_prizes.py`)
- [x] Full test suite green — 615 passed, 2 skipped (`.venv/bin/python -m pytest`)
