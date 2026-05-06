## Summary

<!-- 1-3 bullets: what this PR does and why. Link the issue or roadmap entry it addresses. -->

-

## Changes

<!-- File-by-file or area-by-area summary. Optional for trivial PRs. -->

-

## Test plan

<!-- How you verified the change. Tick the boxes that apply. -->

- [ ] `ruff check .` clean
- [ ] `pyright .` 0 errors / 0 warnings
- [ ] `pytest tests/ -q` — full suite passes (883 + 1 xfailed minimum)
- [ ] `pytest -W error::DeprecationWarning tests/ -q` — same
- [ ] Status-literal grep clean (per `GUIDELINES §6`)
- [ ] `git status --porcelain exports/` empty (isolation gate)
- [ ] CI matrix runs all four versions (3.11 / 3.12 / 3.13 / 3.14) on push
- [ ] Manual UI check (if pages/ touched)

## CHANGELOG

<!-- Add an entry under `[Unreleased]` per `GUIDELINES §14.4` with PR number + commit ref. Or check this box if N/A. -->

- [ ] Added entry to `CHANGELOG.md` `[Unreleased]`
- [ ] Or: not user-facing — N/A (CI / dev-tooling / refactor with no behaviour change)

## Notes for reviewer

<!-- Anything reviewer should know: gotchas, design decisions, test-coverage gaps, follow-ups deferred. -->

-

---

🤖 If this PR was generated with Claude Code, the `Co-Authored-By:` trailer should appear in the squash-merge commit message.
