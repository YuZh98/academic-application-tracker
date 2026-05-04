# exports.py
# Markdown export generators — DESIGN §7.
#
# Called by database.py after every write operation:
#   import exports as _exports; _exports.write_all()
#
# Import rules:
#   - May import: database, config, stdlib
#   - Must NOT import: streamlit
#   - Do NOT import database at module level — that creates a circular import.
#     Import database inside functions when needed.

import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

EXPORTS_DIR: Path = Path(__file__).parent / "exports"

# Em-dash glyph used to mark empty/NULL TEXT cells in the rendered
# markdown tables — single source of truth so the same character flows
# across every generator and matches the in-app `_safe_str_or_em` form.
_EM_DASH = "—"


def _safe_str_or_em(v: Any) -> str:
    """Coerce a SQLite/pandas TEXT cell to a markdown-safe string,
    rendering ``None`` / NaN / empty string as ``_EM_DASH`` so missing
    cells read as a single visible glyph in the rendered table.

    Mirrors the in-app ``_safe_str_or_em`` convention from the page
    layer; duplicated here because pages and exports must NOT share
    helpers (the page layer imports streamlit, which exports.py is
    forbidden from importing per DESIGN §2 layer rules)."""
    if v is None:
        return _EM_DASH
    if isinstance(v, float) and math.isnan(v):
        return _EM_DASH
    s = str(v)
    return s if s else _EM_DASH


def _md_escape_cell(s: str) -> str:
    """Escape characters that would break a markdown table row.

    Pipe (``|``) closes a cell early, and a literal newline splits the
    row across multiple table lines. Both are unlikely in practice
    (position names rarely contain them) but the safety net is cheap
    and keeps a future user-typed cell from corrupting the table."""
    return s.replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def write_all() -> None:
    """Write all three markdown export files. Called after every database write.

    DESIGN §7 exports.py contract #1 + §9.5: errors are logged but
    never propagate past this function's boundary. The DB write that
    triggered this call has already succeeded; the user must see
    "Saved", not a traceback. Each `write_*` runs inside its own
    try/except so a single broken writer does not stop the others —
    matches §9.5's "A failure in ANY write_*" wording.

    `EXPORTS_DIR.mkdir` is wrapped separately and short-circuits the
    rest of the function on failure: nothing else can succeed without
    the destination directory.
    """
    try:
        EXPORTS_DIR.mkdir(exist_ok=True)
    except Exception:
        logger.exception(
            "exports.write_all(): EXPORTS_DIR.mkdir failed; "
            "skipping markdown regeneration this cycle"
        )
        return

    # Iterate by slot NAME (not by captured function reference) so the
    # log message always reads as the intended writer slot — useful
    # because monkeypatched stand-ins (test fixtures) carry their own
    # `__name__` and would otherwise leak into the operator-facing log.
    for name in ("write_opportunities", "write_progress", "write_recommenders"):
        try:
            globals()[name]()
        except Exception:
            logger.exception(
                f"exports.write_all(): {name} failed; "
                "subsequent writers will still run"
            )


def write_opportunities() -> None:
    """Generate ``exports/OPPORTUNITIES.md`` from the positions table.

    DESIGN §7 contract — markdown backup of the positions table.
    Column contract (locked by tests in
    ``tests/test_exports.py::TestWriteOpportunities``):

        | Position | Institute | Field | Deadline | Priority | Status | Created | Updated |

    Cell shapes:
      - Empty/NULL TEXT cells → ``—`` (em-dash) via ``_safe_str_or_em``.
      - Date / datetime cells → pass-through ISO TEXT (the schema stores
        these as ISO already, so no reformatting).
      - Status → raw bracketed sentinel (``[SAVED]`` / ``[APPLIED]`` / …)
        NOT ``STATUS_LABELS`` translation. Markdown is a backup format,
        not a UI surface — round-trippable / greppable raw form trumps
        UI-friendly translation.

    Sort order: ``deadline_date ASC NULLS LAST, position_id ASC`` —
    inherited from ``database.get_all_positions()`` (deadline ASC NULLS
    LAST), with the position_id tiebreaker added here so equal-deadline
    rows have a stable order across rerenders. Mirror of the
    ``database.get_applications_table()`` precedent.

    Idempotent — two calls with the same DB state produce byte-identical
    output (no timestamps embedded in the body, no dict-ordering drift).
    Load-bearing for DESIGN §7 contract #2 ("stable markdown format
    committed to version control") — non-deterministic output would
    create spurious git diffs on every save.

    Deferred ``database`` import inside the function body avoids the
    ``database → exports → database`` circular import at module load."""
    import database  # deferred — see module docstring + DESIGN §7

    EXPORTS_DIR.mkdir(exist_ok=True)

    df = database.get_all_positions()
    # get_all_positions sorts deadline_date ASC NULLS LAST; add the
    # position_id ASC tiebreaker so equal-deadline rows have a stable
    # order across reruns (mirror of get_applications_table — pinned by
    # the test_sort_order_by_deadline_asc_nulls_last test). pandas
    # sort_values supports na_position='last' on the deadline column
    # without disturbing the existing ordering for non-NULL values.
    if not df.empty:
        df = df.sort_values(
            by=["deadline_date", "id"],
            ascending=[True, True],
            na_position="last",
            kind="stable",
        ).reset_index(drop=True)

    header = (
        "| Position | Institute | Field | Deadline "
        "| Priority | Status | Created | Updated |"
    )
    separator = "| --- | --- | --- | --- | --- | --- | --- | --- |"

    lines: list[str] = [header, separator]
    for _, row in df.iterrows():
        cells = [
            _safe_str_or_em(row["position_name"]),
            _safe_str_or_em(row["institute"]),
            _safe_str_or_em(row["field"]),
            _safe_str_or_em(row["deadline_date"]),
            _safe_str_or_em(row["priority"]),
            _safe_str_or_em(row["status"]),
            _safe_str_or_em(row["created_at"]),
            _safe_str_or_em(row["updated_at"]),
        ]
        cells = [_md_escape_cell(c) for c in cells]
        lines.append("| " + " | ".join(cells) + " |")

    out_path = EXPORTS_DIR / "OPPORTUNITIES.md"
    # Trailing newline for POSIX file convention; the data_rows test
    # filters by leading-pipe so the trailing blank line is harmless.
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_progress() -> None:
    """Generate exports/PROGRESS.md from positions + applications tables. (Phase 6)"""
    pass


def write_recommenders() -> None:
    """Generate exports/RECOMMENDERS.md from the recommenders table. (Phase 6)"""
    pass
