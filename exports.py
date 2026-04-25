# exports.py
# Markdown export functions — stub for Phase 2. Full implementation in Phase 6.
#
# Called by database.py after every write operation:
#   import exports as _exports; _exports.write_all()
#
# Import rules:
#   - May import: database, config, stdlib
#   - Must NOT import: streamlit
#   - Do NOT import database at module level — that creates a circular import.
#     Import database inside functions when needed (Phase 6).

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXPORTS_DIR: Path = Path(__file__).parent / "exports"


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
    """Generate exports/OPPORTUNITIES.md from the positions table. (Phase 6)"""
    pass


def write_progress() -> None:
    """Generate exports/PROGRESS.md from positions + applications tables. (Phase 6)"""
    pass


def write_recommenders() -> None:
    """Generate exports/RECOMMENDERS.md from the recommenders table. (Phase 6)"""
    pass
