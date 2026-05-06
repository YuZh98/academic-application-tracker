# Contributing to Academic Application Tracker

This is a personal job-search tool that the maintainer is also using
as a portfolio piece. Outside contributions are welcome but not
actively solicited; small fixes and clarifications are easier to land
than large features. Read [`DESIGN.md`](DESIGN.md) before proposing
architectural changes — it is the authoritative spec for the schema,
page contracts, cascade rules, and exports format.

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
- **Tests for new behaviour.** Follow the TDD red → green → chore
  rollup cadence (see [`GUIDELINES.md`](GUIDELINES.md) §11).

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
