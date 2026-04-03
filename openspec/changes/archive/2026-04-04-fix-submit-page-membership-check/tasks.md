## 1. Regression Coverage

- [x] [P] 1.1 Add member and non-member page tests in `tests/test_pages.py` for the requirement "Student submit page validates class membership before rendering"
- [x] [P] 1.2 Add a focused regression test in `tests/test_dashboard_and_page_bugs.py` that proves non-members receive HTTP 403 instead of class-specific page content

## 2. Route Hardening

- [x] 2.1 Implement "Student submit page validates class membership before rendering" in `src/tasks/submissions/router.py` by checking `ClassMembership` before any template lookup
- [x] 2.2 Ensure the non-member path exits before loading today's template or rejected-submission state, while enrolled students still receive the existing empty-state behavior
