# Contributing to Academic Application Tracker

This is a personal job-search tool that the maintainer is also using
as a portfolio piece. Outside contributions are welcome but not
actively solicited; small fixes and clarifications are easier to land
than large features. Read [`DESIGN.md`](DESIGN.md) before proposing
architectural changes — it is the authoritative spec for the schema,
page contracts, cascade rules, and exports format.

## Where to start

- **Understanding the architecture:** Read [`DESIGN.md`](DESIGN.md) for the schema, page contracts, cascade rules, and export format.
- **Coding conventions:** Read [`GUIDELINES.md`](GUIDELINES.md) — naming, patterns, test structure, and doc conventions. Scan the checklist in §11 before every PR.
- **What's been built:** [`CHANGELOG.md`](CHANGELOG.md) has per-release entries; [`docs/dev-notes/`](docs/dev-notes/) has deep-dives on Streamlit gotchas and the git workflow.

## Dev setup

```bash
git clone https://github.com/YuZh98/academic-application-tracker.git
cd academic-application-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

## Commit + branch conventions

- **Conventional Commits.** `<type>(<scope>): <subject>` — types:
  `feat`, `fix`, `test`, `chore`, `docs`, `refactor`.
- **Branch naming.** `<type>/<short-description>` (e.g.
  `fix/deadline-glyph-overflow`).
- **Co-author lines welcome.** Add a `Co-Authored-By: Name <email>`
  trailer in the commit message body, or amend with
  `git commit --amend` to add one to the most recent commit.
- See [`GUIDELINES.md`](GUIDELINES.md) §11 for the full TDD cadence
  (`test:` → `feat:` → `chore:`) and [`GUIDELINES.md`](GUIDELINES.md)
  §14 for documentation conventions.

## Pull requests

- **Target:** `main`.
- **CI gates.** All seven must pass before review: ruff · pyright ·
  pytest · deprecation-strict pytest · status-literal grep ·
  isolation gate · CI matrix on Python 3.11–3.14.
- **Changelog.** Add a `[Unreleased]` entry to
  [`CHANGELOG.md`](CHANGELOG.md) with the PR number and commit ref.

  A changelog entry looks like this:

  ````markdown
  ### Added
  - Add export timestamp to OPPORTUNITIES.md header (#84)

  ### Changed
  - Rename `priority_score` → `urgency_score` in Upcoming table column (#85)

  ### Fixed
  - Fix crash when `deadline_date` is NULL and urgency column renders (#86)
  ````

  One line per change, imperative mood, ends with PR number. Subsections
  only appear when needed (don't add an empty `### Fixed` block). Changes
  with no user-visible effect (pure refactors, test-only commits) don't
  get entries.

- **Tests for new behaviour.** Follow the TDD red → green → chore
  rollup cadence (see [`GUIDELINES.md`](GUIDELINES.md) §11).

  **Test harness:** Page-level integration tests use Streamlit's official [`AppTest`](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) harness — each test boots a real page file against a temp SQLite database. Unit tests for `database.py` and `exports.py` use a `db` fixture in `tests/conftest.py` that redirects `DB_PATH` and `EXPORTS_DIR` to a per-test temp directory. Use `database.add_position()` and similar helpers to seed data in tests — never raw SQL.

## Issue reporting

Use the templates in [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/)
if present, otherwise open a plain GitHub issue. Security
vulnerabilities follow the private disclosure path in
[`SECURITY.md`](SECURITY.md) (GitHub private advisory) — do not file
them as public issues.

## Code review

Every PR has a pre-merge review document under [`reviews/`](reviews/).
Outside contributors are not expected to write one; the maintainer
will produce it before merge.

## License

By contributing, you agree your contributions will be licensed under
the MIT license per [`LICENSE`](LICENSE).
