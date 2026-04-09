## ADDED Requirements

### Requirement: Migration directory contains only conforming files

The `scripts/migrations/` directory SHALL contain only migration files matching the `YYYYMMDD_NNN_description.py` naming convention, plus `__init__.py` and test fixtures. Files that do not match the convention and are not `__init__.py` or prefixed with `test_` SHALL be removed to prevent confusion about which migrations are active.

#### Scenario: Legacy non-conforming migration file removed

- **WHEN** a developer lists files in `scripts/migrations/`
- **THEN** every `.py` file other than `__init__.py` and `test_*.py` SHALL match the pattern `YYYYMMDD_NNN_*.py`
- **THEN** `role_to_permissions.py` SHALL NOT exist in the directory
