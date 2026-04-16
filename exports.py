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

from pathlib import Path

EXPORTS_DIR: Path = Path(__file__).parent / "exports"


def write_all() -> None:
    """Write all three markdown export files. Called after every database write."""
    EXPORTS_DIR.mkdir(exist_ok=True)
    write_opportunities()
    write_progress()
    write_recommenders()


def write_opportunities() -> None:
    """Generate exports/OPPORTUNITIES.md from the positions table. (Phase 6)"""
    pass


def write_progress() -> None:
    """Generate exports/PROGRESS.md from positions + applications tables. (Phase 6)"""
    pass


def write_recommenders() -> None:
    """Generate exports/RECOMMENDERS.md from the recommenders table. (Phase 6)"""
    pass
