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

import config

logger = logging.getLogger(__name__)

EXPORTS_DIR: Path = Path(__file__).parent / "exports"


def _safe_str_or_em(v: Any) -> str:
    """Coerce a SQLite/pandas TEXT cell to a markdown-safe string,
    rendering ``None`` / NaN / empty string as ``config.EM_DASH`` so missing
    cells read as a single visible glyph in the rendered table.

    Mirrors the in-app ``_safe_str_or_em`` convention from the page
    layer; duplicated here because pages and exports must NOT share
    helpers (the page layer imports streamlit, which exports.py is
    forbidden from importing per DESIGN §2 layer rules)."""
    if v is None:
        return config.EM_DASH
    if isinstance(v, float) and math.isnan(v):
        return config.EM_DASH
    s = str(v)
    return s if s else config.EM_DASH


def _md_escape_cell(s: str) -> str:
    """Escape characters that would break a markdown table row.

    Pipe (``|``) closes a cell early, and a literal newline splits the
    row across multiple table lines. Both are unlikely in practice
    (position names rarely contain them) but the safety net is cheap
    and keeps a future user-typed cell from corrupting the table."""
    return s.replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def _format_confirmation(received: Any, iso_date: Any) -> str:
    """Render the (confirmation_received, confirmation_date) pair as a
    single cell (DESIGN §8.3).

    Tri-state cell:
      received=0 / NULL / NaN  → ``config.EM_DASH``
      received=1 + iso_date    → ``"✓ {iso_date}"``
      received=1 + NULL date   → ``"✓ (no date)"``

    Mirrors the Applications page's `_format_confirmation` shape
    semantically but uses ISO date pass-through (instead of the
    page's "Mon D" form) so the export round-trips cleanly. Pages
    and exports must NOT share helpers (DESIGN §2 layer rules — pages
    import streamlit, exports cannot)."""
    if received is None or (isinstance(received, float) and math.isnan(received)):
        return config.EM_DASH
    try:
        if not int(received):
            return config.EM_DASH
    except (TypeError, ValueError):
        return config.EM_DASH
    iso_str = (
        ""
        if (iso_date is None or (isinstance(iso_date, float) and math.isnan(iso_date)))
        else str(iso_date)
    )
    if not iso_str:
        return "✓ (no date)"
    return f"✓ {iso_str}"


def _format_confirmed(v: Any) -> str:
    """Tri-state Confirmed cell: NULL → '—', 0 → 'No', 1 → 'Yes'.

    Local mirror of ``pages/3_Recommenders.py::_format_confirmed`` —
    DESIGN §2 layer rules forbid pages and exports from sharing helpers
    (the page module imports ``streamlit`` which ``exports.py`` cannot
    transitively pull in). Identical semantics, just lives here so the
    layer rule holds."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return config.EM_DASH
    try:
        i = int(v)
    except (TypeError, ValueError):
        return config.EM_DASH
    return "Yes" if i == 1 else "No"


def _format_interviews_summary(scheduled_dates: list[Any]) -> str:
    """Summarize a position's interviews into a single cell.

    Format: ``"{count} (last: {YYYY-MM-DD})"`` where ``last`` = max
    non-NULL scheduled_date across the position's interviews.

    Edge cases:
      0 interviews → ``config.EM_DASH``
      ≥1 interviews with at least one non-NULL date → ``"N (last: ISO)"``
      ≥1 interviews + every scheduled_date NULL → ``"N (no dates)"``

    The "last = max(scheduled_date)" choice is round-trippable, idempotent,
    and reads coherently in both past + future contexts. See
    `tests/test_exports.py` module-level comment for the design
    rationale + considered alternatives."""
    n = len(scheduled_dates)
    if n == 0:
        return config.EM_DASH
    iso_dates: list[str] = []
    for v in scheduled_dates:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        s = str(v)
        if s:
            iso_dates.append(s)
    if not iso_dates:
        return f"{n} (no dates)"
    return f"{n} (last: {max(iso_dates)})"


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


    for name in ("write_opportunities", "write_progress", "write_recommenders"):
        try:
            globals()[name]()
        except Exception:
            logger.exception(
                f"exports.write_all(): {name} failed; subsequent writers will still run"
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
    if not df.empty:
        df = df.sort_values(
            by=["deadline_date", "id"],
            ascending=[True, True],
            na_position="last",
            kind="stable",
        ).reset_index(drop=True)

    header = "| Position | Institute | Field | Deadline | Priority | Status | Created | Updated |"
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
    """Generate ``exports/PROGRESS.md`` from positions × applications ×
    interviews.

    DESIGN §7 contract — markdown backup of the application-progression
    join. Column contract (locked by tests in
    ``tests/test_exports.py::TestWriteProgress``):

        | Position | Institute | Status | Applied | Confirmation | Response | Result | Interviews |

    Cell shapes (mirror ``write_opportunities`` for cross-export
    cohesion):
      - Empty/NULL TEXT cells → ``—`` (em-dash) via ``_safe_str_or_em``.
      - Date cells → pass-through ISO TEXT.
      - Status → raw bracketed sentinel (``[SAVED]`` / ``[APPLIED]`` / …)
        NOT ``STATUS_LABELS`` translation.
      - Confirmation cell → ``_format_confirmation`` tri-state
        (``—`` / ``✓ {ISO}`` / ``✓ (no date)``).
      - Interviews cell → ``_format_interviews_summary``
        (``—`` / ``{N} (last: {ISO})`` / ``{N} (no dates)``).

    Sort order: ``deadline_date ASC NULLS LAST, position_id ASC`` —
    inherited from ``database.get_applications_table()`` (which already
    sorts in SQL) and re-applied here via pandas with a stable kind
    so a future change to the upstream reader's ORDER BY clause does
    not silently break the export's row order.

    Idempotent — no timestamps embedded in the body, no dict-ordering
    drift. Two calls with the same DB state produce byte-identical
    output (DESIGN §7 contract #2).

    Deferred ``database`` import inside the function body avoids the
    ``database → exports → database`` circular import at module load."""
    import database  # deferred — see module docstring + DESIGN §7

    EXPORTS_DIR.mkdir(exist_ok=True)

    df = database.get_applications_table()
    if not df.empty:
        df = df.sort_values(
            by=["deadline_date", "position_id"],
            ascending=[True, True],
            na_position="last",
            kind="stable",
        ).reset_index(drop=True)

    header = (
        "| Position | Institute | Status | Applied "
        "| Confirmation | Response | Result | Interviews |"
    )
    separator = "| --- | --- | --- | --- | --- | --- | --- | --- |"

    lines: list[str] = [header, separator]
    for _, row in df.iterrows():
        pid_raw: Any = row["position_id"]
        position_id = int(pid_raw)
        interviews_df = database.get_interviews(position_id)
        scheduled_dates = list(interviews_df["scheduled_date"]) if not interviews_df.empty else []

        cells = [
            _safe_str_or_em(row["position_name"]),
            _safe_str_or_em(row["institute"]),
            _safe_str_or_em(row["status"]),
            _safe_str_or_em(row["applied_date"]),
            _format_confirmation(row["confirmation_received"], row["confirmation_date"]),
            _safe_str_or_em(row["response_type"]),
            _safe_str_or_em(row["result"]),
            _format_interviews_summary(scheduled_dates),
        ]
        cells = [_md_escape_cell(c) for c in cells]
        lines.append("| " + " | ".join(cells) + " |")

    out_path = EXPORTS_DIR / "PROGRESS.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_recommenders() -> None:
    """Generate ``exports/RECOMMENDERS.md`` from recommenders × positions.

    DESIGN §7 contract — markdown backup of every recommender × position
    pair (one row per letter owed). Column contract (locked by tests in
    ``tests/test_exports.py::TestWriteRecommenders``):

        | Recommender | Relationship | Position | Institute | Asked | Confirmed | Submitted | Reminder |

    ``notes`` is intentionally NOT exported — recommender notes are
    typically free-form prose that's awkward in a markdown table cell.
    The in-app UI carries them; the export summarises.

    Cell shapes (mirror T1 + T2 conventions for cross-export cohesion):
      - ``_safe_str_or_em`` for missing TEXT cells → em-dash.
      - Date cells (Asked, Submitted) pass-through ISO TEXT.
      - ``_format_confirmed`` for the Confirmed tri-state
        (``—`` / ``No`` / ``Yes``) — local mirror of the
        ``pages/3_Recommenders.py`` helper per the DESIGN §2 layer rule.
      - ``_format_confirmation`` for the Reminder tri-state
        (``—`` / ``✓ {ISO}`` / ``✓ (no date)``) — REUSED because the
        ``(reminder_sent, reminder_sent_date)`` pair has the same
        ``(flag, date)`` shape as the Applications-page Confirmation
        pattern (DESIGN §8.3).
      - ``_md_escape_cell`` on every cell.
      - No status sentinel — recommenders don't carry pipeline status.

    Sort order: ``recommender_name ASC, deadline_date ASC NULLS LAST,
    id ASC``.

      - Primary ``recommender_name`` groups one person's owed letters
        together (the natural reading mode for the file).
      - Secondary ``deadline_date`` orders multiple positions for the
        same recommender by upcoming-ness.
      - Tertiary ``id`` is the deterministic tiebreaker.

    ``database.get_all_recommenders()`` SQL covers the first + third
    keys (``recommender_name ASC, id ASC``); ``deadline_date`` is
    merged in from ``database.get_all_positions()`` here in pandas
    (the deadline sort key is merged here in pandas to avoid a new joined query in database.py).
    The ``pandas.sort_values(... kind='stable')`` re-sort on top of
    that defends against a future upstream change to either reader's
    SQL ORDER BY clause.

    Idempotent — no timestamps in body, no dict-ordering drift. Two
    calls with the same DB state produce byte-identical output
    (DESIGN §7 contract #2).

    Deferred ``database`` import inside the function body avoids the
    ``database → exports → database`` circular import at module load."""
    import database  # deferred — see module docstring + DESIGN §7

    EXPORTS_DIR.mkdir(exist_ok=True)

    df = database.get_all_recommenders()
    if not df.empty:
        # Merge deadline_date from positions for the secondary sort key.
        # Trim positions to (id, deadline_date) so the merge doesn't
        # pollute the row with stray columns; rename id → position_id
        # to align with df's join column.
        positions = database.get_all_positions()[["id", "deadline_date"]].rename(  # type: ignore[call-overload]
            columns={"id": "position_id", "deadline_date": "_pos_deadline"},
        )
        df = df.merge(positions, on="position_id", how="left")
        df = df.sort_values(
            by=["recommender_name", "_pos_deadline", "id"],
            ascending=[True, True, True],
            na_position="last",
            kind="stable",
        ).reset_index(drop=True)

    header = (
        "| Recommender | Relationship | Position | Institute "
        "| Asked | Confirmed | Submitted | Reminder |"
    )
    separator = "| --- | --- | --- | --- | --- | --- | --- | --- |"

    lines: list[str] = [header, separator]
    for _, row in df.iterrows():
        cells = [
            _safe_str_or_em(row["recommender_name"]),
            _safe_str_or_em(row["relationship"]),
            _safe_str_or_em(row["position_name"]),
            _safe_str_or_em(row["institute"]),
            _safe_str_or_em(row["asked_date"]),
            _format_confirmed(row["confirmed"]),
            _safe_str_or_em(row["submitted_date"]),
            _format_confirmation(row["reminder_sent"], row["reminder_sent_date"]),
        ]
        cells = [_md_escape_cell(c) for c in cells]
        lines.append("| " + " | ".join(cells) + " |")

    out_path = EXPORTS_DIR / "RECOMMENDERS.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
