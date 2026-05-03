#!/usr/bin/env bash
# scripts/release.sh — slice CHANGELOG [Unreleased] into a versioned section.
#
# Usage:
#   scripts/release.sh vX.Y.Z "Topical title"
#
# Example:
#   scripts/release.sh v0.6.0 "Phase 5 close — Applications + Recommenders"
#
# What it does:
#   - Validates the version arg (vMAJOR.MINOR.PATCH)
#   - Refuses if the version already exists in CHANGELOG.md
#   - Refuses if [Unreleased] has no entries (### or `- `) under it
#   - Inserts a new `## [vX.Y.Z] — YYYY-MM-DD — <title>` header directly
#     under [Unreleased], so existing entries become the new version's body
#   - Leaves [Unreleased] empty (its content moved into the new version)
#
# What it does NOT do (intentional — gives you a chance to review):
#   - git add / git commit
#   - git tag
#   - git push
#
# After running, review `git diff CHANGELOG.md`, then run the suggested
# follow-up commands the script prints.

set -euo pipefail

VERSION="${1:-}"
TITLE="${2:-}"

if [[ -z "$VERSION" || -z "$TITLE" ]]; then
  cat <<USAGE >&2
Usage: $0 vX.Y.Z "Topical title"

Example:
  $0 v0.6.0 "Phase 5 close — Applications + Recommenders"
USAGE
  exit 2
fi

if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERROR: version must match vMAJOR.MINOR.PATCH (got: $VERSION)" >&2
  exit 2
fi

# Run from repo root (the directory containing CHANGELOG.md).
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f CHANGELOG.md ]]; then
  echo "ERROR: CHANGELOG.md not found at $REPO_ROOT" >&2
  exit 1
fi

if grep -qE "^## \[${VERSION//./\\.}\]" CHANGELOG.md; then
  echo "ERROR: $VERSION already exists as a section header in CHANGELOG.md" >&2
  exit 3
fi

# Extract the [Unreleased] body — everything from `## [Unreleased]` up to
# the next `## [` line. Reject if it has no real entries.
unreleased_body="$(awk '
  /^## \[Unreleased\]/ { flag = 1; next }
  /^## \[/             { flag = 0 }
  flag                 { print }
' CHANGELOG.md)"

if ! grep -qE '^(### |- )' <<<"$unreleased_body"; then
  echo "ERROR: [Unreleased] has no entries to release." >&2
  echo "       Add at least one '### Added' subsection or '- bullet' first." >&2
  exit 4
fi

DATE="$(date -u +%Y-%m-%d)"
NEW_HEADER="## [${VERSION}] — ${DATE} — ${TITLE}"

# Insert the new version header directly under `## [Unreleased]`. Existing
# entries below [Unreleased] become the body of the new version. Use a
# tempfile + atomic mv to avoid partial writes on interrupt.
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

awk -v new_header="$NEW_HEADER" '
  /^## \[Unreleased\]/ && !done {
    print
    print ""
    print new_header
    done = 1
    next
  }
  { print }
' CHANGELOG.md > "$TMP"

mv "$TMP" CHANGELOG.md
trap - EXIT

cat <<DONE
✓ Sliced [Unreleased] into ${VERSION} (${DATE})
  Title: ${TITLE}

Next steps:
  1. Review the diff:   git diff CHANGELOG.md
  2. Stage + commit:    git add CHANGELOG.md && git commit -m "docs(changelog): cut ${VERSION}"
  3. Tag:               git tag -a ${VERSION} -m "${TITLE}"
  4. Push commit + tag: git push && git push origin ${VERSION}
DONE
