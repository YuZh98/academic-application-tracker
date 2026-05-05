# Dev Setup

_Install + run commands for first-time clone or re-setup of the Academic Application Tracker._

Local install and run commands for the Academic Application Tracker. For **why**
each component was chosen, see
[DESIGN §3 Technology Stack](../../DESIGN.md#3-technology-stack).
For **version pins** and environment conventions, see
[GUIDELINES §1 Environment](../../GUIDELINES.md#1-environment).

---

## Prerequisites

- Python 3.14 (Homebrew or system install)
- A POSIX shell (`bash` / `zsh`) for the `source` command below
- `git` (for cloning; not required at runtime)

The app is single-user and runs locally — no server, no cloud, no
credentials to manage.

---

## Install

From the project root, first-time setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install streamlit plotly pandas
pip freeze > requirements.txt
```

On a fresh clone where `requirements.txt` already exists, replace the
third line with `pip install -r requirements.txt` so the pinned versions
reproduce exactly.

---

## Run

```bash
source .venv/bin/activate
streamlit run app.py
# → http://localhost:8501
```

Leave the venv active for the rest of the session. If you open a new
shell, re-activate it before running `pytest` or any project script.
