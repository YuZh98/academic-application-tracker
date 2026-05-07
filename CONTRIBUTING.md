# Contributing

Contributions are welcome — bug fixes, new features, documentation improvements, and test coverage. This guide gets you from clone to merged PR.

---

## Before you start

| Doc | What it covers |
|-----|---------------|
| [`DESIGN.md`](DESIGN.md) | Schema, page contracts, cascade rules, export format — read before proposing architectural changes |
| [`GUIDELINES.md`](GUIDELINES.md) | Coding conventions, naming, test structure, TDD cadence |
| [`CHANGELOG.md`](CHANGELOG.md) | Per-release development narrative |

---

## Dev setup

```bash
git clone https://github.com/YuZh98/academic-application-tracker.git
cd academic-application-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

Run the test suite to confirm everything works:

```bash
pytest
```

---

## Branch and commit conventions

- **Branch naming:** `<type>/<short-description>` (e.g. `fix/deadline-glyph-overflow`)
- **Conventional Commits:** `<type>(<scope>): <subject>` — types: `feat`, `fix`, `test`, `chore`, `docs`, `refactor`
- **Co-author lines welcome** — add `Co-Authored-By: Name <email>` in the commit body

---

## Pull requests

**Target branch:** `main`

**CI must pass.** Every PR runs:
- ruff lint (zero warnings)
- pyright strict-basic (zero errors)
- pytest (two passes: normal + deprecation-as-error)
- Status-literal grep (no hardcoded status strings in page code)

**Include tests.** Follow the TDD cadence: write a failing test → make it pass → clean up. Page-level tests use Streamlit's [`AppTest`](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) harness; unit tests use the `db` fixture in `tests/conftest.py`. Seed data with `database.add_position()` and similar helpers — never raw SQL in tests.

**Add a changelog entry.** Add a line under `[Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md):

```markdown
### Added
- Add export timestamp to OPPORTUNITIES.md header (#84)
```

One line per change, imperative mood, ends with PR number. Pure refactors and test-only changes don't need entries.

---

## Issue reporting

Use the templates in [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) if present, otherwise open a plain GitHub issue. Security vulnerabilities should follow the private disclosure path in [`SECURITY.md`](SECURITY.md) — do not file them as public issues.

---

## License

By contributing, you agree your contributions will be licensed under the [MIT License](LICENSE).
