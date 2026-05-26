"""Build the UX field-study PDF report + matplotlib charts.

Run:  .venv/bin/python scripts/build_ux_report.py

Outputs:
  docs/ux-research/figs/*.png    six charts
  docs/ux-research/UX_Field_Study_Report_2026-05-22.pdf
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import matplotlib
import numpy as np

# Ensure the repo root is importable so `import config` works regardless of
# the invocation directory (CLI users typically run from repo root, but the
# script is also called from CI in other cwds).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import config  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs" / "ux-research"
FIG_DIR = OUT_DIR / "figs"
FIG_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = OUT_DIR / "UX_Field_Study_Report_2026-05-22.pdf"

# ── Editorial-brutalist palette (matches ui.py tokens) ───────────────────────

PAPER = "#F4EDE0"
INK = "#0A0A0A"
VERMILION = config.ACCENT_VERMILION
COBALT = "#2541B2"
CITRON = "#F4D35E"
RULE = "#5A5752"
SAGE = "#5C8A6B"
OXBLOOD = "#7A1F2B"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman"],
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "axes.edgecolor": INK,
        "axes.facecolor": PAPER,
        "figure.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "savefig.dpi": 150,
        "axes.grid": True,
        "grid.color": RULE,
        "grid.alpha": 0.18,
        "grid.linewidth": 0.5,
    }
)


# ── Chart 1: Persona radar ────────────────────────────────────────────────────

def chart_persona_radar() -> Path:
    """Radar of five normalized axes per persona."""
    axes_labels = [
        "Tech\ncomfort",
        "Positions\ntracked",
        "Recommenders\nload",
        "Mobile / tablet\nusage",
        "Churn\nrisk",
    ]
    # 0..1 normalized
    p1 = [0.85, 0.80, 0.80, 0.60, 0.70]  # Aisha (life-sci postdoc)
    p2 = [0.40, 0.45, 1.00, 0.05, 0.65]  # James (humanities TT)
    p3 = [1.00, 1.00, 0.30, 0.05, 0.35]  # Wei (CS mixed)

    angles = np.linspace(0, 2 * np.pi, len(axes_labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7.2, 5.0), subplot_kw=dict(polar=True))
    ax.set_facecolor(PAPER)

    for vals, color, label in (
        (p1, VERMILION, "P1 — Aisha (life-sci postdoc)"),
        (p2, COBALT, "P2 — James (humanities TT)"),
        (p3, CITRON, "P3 — Wei (CS mixed)"),
    ):
        v = vals + vals[:1]
        ax.plot(angles, v, color=color, linewidth=2, label=label)
        ax.fill(angles, v, color=color, alpha=0.18)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(axes_labels, fontsize=9)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=7, color=RULE)
    ax.set_ylim(0, 1)
    ax.set_title("Persona profile across five axes (normalized 0–1)", pad=18)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.05), fontsize=8, frameon=False)
    fig.tight_layout()
    p = FIG_DIR / "01_persona_radar.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# ── Chart 2: Friction heatmap ────────────────────────────────────────────────

def chart_friction_heatmap() -> Path:
    """Friction theme × persona, cell = composite severity score (0–3).
    0=N/A, 1=low, 2=medium, 3=high/catastrophic."""
    themes = [
        "Recommender entity per-position",
        "No bulk operations",
        "Vocabulary hardcoded in config.py",
        "Schema-UI gap (positions table)",
        "Cascade asymmetry (R2-delete bug)",
        "No materials versioning / attachments",
        "Threshold tuning requires Python edit",
        "Recommender email column missing",
        "No responsive layout (tablet broken)",
        "No keyboard shortcuts",
        "Pipeline doesn't fit non-postdoc cycles",
        "Reminder mailto per-position not per-recommender",
        "Dashboard date column ambiguous (no year)",
        "No in-app backup affordance",
        "init_db on every page load",
    ]
    personas = ["P1 Aisha", "P2 James", "P3 Wei"]
    data = np.array(
        [
            [3, 3, 0],  # recommender entity
            [3, 3, 2],  # bulk ops
            [2, 2, 2],  # vocab hardcoded
            [3, 1, 1],  # schema-UI gap
            [0, 0, 3],  # R2-delete asymmetry
            [1, 3, 1],  # materials versioning
            [1, 2, 1],  # threshold tuning
            [3, 1, 0],  # recommender email
            [3, 0, 0],  # responsive layout
            [0, 1, 2],  # keyboard shortcuts
            [0, 2, 3],  # pipeline non-postdoc
            [1, 2, 0],  # reminder mailto grouping
            [2, 1, 0],  # date column no year
            [1, 3, 0],  # no backup
            [0, 0, 1],  # init_db latency
        ]
    )

    fig, ax = plt.subplots(figsize=(7.2, 6.8))
    ax.set_facecolor(PAPER)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "vermilion_band", ["#FFFFFF", "#FCE4DD", VERMILION, OXBLOOD]
    )
    im = ax.imshow(data, cmap=cmap, vmin=0, vmax=3, aspect="auto")

    ax.set_xticks(range(len(personas)))
    ax.set_xticklabels(personas, fontsize=9)
    ax.set_yticks(range(len(themes)))
    ax.set_yticklabels(themes, fontsize=8)
    ax.set_xlabel("Persona")
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False)
    ax.xaxis.set_label_position("top")

    for i in range(len(themes)):
        for j in range(len(personas)):
            v = data[i, j]
            label = {0: "—", 1: "L", 2: "M", 3: "H"}[v]
            txt_color = "white" if v >= 2 else INK
            ax.text(j, i, label, ha="center", va="center", fontsize=9, color=txt_color)

    # Legend
    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3], shrink=0.55)
    cbar.ax.set_yticklabels(["N/A", "Low", "Medium", "High"], fontsize=8)
    ax.set_title("Friction severity by persona  (15 themes × 3 personas)", pad=12)
    ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 15, 1), minor=True)
    ax.grid(which="minor", color=RULE, alpha=0.25, linewidth=0.4)
    ax.tick_params(which="minor", length=0)
    fig.tight_layout()
    p = FIG_DIR / "02_friction_heatmap.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# ── Chart 3: Churn-risk timeline ─────────────────────────────────────────────

def chart_churn_timeline() -> Path:
    """Per-week trust/usage index per persona over 12 weeks. Annotated
    near-quit moments."""
    weeks = np.arange(1, 13)
    # Trust index 0..1. Personas start high, dip at known events.
    p1 = np.array(
        [0.95, 0.90, 0.80, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.50, 0.45, 0.50]
    )
    p2 = np.array(
        [0.92, 0.80, 0.70, 0.60, 0.58, 0.55, 0.55, 0.50, 0.45, 0.55, 0.55, 0.55]
    )
    p3 = np.array(
        [0.90, 0.78, 0.65, 0.70, 0.75, 0.78, 0.75, 0.70, 0.80, 0.85, 0.88, 0.90]
    )

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.set_facecolor(PAPER)
    for vals, color, label, marker in (
        (p1, VERMILION, "P1 Aisha", "o"),
        (p2, COBALT, "P2 James", "s"),
        (p3, CITRON, "P3 Wei", "^"),
    ):
        ax.plot(weeks, vals, color=color, linewidth=2, marker=marker, label=label, markersize=5)

    # Near-quit annotations
    ax.annotate(
        "P1 near-quit:\nrecommender entry tax",
        xy=(2, p1[1]),
        xytext=(2.2, 0.40),
        fontsize=7.5,
        color=VERMILION,
        arrowprops=dict(arrowstyle="->", color=VERMILION, lw=0.8),
    )
    ax.annotate(
        "P2 near-quit:\nDay 1 recommender tax",
        xy=(1, p2[0]),
        xytext=(0.5, 0.38),
        fontsize=7.5,
        color=COBALT,
        arrowprops=dict(arrowstyle="->", color=COBALT, lw=0.8),
    )
    ax.annotate(
        "P3 near-fork:\nindustry vocab",
        xy=(4, p3[3]),
        xytext=(4.0, 0.92),
        fontsize=7.5,
        color="#8a6d00",
        arrowprops=dict(arrowstyle="->", color="#8a6d00", lw=0.8),
    )
    ax.annotate(
        "P1 trust shake:\nphantom status flicker",
        xy=(11, p1[10]),
        xytext=(7.5, 0.32),
        fontsize=7.5,
        color=VERMILION,
        arrowprops=dict(arrowstyle="->", color=VERMILION, lw=0.8),
    )
    ax.annotate(
        "P2 trust shake:\nmissed Yale deadline",
        xy=(9, p2[8]),
        xytext=(9.0, 0.30),
        fontsize=7.5,
        color=COBALT,
        arrowprops=dict(arrowstyle="->", color=COBALT, lw=0.8),
    )

    ax.set_xlabel("Week of cycle (Sept Week 1 → Nov Week 12)")
    ax.set_ylabel("Trust + retained usage (0–1)")
    ax.set_title("Churn-risk timeline across 3 personas, Sept–Nov 2026", pad=10)
    ax.set_ylim(0.25, 1.0)
    ax.set_xticks(weeks)
    ax.axhline(0.5, color=RULE, linestyle="--", linewidth=0.6, alpha=0.5)
    ax.text(12.2, 0.50, "quit\nthreshold", fontsize=7, color=RULE, va="center")
    ax.legend(loc="lower left", fontsize=8, frameon=False)
    fig.tight_layout()
    p = FIG_DIR / "03_churn_timeline.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# ── Chart 4: Retained scope by persona ───────────────────────────────────────

def chart_retained_scope() -> Path:
    """Stacked horizontal bars: % of intended scope still actively used,
    plus the workaround/abandoned slices."""
    personas = ["P1 Aisha", "P2 James", "P3 Wei"]
    used = [55, 50, 90]
    workaround = [25, 30, 8]
    abandoned = [20, 20, 2]

    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.set_facecolor(PAPER)
    y = np.arange(len(personas))
    ax.barh(y, used, color=SAGE, label="Still actively used")
    ax.barh(y, workaround, left=used, color=CITRON, label="Workaround (parallel tool)")
    ax.barh(
        y,
        abandoned,
        left=np.array(used) + np.array(workaround),
        color=OXBLOOD,
        label="Abandoned",
    )
    ax.set_yticks(y)
    ax.set_yticklabels(personas)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of intended scope (%)")
    ax.set_title("Retained scope by persona at end of Month 3", pad=10)
    ax.legend(loc="lower right", fontsize=8, frameon=False, ncol=3, bbox_to_anchor=(1.0, -0.55))
    for i, (u, w, a) in enumerate(zip(used, workaround, abandoned)):
        ax.text(u / 2, i, f"{u}%", ha="center", va="center", color="white", fontsize=8)
        ax.text(u + w / 2, i, f"{w}%", ha="center", va="center", color=INK, fontsize=8)
        if a > 0:
            ax.text(u + w + a / 2, i, f"{a}%", ha="center", va="center", color="white", fontsize=8)
    fig.tight_layout()
    p = FIG_DIR / "04_retained_scope.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# ── Chart 5: Effort vs impact 2x2 for recommendations ────────────────────────

def chart_effort_impact() -> Path:
    """Recommendations plotted by effort vs impact. P0 in upper-left."""
    items = [
        # (label, effort 0..10, impact 0..10, color)
        ("R0a Recommender entity refactor", 7.5, 9.5, VERMILION),
        ("R0b Wire up positions schema cols", 2.5, 7.5, VERMILION),
        ("R0c Fix R2-delete cascade", 1.5, 5.0, VERMILION),
        ("R0d Recommender email + mailto", 2.0, 6.0, VERMILION),
        ("R1a Bulk operations", 5.5, 8.0, COBALT),
        ("R1b In-UI settings page", 4.0, 6.5, COBALT),
        ("R1c TRACKER_PROFILE switch", 6.5, 8.5, COBALT),
        ("R2a File attachments + versioning", 8.5, 7.0, "#8a6d00"),
        ("R2b Responsive layout", 5.0, 5.5, "#8a6d00"),
        ("R2c Keyboard shortcuts", 3.5, 4.5, "#8a6d00"),
        ("R2d In-app backup button", 1.5, 4.5, "#8a6d00"),
        ("R2e Grouped reminder mailto", 2.0, 3.5, "#8a6d00"),
    ]

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.set_facecolor(PAPER)
    for label, eff, imp, c in items:
        ax.scatter(eff, imp, s=180, color=c, edgecolor=INK, linewidth=0.6, alpha=0.85, zorder=3)
        ax.annotate(label, (eff, imp), xytext=(6, 4), textcoords="offset points", fontsize=7.5)

    ax.axvline(5, color=RULE, linestyle="--", linewidth=0.6, alpha=0.7)
    ax.axhline(5, color=RULE, linestyle="--", linewidth=0.6, alpha=0.7)
    ax.text(2.5, 9.6, "QUICK WINS", fontsize=10, color=SAGE, weight="bold", ha="center")
    ax.text(7.5, 9.6, "BIG BETS", fontsize=10, color=COBALT, weight="bold", ha="center")
    ax.text(2.5, 0.4, "TIME-FILLERS", fontsize=10, color=RULE, weight="bold", ha="center")
    ax.text(7.5, 0.4, "RECONSIDER", fontsize=10, color=OXBLOOD, weight="bold", ha="center")

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_xlabel("Engineering effort  (1 = afternoon, 10 = multi-week)")
    ax.set_ylabel("Churn-risk reduction impact  (1 = nicety, 10 = retention-critical)")
    ax.set_title("Effort vs impact — 12 prioritized recommendations", pad=10)
    legend_items = [
        Patch(color=VERMILION, label="P0 — churn-blocker"),
        Patch(color=COBALT, label="P1 — frequent friction"),
        Patch(color="#8a6d00", label="P2 — quality-of-life"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    p = FIG_DIR / "05_effort_impact.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# ── Chart 6: Competitor feature matrix ───────────────────────────────────────

def chart_competitor_matrix() -> Path:
    """Feature × competitor heatmap. 0=absent, 1=partial, 2=full."""
    features = [
        "Academic vocabulary native",
        "Recommender workflow first-class",
        "Per-position materials matrix",
        "Status pipeline / kanban",
        "Deadline urgency view",
        "Letters delivered to committees",
        "Job-board ingestion",
        "AI cover-letter / resume",
        "Browser extension",
        "Mobile / tablet UI",
        "Local data ownership",
        "Markdown / portable export",
        "$0 pricing, no account",
        "Multi-device sync",
    ]
    competitors = [
        "AAT\n(this app)",
        "Interfolio\nDossier",
        "Academic\nJobs Online",
        "Huntr",
        "Teal HQ",
        "Notion\ntemplate",
    ]
    data = np.array(
        [
            # AAT, Interfolio, AJO, Huntr, Teal, Notion
            [2, 2, 2, 0, 0, 1],  # academic vocab
            [1, 2, 2, 0, 0, 1],  # recommender workflow
            [2, 0, 0, 0, 0, 1],  # materials matrix
            [2, 0, 0, 2, 2, 2],  # status pipeline
            [2, 1, 1, 1, 1, 1],  # urgency view
            [0, 2, 2, 0, 0, 0],  # letter delivery
            [0, 0, 1, 2, 2, 0],  # job-board ingestion
            [0, 0, 0, 1, 2, 0],  # AI tailoring
            [0, 0, 0, 2, 2, 1],  # extension
            [0, 1, 1, 2, 2, 2],  # mobile
            [2, 0, 0, 0, 0, 0],  # local data
            [2, 0, 0, 0, 1, 1],  # markdown export
            [2, 0, 2, 1, 1, 1],  # free/no-account
            [0, 2, 2, 2, 2, 2],  # multi-device sync
        ]
    )

    fig, ax = plt.subplots(figsize=(7.4, 6.0))
    ax.set_facecolor(PAPER)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "cobalt_band", ["#FFFFFF", "#DDE3F3", COBALT]
    )
    im = ax.imshow(data, cmap=cmap, vmin=0, vmax=2, aspect="auto")
    ax.set_xticks(range(len(competitors)))
    ax.set_xticklabels(competitors, fontsize=8.5)
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False)
    ax.set_yticks(range(len(features)))
    ax.set_yticklabels(features, fontsize=8)

    for i in range(len(features)):
        for j in range(len(competitors)):
            v = data[i, j]
            label = {0: "—", 1: "◐", 2: "●"}[v]
            txt_color = "white" if v == 2 else INK
            ax.text(j, i, label, ha="center", va="center", fontsize=10, color=txt_color)

    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2], shrink=0.5)
    cbar.ax.set_yticklabels(["Absent", "Partial", "Full"], fontsize=8)
    ax.set_title("Competitive feature matrix  (14 features × 6 products)", pad=12)
    ax.set_xticks(np.arange(-0.5, 6, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 14, 1), minor=True)
    ax.grid(which="minor", color=RULE, alpha=0.25, linewidth=0.4)
    ax.tick_params(which="minor", length=0)
    fig.tight_layout()
    p = FIG_DIR / "06_competitor_matrix.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# ── PDF builder ──────────────────────────────────────────────────────────────


def build_pdf(chart_paths: dict[str, Path]) -> Path:
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Academic Application Tracker — UX Field Study Report",
        author="UX Research",
    )

    styles = getSampleStyleSheet()
    H1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName="Times-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor(INK),
        spaceAfter=10,
    )
    # H2 style retained for downstream forks of this script; currently
    # unused by the rendered report.
    _H2_unused = ParagraphStyle(  # noqa: F841
        "H2",
        parent=styles["Heading2"],
        fontName="Times-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor(VERMILION),
        spaceBefore=14,
        spaceAfter=6,
    )
    H3 = ParagraphStyle(
        "H3",
        parent=styles["Heading3"],
        fontName="Times-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor(COBALT),
        spaceBefore=8,
        spaceAfter=4,
    )
    BODY = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=10,
        leading=13.5,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    BULLET = ParagraphStyle(
        "Bullet",
        parent=BODY,
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=3,
    )
    QUOTE = ParagraphStyle(
        "Quote",
        parent=BODY,
        leftIndent=20,
        rightIndent=20,
        fontName="Times-Italic",
        textColor=colors.HexColor("#5A5752"),
        spaceBefore=4,
        spaceAfter=8,
    )
    CAPTION = ParagraphStyle(
        "Caption",
        parent=BODY,
        fontName="Times-Italic",
        fontSize=8.5,
        textColor=colors.HexColor("#5A5752"),
        alignment=TA_CENTER,
        spaceBefore=2,
        spaceAfter=10,
    )
    META = ParagraphStyle(
        "Meta",
        parent=BODY,
        fontName="Times-Italic",
        fontSize=9,
        textColor=colors.HexColor("#5A5752"),
        alignment=TA_CENTER,
    )
    COVER_TITLE = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=28,
        leading=34,
        textColor=colors.HexColor(INK),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    COVER_SUB = ParagraphStyle(
        "CoverSub",
        parent=BODY,
        fontName="Times-Italic",
        fontSize=14,
        leading=20,
        textColor=colors.HexColor(VERMILION),
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    story: list = []

    # ── Cover page ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.4 * inch))
    story.append(Paragraph("Academic Application Tracker", COVER_TITLE))
    story.append(Paragraph("UX Field Study Report", COVER_SUB))
    story.append(Spacer(1, 0.4 * inch))
    story.append(
        Paragraph(
            "Three-month simulated usage across three personas<br/>"
            "Sept – Nov 2026<br/>"
            "Fact-verified against the v0.14.0-dev codebase",
            META,
        )
    )
    story.append(Spacer(1, 2.0 * inch))
    cover_meta = Table(
        [
            ["Report date", date(2026, 5, 22).isoformat()],
            ["Codebase reference", "feat/ui-redesign-v0.14.0 @ commit 2ded3ba"],
            ["Audience", "Marketing · Product · Engineering"],
            ["Length", "20 pages, 6 figures, 7 tables"],
            ["Classification", "Internal — pre-decision research"],
        ],
        colWidths=[1.8 * inch, 4.0 * inch],
    )
    cover_meta.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 10),
                ("FONT", (0, 0), (0, -1), "Times-Bold", 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(COBALT)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
            ]
        )
    )
    story.append(cover_meta)
    story.append(PageBreak())

    # ── Table of Contents ──────────────────────────────────────────────────
    story.append(Paragraph("Table of Contents", H1))
    story.append(Spacer(1, 6))
    toc_rows = [
        ["1.", "Executive Summary", "3"],
        ["2.", "Study Methodology", "4"],
        ["3.", "Personas at a Glance", "5"],
        ["4.", "Persona 1 — Aisha K., life-sci postdoc", "6"],
        ["5.", "Persona 2 — James M., humanities TT applicant", "7"],
        ["6.", "Persona 3 — Wei L., CS PhD mixed search", "8"],
        ["7.", "Cross-cutting Friction Themes", "9"],
        ["8.", "Friction Severity Heatmap", "10"],
        ["9.", "Verified Bug-class Findings", "11"],
        ["10.", "Churn-risk Timeline + Retained Scope", "12"],
        ["11.", "What's Working — Strengths to Preserve", "13"],
        ["12.", "Competitive Landscape Analysis", "14"],
        ["13.", "Competitive Feature Matrix", "15"],
        ["14.", "Prioritized Recommendations (P0)", "16"],
        ["15.", "Prioritized Recommendations (P1, P2) + Effort-Impact", "17"],
        ["16.", "Strategic Roadmap & Audience-specific Takeaways", "18"],
        ["17.", "Appendix A — Verified Code References", "19"],
        ["18.", "Appendix B — Methodology Limitations + References", "20"],
    ]
    toc = Table(toc_rows, colWidths=[0.5 * inch, 5.5 * inch, 0.5 * inch])
    toc.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 10),
                ("FONT", (0, 0), (0, -1), "Times-Bold", 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(VERMILION)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
            ]
        )
    )
    story.append(toc)
    story.append(PageBreak())

    # ── 1. Executive Summary ───────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", H1))
    story.append(
        Paragraph(
            "Three independent persona simulations (a life-sciences postdoc, a humanities "
            "tenure-track applicant, and a computer-science PhD running a mixed academic + "
            "industry search) used the Academic Application Tracker (AAT) for a simulated "
            "three-month cycle, Sept–Nov 2026. Each persona's journey was traced against the "
            "actual v0.14.0-dev codebase; the friction points, near-quit moments, and "
            "workarounds reported below are tied to specific file and line numbers and have "
            "been spot-verified against the source.",
            BODY,
        )
    )
    story.append(Paragraph("Headline finding.", H3))
    story.append(
        Paragraph(
            "The dominant churn risk is structural, not cosmetic. The "
            "<b>recommender entity is modelled per-position</b> rather than as a global "
            "first-class entity, which forces N × M data entry on Day 1. Both the postdoc and "
            "the humanities applicant nearly abandoned the tool within the first hour; both "
            "permanently demoted the Recommenders page to a manual filing-cabinet workflow.",
            BODY,
        )
    )
    story.append(Paragraph("Secondary themes (all three personas).", H3))
    for txt in [
        "Hardcoded vocabulary in <i>config.py</i> requires Python edits to extend "
        "(blocks non-coders entirely; converts a power user into a contributor).",
        "No bulk operations — single-row select everywhere; one-recommender-per-row "
        "submission updates; one-cell-per-edit requirement toggles.",
        "Cascade asymmetries: <b>R2 promotes on add_interview but does not retract "
        "on delete_interview</b> (real defect, verified at database.py:707–719).",
        "Mobile/tablet experience is broken; lost ≈30% of one persona's tracking "
        "sessions to layout collapse under <i>layout=&quot;wide&quot;</i>.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))

    story.append(Paragraph("What's working (preserve at all costs).", H3))
    for txt in [
        "The editorial-brutalist visual identity (<i>ui.py</i>) drew "
        "unprompted positive reactions from all three personas — rare for a "
        "research-internal Streamlit app.",
        "The Upcoming-deadlines panel + urgency banding is the single feature that "
        "<i>genuinely outperforms a spreadsheet</i> for two of three personas.",
        "Markdown exports on every write (DESIGN D4) build durable trust that the data "
        "survives the app itself.",
        "The <i>config.py</i> import-time invariants converted a near-fork into an "
        "upstream pull request from the power-user persona — the highest praise a "
        "codebase can earn from a developer-evaluator.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))

    story.append(Paragraph("Verdict.", H3))
    story.append(
        Paragraph(
            "All three personas retained the tool through Month 3 — none churned outright — "
            "but two operate at roughly 50% of intended scope, maintaining parallel "
            "Google Docs / Sheets for the workflows AAT could not absorb. The "
            "recommender-entity refactor (P0) is the single biggest churn-reduction lever; "
            "shipping it before any new feature work will lift retention from "
            "<i>de facto</i> half-use to genuine primary-workflow status.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 2. Methodology ─────────────────────────────────────────────────────
    story.append(Paragraph("2. Study Methodology", H1))
    story.append(Paragraph("Design.", H3))
    story.append(
        Paragraph(
            "Simulated longitudinal field study with three composite personas, each "
            "constructed from common applicant archetypes in their field. Each persona's "
            "three-month timeline was synthesized by an independent reviewer reading the "
            "v0.14.0-dev source in full (DESIGN.md, GUIDELINES.md, app.py, pages/*.py, "
            "ui.py, config.py, database.py, docs/dev-notes/self-host-setup.md) and "
            "walking through the page-by-page workflows for the persona's most likely "
            "operational sequence.",
            BODY,
        )
    )
    story.append(Paragraph("Reviewer brief.", H3))
    story.append(
        Paragraph(
            "Each reviewer was instructed to be a tough, honest user — not a friendly "
            "tester — and to surface at least eight concrete frictions and at least two "
            "near-quit moments per persona, citing file and line references so the "
            "engineering team could locate root causes.",
            BODY,
        )
    )
    story.append(Paragraph("Verification.", H3))
    story.append(
        Paragraph(
            "Every load-bearing file:line citation in this report was spot-checked against "
            "the current source before publication. Two claims required reclassification:",
            BODY,
        )
    )
    for txt in [
        "Persona 1's report that <i>applied_date</i> does not promote status to <i>[APPLIED]</i> "
        "is incorrect at the data-layer: the R1 cascade is implemented at <b>database.py:506–510</b>. "
        "Reclassified as a <i>UI feedback gap</i> (the promotion happens silently from the user's "
        "perspective — no toast on the Applications page) rather than a logic bug.",
        "Persona 3's report of an R2 asymmetry on <i>delete_interview</i> is confirmed: "
        "<b>database.py:707–719</b> deletes the interview row but has no symmetric "
        "<i>[INTERVIEW] → [APPLIED]</i> retraction. Filed as a real defect.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))

    story.append(Paragraph("Scope limits.", H3))
    story.append(
        Paragraph(
            "This is a simulated study, not a live human study. Findings about visual "
            "appeal, friction intensity, and trust shake are reasoned from realistic usage "
            "patterns but have not been validated against real user telemetry or "
            "interview data. The competitive analysis is desk-research only.",
            BODY,
        )
    )
    story.append(Paragraph("Reproducibility.", H3))
    story.append(
        Paragraph(
            "Charts and the full PDF are regenerated by "
            "<i>.venv/bin/python scripts/build_ux_report.py</i>. All friction theme scores, "
            "competitive matrix cells, and effort-impact placements live in that script's "
            "data arrays; revising any data point only requires editing the script and "
            "re-running.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 3. Personas at a Glance ────────────────────────────────────────────
    story.append(Paragraph("3. Personas at a Glance", H1))
    persona_table = Table(
        [
            ["Axis", "P1 — Aisha K.", "P2 — James M.", "P3 — Wei L."],
            ["Field", "Computational biology", "Comparative literature", "Machine learning / NLP"],
            ["Cycle target", "Fall 2026 postdoc", "Fall 2027 TT faculty", "Postdoc + industry research"],
            ["Tracked positions (3 mo)", "~40", "~22", "~51 (15 ac. + 30 ind. + 6 other)"],
            ["Recommenders", "4", "5", "3"],
            ["Tech comfort", "High (Python dev)", "Moderate (no Python)", "Very high (would fork)"],
            ["Primary device", "MacBook + iPad on bus", "Saturday desktop sessions", "Linux desktop"],
            ["Near-quit moments", "2", "2", "2 near-fork (resolved)"],
            ["Outcome (Month 3)", "Stays w/ caveats (B−)", "Stays at ~50% scope", "Stays + upstream PR"],
        ],
        colWidths=[1.5 * inch, 1.85 * inch, 1.85 * inch, 1.85 * inch],
    )
    persona_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 9),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9.5),
                ("FONT", (0, 0), (0, -1), "Times-Bold", 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(INK)),
                ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor(COBALT)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
            ]
        )
    )
    story.append(persona_table)
    story.append(Spacer(1, 12))
    story.append(Image(str(chart_paths["radar"]), width=6.5 * inch, height=4.5 * inch))
    story.append(Paragraph("Figure 1. Persona profile across five normalized axes.", CAPTION))
    story.append(PageBreak())

    # ── 4. Persona 1 — Aisha ───────────────────────────────────────────────
    story.append(Paragraph("4. Persona 1 — Aisha K., life-sciences postdoc applicant", H1))
    story.append(
        Paragraph(
            "<b>Profile.</b> Fourth-year PhD in computational biology at a US R1; targeting "
            "~40 fall 2026 postdoc positions over a three-month cycle. Four recommenders; "
            "high Python fluency; tracks on a MacBook at her desk and on an iPad on the bus.",
            BODY,
        )
    )
    story.append(Paragraph("Month-1 onboarding.", H3))
    story.append(
        Paragraph(
            "Setup is smooth — clone, venv, <i>streamlit run app.py</i>. The dashboard's "
            "editorial design lands well. Quick-add covers six fields. Within 40 minutes she "
            "has logged 12 positions. Two hours in she discovers the <b>schema-UI gap</b>: "
            "<i>location</i>, <i>source</i>, <i>mentor</i>, <i>point_of_contact</i>, "
            "<i>portal_url</i>, <i>stipend</i> and four other columns exist in the "
            "<i>positions</i> table (database.py:77–94) but are written nowhere in the UI. "
            "Quote: <i>“They built half the schema and then forgot to wire it up?”</i>",
            BODY,
        )
    )
    story.append(Paragraph("Day 14 — near-quit #1.", H3))
    story.append(
        Paragraph(
            "Adding her first recommender, she discovers the per-position model "
            "(database.py:135; pages/3_Recommenders.py:311): 4 recommenders × 40 positions = "
            "160 manual add operations. She stops at row 15.",
            BODY,
        )
    )
    story.append(
        Paragraph(
            "“This is a database UI, not a job tracker. I'm doing data entry, not "
            "application strategy. I came here to stop using a spreadsheet, not to build a "
            "worse one.”",
            QUOTE,
        )
    )
    story.append(
        Paragraph(
            "Resolution: she enters recommenders only for her top-15 positions; the dashboard "
            "alert panel becomes silently incomplete for the remaining 25.",
            BODY,
        )
    )
    story.append(Paragraph("Mid-cycle frictions.", H3))
    for txt in [
        "iPad layout collapses under <i>layout=&quot;wide&quot;</i>; ~30% of her "
        "intended bus-commute tracking sessions are abandoned.",
        "<i>Compose Reminder Email</i> opens a <i>mailto:</i> with an empty <b>To</b> field — "
        "the <i>recommenders</i> schema has no email column (verified: database.py:135–148, "
        "pages/3_Recommenders.py:142).",
        "Setting <i>applied_date</i> on the Applications page does promote status via R1 "
        "(database.py:506–510) but the page emits no visible feedback, so the promotion "
        "feels invisible.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))

    story.append(Paragraph("Nov 18 — near-quit #2.", H3))
    story.append(
        Paragraph(
            "36 hours before the Stanford deadline, a fast tab-switch makes the Status "
            "selectbox flicker stale state, briefly showing <i>[SAVED]</i> for a row she'd "
            "already promoted to <i>[APPLIED]</i>. She refreshes; the state is correct. "
            "But the trust hit is real. <i>“If this is wrong, my whole pipeline view is wrong.”</i> "
            "She stays out of pure inertia, not loyalty.",
            BODY,
        )
    )
    story.append(Paragraph("Month-3 verdict.", H3))
    story.append(
        Paragraph(
            "Still using AAT on her laptop, but has <b>stopped opening it on the bus</b> and "
            "maintains a parallel Google Sheet for recommender coverage. The tool has become "
            "“where I write the canonical state once, then never edit from a touch device.” "
            "Grade: B−.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 5. Persona 2 — James ───────────────────────────────────────────────
    story.append(Paragraph("5. Persona 2 — James M., humanities tenure-track applicant", H1))
    story.append(
        Paragraph(
            "<b>Profile.</b> Third-year postdoc in comparative literature; targeting ~22 "
            "TT positions for a fall 2027 start. Five recommenders (almost every faculty "
            "application asks for all five); 8–11 separate documents per application "
            "including a heavily customised cover letter and a 30-page writing sample whose "
            "chapter varies per posting. Moderate tech comfort — will not edit Python.",
            BODY,
        )
    )
    story.append(Paragraph("Day-1 setup.", H3))
    story.append(
        Paragraph(
            "Successful clone + install + <i>streamlit run</i>. The editorial design lands "
            "as charming rather than fussy. He enters nine positions through Quick-Add over "
            "a Saturday morning. The Requirements tab forces a vocabulary gap: there is no "
            "<i>Teaching Portfolio</i>, no <i>Job Talk Sample</i>, no <i>Syllabi</i> in "
            "<i>REQUIREMENT_DOCS</i> (config.py:286–295). He pushes them into the Notes "
            "freetext, knowing the dashboard's Materials Readiness will be lying.",
            BODY,
        )
    )
    story.append(Paragraph("Day 1 — near-quit #1.", H3))
    story.append(
        Paragraph(
            "Adding his five recommenders × 22 positions = 110 manual rows. He stops at "
            "row 15. Demotes the Recommenders page on Day 1 from <i>workflow</i> to "
            "<i>filing cabinet</i>. Tracks his real letter-writer state in his existing "
            "Google Doc.",
            BODY,
        )
    )
    story.append(Paragraph("Month 2 — the materials-versioning gap becomes the story.", H3))
    story.append(
        Paragraph(
            "Hopkins wants 25 pages of the Borges chapter; UPenn wants 35 pages of a "
            "different (Cortázar) chapter; Cornell wants the Borges chapter with a "
            "job-talk-framed rewrite. The Materials tab tracks only a boolean: "
            "<i>done_writing_sample = 1</i> = “I sent something.” It records <i>nothing</i> "
            "about which chapter, which version, or which file. Quote: <i>“The thing the tool "
            "helps me with — am I done? — isn't what I most need to track.”</i>",
            BODY,
        )
    )
    story.append(Paragraph("Oct 31 — near-quit #2.", H3))
    story.append(
        Paragraph(
            "Misses the Yale 5pm submission window by minutes. The urgency pill said "
            "<i>T-7D</i> all week; his Google Calendar's 7-day-out reminder fired the same "
            "signal. AAT added zero independent value to deadline awareness for that "
            "application. Stays because switching tools 36 hours from a deadline is its own "
            "risk.",
            BODY,
        )
    )
    story.append(Paragraph("Month 3 — settled but narrowed.", H3))
    story.append(
        Paragraph(
            "Uses Dashboard + Opportunities + Applications. Recommenders page effectively "
            "abandoned. Keeps Google Docs for cover-letter versioning, writing-sample-per-"
            "department tracking, and per-interview prep notes. Saves a Dropbox copy of "
            "<i>postdoc.db</i> manually on Nov 22 after realizing the markdown export does "
            "not protect his state.",
            BODY,
        )
    )
    story.append(Paragraph("Verdict.", H3))
    story.append(
        Paragraph(
            "Stays at ~50% scope. Would recommend with reservations. Would not pay for it.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 6. Persona 3 — Wei ─────────────────────────────────────────────────
    story.append(Paragraph("6. Persona 3 — Wei L., CS PhD running a mixed search", H1))
    story.append(
        Paragraph(
            "<b>Profile.</b> Fifth-year PhD, ML / NLP. Mixed search: ~15 academic positions "
            "(postdoc + TT) and ~30 industry research roles (DeepMind, Anthropic, FAIR, "
            "smaller labs, two YC AI startups). Three recommenders. Very high tech comfort "
            "— would read the source and consider forking. Currently on a Notion database.",
            BODY,
        )
    )
    story.append(Paragraph("Day-1 onboarding.", H3))
    story.append(
        Paragraph(
            "Reads <i>DESIGN.md</i> and <i>config.py</i> end-to-end before adding data. "
            "Quote: <i>“OK, fine, this is a real codebase.”</i> The four-layer architecture "
            "and import-time invariants earn explicit respect.",
            BODY,
        )
    )
    story.append(Paragraph("Day 7 — near-fork #1.", H3))
    story.append(
        Paragraph(
            "Adds his first recruiter screen as an interview row. R2 cascade "
            "(database.py:629) immediately promotes the position to <i>[INTERVIEW]</i>. A "
            "25-minute recruiter chat is now visually equivalent to a Stanford committee "
            "onsite on the dashboard funnel. Considers forking; instead opens a GitHub "
            "issue draft. <b>Resolved by codebase extensibility</b> — the <i>config.py</i> "
            "invariants make extension feasible.",
            BODY,
        )
    )
    story.append(Paragraph("Day 28 — near-fork #2.", H3))
    story.append(
        Paragraph(
            "Maintains a personal branch with new statuses (<i>[GHOSTED]</i>), new interview "
            "formats (Recruiter Screen, Tech Screen, Onsite Loop), new response types, and "
            "a CSV importer. Reads the v2 vision in <i>roadmap.md</i> and files three "
            "GitHub issues instead of forking. Eventually lands one upstream PR "
            "(recruiter-screen R2 exemption).",
            BODY,
        )
    )
    story.append(Paragraph("Nov 4 — real defect filed.", H3))
    story.append(
        Paragraph(
            "Deletes the only interview row on a position that had been auto-promoted to "
            "<i>[INTERVIEW]</i>. Status does not retract. Files an issue: <i>“R2 promotion "
            "is not symmetric with delete_interview — orphan [INTERVIEW] status after "
            "deleting the only interview row.”</i> Verified against database.py:707–719: "
            "the delete path has no reverse cascade.",
            BODY,
        )
    )
    story.append(Paragraph("Verdict.", H3))
    story.append(
        Paragraph(
            "Daily use through Month 3. <b>Contributes upstream</b> rather than forking — "
            "the highest-praise outcome a codebase can earn from a developer-evaluator. "
            "Net cost: he maintains a personal branch for industry-specific extensions the "
            "upstream hasn't yet absorbed.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 7. Cross-cutting friction themes ──────────────────────────────────
    story.append(Paragraph("7. Cross-cutting Friction Themes", H1))
    story.append(
        Paragraph(
            "Fifteen friction themes were identified across the three persona studies. The "
            "table below ranks them by composite churn-risk weight (frequency × severity × "
            "persona reach). Cells use <b>H</b> = high/catastrophic, <b>M</b> = medium, "
            "<b>L</b> = low, <b>—</b> = not encountered.",
            BODY,
        )
    )
    rows = [
        ["#", "Theme", "P1", "P2", "P3", "Root location"],
        ["1", "Recommender entity modelled per-position", "H", "H", "—", "database.py:135"],
        ["2", "No bulk operations across rows", "H", "H", "M", "pages/3_Recommenders.py"],
        ["3", "Vocabulary hardcoded in config.py", "M", "M", "M", "config.py:45–322"],
        ["4", "Schema-UI gap on positions table", "H", "L", "L", "database.py:77–94"],
        ["5", "Cascade asymmetry on delete_interview", "—", "—", "H", "database.py:707–719"],
        ["6", "No materials versioning / attachments", "L", "H", "L", "schema by design"],
        ["7", "Threshold tuning requires Python edit", "L", "M", "L", "config.py:320–322"],
        ["8", "Recommender email column missing", "H", "L", "—", "database.py:135–148"],
        ["9", "No responsive layout (tablet broken)", "H", "—", "—", "app.py:19; ui.py"],
        ["10", "No keyboard shortcuts", "—", "L", "M", "ui.py:1265 shield"],
        ["11", "Pipeline doesn't fit non-postdoc cycles", "—", "M", "H", "config.py:45–53,265"],
        ["12", "Reminder mailto per-position not per-recommender", "L", "M", "—", "pages/3_Recommenders.py:230"],
        ["13", "Dashboard date column has no year", "M", "L", "—", "app.py:378"],
        ["14", "No in-app backup affordance", "L", "H", "—", "pages/4_Export.py"],
        ["15", "init_db() on every page load (~500ms)", "—", "—", "L", "app.py:22"],
    ]
    table = Table(rows, colWidths=[0.3 * inch, 3.0 * inch, 0.45 * inch, 0.45 * inch, 0.45 * inch, 2.2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 8.5),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("ALIGN", (2, 0), (4, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
                ("FONT", (5, 1), (5, -1), "Courier", 7.5),
            ]
        )
    )
    story.append(table)
    story.append(PageBreak())

    # ── 8. Heatmap ────────────────────────────────────────────────────────
    story.append(Paragraph("8. Friction Severity Heatmap", H1))
    story.append(
        Paragraph(
            "The same fifteen themes rendered as a heatmap make the persona-reach pattern "
            "visible at a glance. Three themes are universal (cells lit in all three columns); "
            "five are persona-specific. The pattern is informative for prioritization: "
            "<b>universal frictions are P0 candidates</b>; persona-specific high-severity "
            "frictions (P1 mobile, P2 versioning, P3 cascade defect) belong in P1/P2 tiers.",
            BODY,
        )
    )
    story.append(Image(str(chart_paths["heatmap"]), width=6.6 * inch, height=6.2 * inch))
    story.append(Paragraph("Figure 2. Friction severity matrix.", CAPTION))
    story.append(PageBreak())

    # ── 9. Bug-class findings ─────────────────────────────────────────────
    story.append(Paragraph("9. Verified Bug-class Findings", H1))
    story.append(
        Paragraph(
            "Four findings rise above UX friction and qualify as defects or "
            "feature-completion gaps. Each was verified against the source on the "
            "<i>feat/ui-redesign-v0.14.0</i> branch.",
            BODY,
        )
    )
    bug_rows = [
        ["#", "Finding", "Severity", "Location", "Status"],
        [
            "B1",
            "R2 cascade asymmetry: add_interview promotes [APPLIED]→[INTERVIEW]; "
            "delete_interview has no reverse cascade. Position promoted via since-"
            "deleted interview stays at [INTERVIEW] forever.",
            "High",
            "database.py:707–719\n(delete path)",
            "Confirmed",
        ],
        [
            "B2",
            "Recommender email column missing from schema; Compose Reminder Email "
            "helper builds a mailto: with an empty To field.",
            "High",
            "database.py:135–148\npages/3_Recommenders.py:142",
            "Confirmed",
        ],
        [
            "B3",
            "Schema-UI gap on positions table: 10 nullable columns "
            "(location, source, mentor, point_of_contact, portal_url, stipend, "
            "keywords, description, deadline_note, reference_code) exist in the "
            "schema but no UI surface writes to them. Violates D1 (config single "
            "source of truth) and traps user data in the Notes freetext.",
            "High",
            "database.py:77–94\npages/1_Opportunities.py",
            "Confirmed",
        ],
        [
            "B4",
            "Applications page calls upsert_application with applied_date; R1 "
            "cascade fires correctly at database.py:506–510 but no toast or visible "
            "indicator surfaces the promotion. Persona 1 perceived this as a missing "
            "cascade. Reclassified from logic bug to feedback gap.",
            "Medium",
            "pages/2_Applications.py\nvs database.py:506–510",
            "Reclassified",
        ],
    ]
    bug_table = Table(bug_rows, colWidths=[0.35 * inch, 3.0 * inch, 0.7 * inch, 1.5 * inch, 0.8 * inch])
    bug_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 8.5),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (4, 0), (4, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
                ("FONT", (3, 1), (3, -1), "Courier", 7.5),
                ("TEXTCOLOR", (2, 1), (2, 3), colors.HexColor(VERMILION)),
                ("TEXTCOLOR", (2, 4), (2, 4), colors.HexColor("#8a6d00")),
            ]
        )
    )
    story.append(bug_table)
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "<b>Recommended response.</b> File B1, B2, B3 as <i>fix:</i>-typed commits "
            "before any new feature work; each is a few-hour change with high churn-risk "
            "payoff. B4 needs a one-line toast addition in <i>pages/2_Applications.py</i> "
            "matching the existing R2 toast pattern at <i>pages/2_Applications.py:645</i>.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 10. Churn-risk timeline ────────────────────────────────────────────
    story.append(Paragraph("10. Churn-risk Timeline + Retained Scope", H1))
    story.append(
        Paragraph(
            "The two charts below trace each persona's trust + active-usage index across "
            "the 12-week study, and the share of intended scope still active at the end of "
            "Month 3.",
            BODY,
        )
    )
    story.append(Image(str(chart_paths["churn"]), width=6.8 * inch, height=3.6 * inch))
    story.append(
        Paragraph(
            "Figure 3. Trust + retained-usage index by week, with annotated near-quit "
            "events. The dashed line marks the qualitative quit threshold; the postdoc and "
            "humanities personas hover above it but do not cross.",
            CAPTION,
        )
    )
    story.append(Image(str(chart_paths["scope"]), width=6.6 * inch, height=2.4 * inch))
    story.append(
        Paragraph(
            "Figure 4. Share of intended scope at end of Month 3 — split into still-used, "
            "covered-by-parallel-tool, and outright-abandoned slices.",
            CAPTION,
        )
    )
    story.append(
        Paragraph(
            "<b>Reading.</b> P3 trends upward after Week 5 because the codebase rewards "
            "extension; his abandonment risk converts into contribution. P1 and P2 settle "
            "into a permanent ~50% trust plateau — the tool is retained but never owns the "
            "workflow. The retained-scope chart shows this directly: 20% of Aisha's "
            "intended workflow is outright abandoned (the Recommenders page and the "
            "tablet-on-bus tracking sessions).",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 11. What's working ────────────────────────────────────────────────
    story.append(Paragraph("11. What's Working — Strengths to Preserve", H1))
    story.append(
        Paragraph(
            "Six product strengths surfaced as positively-noted in two or more persona "
            "studies. These are not optional polish; they are the reasons each persona "
            "retained the tool through Month 3 despite the frictions above. Any feature work "
            "that risks degrading these properties should clear an explicit bar.",
            BODY,
        )
    )
    rows = [
        ["#", "Strength", "Personas", "Why it matters"],
        [
            "S1",
            "Editorial-brutalist visual identity",
            "P1, P2, P3",
            "Only Streamlit app in surveyed competitor set with a distinct visual voice. "
            "P2: “the only tool that feels commensurate with the seriousness of a faculty "
            "job search.”",
        ],
        [
            "S2",
            "Upcoming-deadlines panel + urgency banding",
            "P1, P2, P3",
            "The single feature that genuinely outperforms a spreadsheet. Daily-driver "
            "pane for all three personas (app.py:336–410; config.py:363–390).",
        ],
        [
            "S3",
            "Markdown export on every write (D4)",
            "P1, P2, P3",
            "Builds durable trust that data survives the app itself. P3 commits the "
            "exported markdowns to a private git repo as a daily backup.",
        ],
        [
            "S4",
            "Auto-promotion cascade (R1/R2/R3) when correctly tuned",
            "P2 (love), P3 (respect)",
            "Removes invisible work from the user's head when correct. When incorrect "
            "(see B1, B4), it breaks trust hard.",
        ],
        [
            "S5",
            "config.py import-time invariants",
            "P3",
            "Converted P3's near-fork into an upstream PR. The single feature that earned "
            "the codebase respect from a developer-evaluator.",
        ],
        [
            "S6",
            "Quick-Add 6-field discipline (D6)",
            "P1, P2, P3",
            "Captures a new posting in genuinely under 30 seconds. Do not widen.",
        ],
    ]
    t = Table(rows, colWidths=[0.35 * inch, 2.0 * inch, 1.0 * inch, 3.55 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 9),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9.5),
                ("FONT", (1, 1), (1, -1), "Times-Bold", 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor(COBALT)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # ── 12. Competitive landscape ─────────────────────────────────────────
    story.append(Paragraph("12. Competitive Landscape Analysis", H1))
    story.append(
        Paragraph(
            "Four competitive categories were surveyed against the Academic Application "
            "Tracker (AAT). For each category, two to three representative products were "
            "compared on pricing, deployment, and the features most relevant to AAT's "
            "academic-applicant use case. Full URLs are in the References appendix.",
            BODY,
        )
    )
    rows = [
        ["Category", "Representative product", "Pricing", "Deployment", "Notable"],
        [
            "Academic-specific",
            "Interfolio Dossier",
            "$48–60 / year",
            "Cloud SaaS",
            "Canonical letter-delivery service; mandatory account; no personal pipeline",
        ],
        ["", "Academic Jobs Online", "Free to applicant", "Cloud SaaS", "STEM-heavy; institution-side workflow"],
        ["", "Versatile PhD", "Institutional subscription", "Cloud SaaS", "Content + community; not a tracker"],
        [
            "General SaaS",
            "Huntr",
            "Free ≤40 jobs; $10/mo Pro",
            "Cloud + Chrome extension",
            "Kanban + extension; no recommender model; industry vocab",
        ],
        ["", "Teal HQ", "Free; $29/mo Teal+", "Cloud + extension", "AI resume / cover-letter; ATS-keyword tuned"],
        ["", "JibberJobber", "Free; $9.95/mo Premium", "Cloud SaaS", "CRM-style; dated UI; generic"],
        [
            "Notion / templates",
            "Notion job-tracker template",
            "Free template + account",
            "Cloud SaaS",
            "Fully customisable; no schema validation",
        ],
        [
            "",
            "Etsy “Psych Postdoc Tracker” sheet",
            "One-off (~$5)",
            "Google Sheets",
            "Closest direct analog; explicit LOR + materials columns",
        ],
        [
            "OSS self-host",
            "JobSync (GitHub)",
            "Free",
            "Next.js + Docker",
            "Generic; no academic vocab; AI resume review",
        ],
        ["", "JobHunt (GitHub)", "Free", "React + ASP.NET 7", "Aggregates scraped postings; generic"],
    ]
    t = Table(
        rows,
        colWidths=[1.1 * inch, 1.7 * inch, 1.2 * inch, 1.3 * inch, 1.6 * inch],
    )
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 8.5),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor(VERMILION)),
                ("FONT", (0, 1), (0, -1), "Times-Bold", 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("SPAN", (0, 1), (0, 3)),
                ("SPAN", (0, 4), (0, 6)),
                ("SPAN", (0, 7), (0, 8)),
                ("SPAN", (0, 9), (0, 10)),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "<b>Positioning conclusion.</b> The combination <i>local SQLite + academic "
            "vocabulary + first-class recommender workflow + markdown export + $0 + no "
            "account</i> is not offered by any product surveyed. AAT does not replace "
            "Interfolio (still essential for delivering letters to committees). It replaces "
            "the <b>personal tracking spreadsheet that almost every academic applicant "
            "maintains alongside Interfolio</b>, with a real schema, deadline urgency view, "
            "interview-round modelling, and a portable markdown archive once the cycle ends.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 13. Feature matrix chart ──────────────────────────────────────────
    story.append(Paragraph("13. Competitive Feature Matrix", H1))
    story.append(
        Paragraph(
            "Fourteen features × six products. ● = full coverage, ◐ = partial, — = absent. "
            "AAT's column is densest in academic vocabulary, recommender workflow, materials "
            "matrix, status pipeline, urgency view, local data ownership, markdown export, "
            "and pricing — while leaving letter-delivery, mobile, browser extension, AI "
            "tailoring, and multi-device sync entirely uncovered.",
            BODY,
        )
    )
    story.append(Image(str(chart_paths["matrix"]), width=6.6 * inch, height=5.2 * inch))
    story.append(Paragraph("Figure 5. Competitive feature matrix.", CAPTION))
    story.append(
        Paragraph(
            "<b>For marketing.</b> The empty cells on the right half of AAT's column are "
            "not weaknesses to apologize for — they are the explicit non-goals stated in "
            "DESIGN §1.3 (no auth, no cloud, no mobile-first, no email/calendar, no "
            "multi-user). The right user is one for whom that list of absences is itself a "
            "selling point.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 14. P0 recommendations ────────────────────────────────────────────
    story.append(Paragraph("14. Prioritized Recommendations — P0 (churn-blockers)", H1))
    story.append(
        Paragraph(
            "Four P0 items should ship before any new feature work. Each addresses a "
            "verified bug or a high-severity friction encountered by at least two personas, "
            "and each is scoped to a few hours to a few days of engineering effort.",
            BODY,
        )
    )
    rows = [
        ["ID", "Item", "Effort", "Impact", "Closes"],
        [
            "R0a",
            "Promote recommenders to a global entity. New (id, name, email, relationship) "
            "table + join table (position_id, recommender_id, asked_date, confirmed, "
            "submitted_date, …). Bulk-assign UI on Opportunities.",
            "Multi-week",
            "Critical",
            "Friction #1, #8; Bug B2",
        ],
        [
            "R0b",
            "Wire up the 10 unused positions columns into Quick-Add (location, source) and "
            "Overview tab (mentor, point_of_contact, portal_url, stipend, keywords, "
            "deadline_note, reference_code, description). Either expose or remove from schema "
            "— D1 forbids dead schema.",
            "1–2 days",
            "High",
            "Bug B3; Friction #4",
        ],
        [
            "R0c",
            "Symmetric R2 cascade: delete_interview must retract status from [INTERVIEW] to "
            "[APPLIED] when the deleted row was the only interview on the position.",
            "Half-day",
            "High",
            "Bug B1",
        ],
        [
            "R0d",
            "Add a recommender_email column and populate the mailto: To field. Trivial "
            "schema migration with a large UX payoff.",
            "Half-day",
            "Medium-High",
            "Bug B2; Friction #8",
        ],
    ]
    t = Table(rows, colWidths=[0.4 * inch, 3.6 * inch, 0.8 * inch, 0.75 * inch, 1.4 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 9),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("FONT", (0, 1), (0, -1), "Times-Bold", 9),
                ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor(VERMILION)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # ── 15. P1 + P2 + chart ───────────────────────────────────────────────
    story.append(Paragraph("15. P1 & P2 Recommendations + Effort-Impact Map", H1))
    story.append(Paragraph("P1 — frequent friction (next minor).", H3))
    p1_rows = [
        ["ID", "Item", "Effort"],
        ["R1a", "Bulk operations: multi-select in Opportunities table; bulk status flip, "
                "requirement set, mark-submitted across N rows.", "Week"],
        ["R1b", "In-UI Settings page for DEADLINE_ALERT_DAYS, RECOMMENDER_ALERT_DAYS, "
                "UPCOMING_WINDOW_OPTIONS. Persist to a settings table; fall back to "
                "config.py defaults.", "Few days"],
        ["R1c", "TRACKER_PROFILE switch (roadmap §12). Ship faculty + industry profiles "
                "alongside postdoc, each with its own STATUS_VALUES, INTERVIEW_FORMATS, "
                "REQUIREMENT_DOCS, RESPONSE_TYPES.", "1–2 weeks"],
    ]
    t = Table(p1_rows, colWidths=[0.4 * inch, 5.5 * inch, 0.85 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 9),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9.5),
                ("FONT", (0, 1), (0, -1), "Times-Bold", 9),
                ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor(COBALT)),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
            ]
        )
    )
    story.append(t)
    story.append(Paragraph("P2 — quality of life (post-v1).", H3))
    p2_rows = [
        ["ID", "Item", "Effort"],
        ["R2a", "File attachments + per-document version metadata (roadmap §12).", "Multi-week"],
        ["R2b", "Responsive layout — wrap Quick-Add columns and filter bars below ~900px.", "Week"],
        ["R2c", "Keyboard shortcuts (/ search, n new, j/k row nav). The hotkey shield post-v0.14.0 already gates on single-char keys.", "Few days"],
        ["R2d", "In-app backup button: one-click copy postdoc.db to ~/Documents/aat-backup-YYYYMMDD.db.", "Half-day"],
        ["R2e", "Grouped reminder mailto — single email lists all owed positions per recommender.", "Half-day"],
    ]
    t = Table(p2_rows, colWidths=[0.4 * inch, 5.5 * inch, 0.85 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 9),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9.5),
                ("FONT", (0, 1), (0, -1), "Times-Bold", 9),
                ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor("#8a6d00")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))
    story.append(Image(str(chart_paths["effort"]), width=6.5 * inch, height=4.6 * inch))
    story.append(
        Paragraph(
            "Figure 6. Effort vs impact 2×2 for the twelve prioritized items.",
            CAPTION,
        )
    )
    story.append(PageBreak())

    # ── 16. Strategic roadmap + audience takeaways ────────────────────────
    story.append(Paragraph("16. Strategic Roadmap & Audience-specific Takeaways", H1))
    story.append(Paragraph("Suggested four-tier shipping order.", H3))
    for tier, items in [
        ("v0.14.0 (current branch, before merge)", ["B1, B2, B3 fixes (one fix commit each)"]),
        ("v0.15.0", ["R0a Recommender entity refactor", "R0d email + mailto", "R0b schema-UI wireup"]),
        ("v0.16.0", ["R1a Bulk operations", "R1b In-UI Settings page", "R2d Backup button", "R2e Grouped mailto"]),
        ("v0.17.0+", ["R1c TRACKER_PROFILE switch (postdoc + faculty + industry)",
                       "R2a File attachments + versioning", "R2b Responsive layout", "R2c Keyboard shortcuts"]),
    ]:
        story.append(Paragraph(f"<b>{tier}</b>", BODY))
        for it in items:
            story.append(Paragraph(f"• {it}", BULLET))

    story.append(Paragraph("For the marketing manager.", H3))
    story.append(
        Paragraph(
            "Position AAT as <b>“the personal tracking layer beneath Interfolio”</b> — "
            "the missing piece of the academic applicant's stack, not a replacement for the "
            "letter-delivery service. Target users: PhD candidates and postdocs on the "
            "academic market, comfortable with <i>streamlit run</i>, who already maintain "
            "a tracking spreadsheet they're frustrated with. Lead with the editorial design "
            "(S1), the urgency-banded Upcoming panel (S2), and the markdown export safety "
            "net (S3). Lead away from competing on browser extensions, AI tailoring, or "
            "mobile-first UX — those are explicit non-goals (DESIGN §1.3) and chasing them "
            "would dilute the niche.",
            BODY,
        )
    )
    story.append(Paragraph("For the product team.", H3))
    story.append(
        Paragraph(
            "Two near-quit moments per persona, all in the first two weeks, all anchored to "
            "the same root cause: <b>data-entry tax on the recommender model</b>. R0a is "
            "the most leveraged single bet in the backlog. Ship it before any new feature. "
            "After that, R1c (TRACKER_PROFILE switch) is the move that converts the "
            "architecture's promise into delivered breadth — and the move that lets P3-style "
            "developer-evaluators contribute upstream instead of forking.",
            BODY,
        )
    )
    story.append(Paragraph("For the engineering team.", H3))
    story.append(
        Paragraph(
            "Four verified findings ready to land as <i>fix:</i> commits today. B1 and B4 "
            "are small (half-day each). B3 is a 1–2 day sweep with a pinning test that "
            "asserts every nullable column has a UI binding. B2 plus R0d together are "
            "approximately one day including a migration. The <i>config.py</i> invariant "
            "harness (config.py:123–148) is your friend for the larger R0a refactor; "
            "extend the invariants to cover the new join table on Day 1 of that work.",
            BODY,
        )
    )
    story.append(PageBreak())

    # ── 17. Appendix A — verified refs ────────────────────────────────────
    story.append(Paragraph("17. Appendix A — Verified Code References", H1))
    story.append(
        Paragraph(
            "Every load-bearing file:line reference cited in the body of this report was "
            "checked against the current source on branch <i>feat/ui-redesign-v0.14.0</i> "
            "(commit 2ded3ba). The table below records the verification result.",
            BODY,
        )
    )
    rows = [
        ["Reference", "Claim", "Verification result"],
        ["database.py:135–148", "recommenders schema (per-position, no email column)", "Confirmed"],
        ["database.py:77–94", "10 nullable positions columns unused by UI", "Confirmed"],
        ["database.py:506–510", "R1 cascade fires on applied_date NULL→non-NULL", "Confirmed (P1 claim reclassified)"],
        ["database.py:629", "R2 cascade fires on add_interview", "Confirmed"],
        ["database.py:707–719", "delete_interview has no reverse cascade", "Confirmed (real defect)"],
        ["pages/3_Recommenders.py:142", "mailto built with no To field", "Confirmed"],
        ["pages/3_Recommenders.py:240", "_build_compose_mailto callsite", "Confirmed"],
        ["pages/3_Recommenders.py:311", "Recommender add path (per-position)", "Confirmed"],
        ["config.py:45–53", "STATUS_VALUES pipeline (postdoc-shaped)", "Confirmed"],
        ["config.py:265", "INTERVIEW_FORMATS = ['Phone','Video','Onsite','Other']", "Confirmed"],
        ["config.py:286–295", "REQUIREMENT_DOCS hardcoded list", "Confirmed"],
        ["config.py:320–322", "DEADLINE_ALERT_DAYS, RECOMMENDER_ALERT_DAYS", "Confirmed"],
        ["config.py:123–148", "Import-time invariants on STATUS/COLORS/LABELS", "Confirmed"],
        ["app.py:336–410", "Upcoming panel + urgency banding", "Confirmed"],
        ["app.py:19", "layout='wide' set unconditionally", "Confirmed"],
        ["ui.py:1265", "Hotkey shield (post-v0.14.0 narrowed to single-char)", "Confirmed"],
        ["DESIGN.md §1.3", "Explicit non-goals (no auth, cloud, mobile-first, …)", "Confirmed"],
        ["DESIGN.md §9.3", "R1/R2/R3 cascade documentation", "Confirmed"],
    ]
    t = Table(rows, colWidths=[1.7 * inch, 3.0 * inch, 2.15 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Times-Roman", 8.5),
                ("FONT", (0, 0), (-1, 0), "Times-Bold", 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE8DA")),
                ("FONT", (0, 1), (0, -1), "Courier", 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(RULE)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # ── 18. Appendix B + References ───────────────────────────────────────
    story.append(Paragraph("18. Appendix B — Methodology Limitations + References", H1))
    story.append(Paragraph("Limitations.", H3))
    for txt in [
        "Simulated personas only. No live human users, no telemetry, no recorded sessions. "
        "Friction frequencies and trust-index trajectories are reasoned, not measured.",
        "Three personas are a deliberately small sample chosen for diversity (postdoc / "
        "faculty / industry-hybrid). A real study should add at least one mobile-first user, "
        "one international applicant, and one user with accessibility needs.",
        "Competitive analysis is desk research from public marketing pages and review sites; "
        "no hands-on trials of competitors were conducted.",
        "Severity ratings in the friction heatmap are composite expert judgements, not "
        "user-elicited Likert scores.",
        "The B1 defect (R2-delete asymmetry) was verified in source but not reproduced in a "
        "running app. A pinning test should accompany its fix.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))

    story.append(Paragraph("References.", H3))
    refs = [
        "Interfolio Dossier — https://www.interfolio.com/dossier/",
        "Interfolio pricing reference — https://www.trustradius.com/products/interfolio-dossier/pricing",
        "Academic Jobs Online — https://academicjobsonline.org/ajo",
        "Versatile PhD — https://versatilephd.com/",
        "Huntr — https://huntr.co",
        "Teal HQ — https://www.tealhq.com",
        "Simplify — https://simplify.jobs",
        "JibberJobber — https://www.jibberjobber.com/pricing.php",
        "Notion job-applications template — https://www.notion.com/templates/job-applications",
        "Etsy Psych Postdoc Tracker — https://www.etsy.com/listing/4310751919/psych-postdoc-application-tracker",
        "Job-tracker comparison (Prentus) — https://prentus.com/blog/we-found-the-5-best-job-tracker-tools-on-the-market",
        "JobSync (GitHub) — https://github.com/Gsync/jobsync",
        "JobHunt (GitHub) — https://github.com/jamerst/JobHunt",
        "AAT source — https://github.com/YuZh98/academic-application-tracker  (branch feat/ui-redesign-v0.14.0 @ 2ded3ba)",
        "Keep a Changelog — https://keepachangelog.com/en/1.1.0/",
        "Semantic Versioning — https://semver.org/spec/v2.0.0.html",
    ]
    for i, r in enumerate(refs, 1):
        story.append(Paragraph(f"[{i}] {r}", BULLET))

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "<i>End of report. Regenerate with</i> "
            "<font face='Courier'>.venv/bin/python scripts/build_ux_report.py</font>",
            META,
        )
    )

    # ── Footer (page numbers) ─────────────────────────────────────────────
    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Times-Italic", 8)
        canvas.setFillColor(colors.HexColor(RULE))
        canvas.drawString(
            0.75 * inch,
            0.45 * inch,
            "Academic Application Tracker  ·  UX Field Study  ·  2026-05-22",
        )
        canvas.drawRightString(
            LETTER[0] - 0.75 * inch, 0.45 * inch, f"Page {doc_.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return PDF_PATH


def main() -> None:
    print("Generating charts…")
    charts = {
        "radar": chart_persona_radar(),
        "heatmap": chart_friction_heatmap(),
        "churn": chart_churn_timeline(),
        "scope": chart_retained_scope(),
        "effort": chart_effort_impact(),
        "matrix": chart_competitor_matrix(),
    }
    for name, p in charts.items():
        print(f"  · {name}: {p.relative_to(REPO)}")
    print("Building PDF…")
    pdf = build_pdf(charts)
    print(f"\nDone → {pdf.relative_to(REPO)}")
    print(f"Size:  {pdf.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
