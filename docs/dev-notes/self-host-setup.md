# Self-Host Setup

_For users who want to run the Academic Application Tracker on their own
laptop and keep their data private. If you want to contribute code, see
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) and
[`GUIDELINES.md`](../../GUIDELINES.md) instead._

The app is **local-first**: it runs on your machine, reads and writes a
single SQLite file beside the code, and never sends data anywhere. No
account, no cloud, no telemetry.

---

## Prerequisites

- **Python 3.11 or newer.** Check with:
  ```bash
  python3 --version
  ```
  If you see `Python 3.11.x` or higher, you're good. If `python3` is not
  found, install Python from [python.org/downloads](https://www.python.org/downloads/)
  or your system package manager (`brew install python` on macOS;
  `apt install python3 python3-venv` on Debian/Ubuntu).
- **`git`** for cloning the repo. macOS users will be prompted to
  install the Xcode Command Line Tools the first time they run `git`;
  on Debian/Ubuntu, `apt install git`.
- **A terminal app.** Terminal on macOS, Terminal / GNOME Terminal on
  Linux, WSL or Git Bash on Windows. PowerShell-only setups are not
  covered here.

---

## First-time install

```bash
git clone https://github.com/YuZh98/academic-application-tracker.git
cd academic-application-tracker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The `pip` upgrade step is harmless on a fresh install and resolves the
most common failure mode where an outdated pip stumbles on a recent wheel.

You only do this once. Subsequent runs just need the activation +
launch commands in the next section.

---

## Run and stop

Every session starts from inside the project folder:

```bash
cd academic-application-tracker
source .venv/bin/activate
streamlit run app.py
```

Streamlit prints a local URL (default `http://localhost:8501`) and
opens it in your default browser. The SQLite database is created on
first run; the empty-state screen walks you through adding your first
position.

**To stop the app**, press `Ctrl+C` in the terminal where it's running.
Closing the browser tab does not stop it.

**To restart**, run the same `streamlit run app.py` command again — your
data is preserved between sessions (it lives in the SQLite file, not in
the running process).

---

## Where your data lives

Three locations matter, all inside the project folder:

| Path | What it is | Backup priority |
|---|---|---|
| `postdoc.db` | The SQLite database — every position, application, interview, and recommender you've entered | 🔴 Critical |
| `exports/*.md` | Plaintext markdown snapshots (`OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`) auto-regenerated on every database write | 🟡 Optional (human-readable backup) |
| `.venv/` | Python virtual environment with installed packages | ⚪ Disposable — rebuildable from `requirements.txt` |

Both `postdoc.db` and `exports/` are listed in `.gitignore` on purpose.
`postdoc.db` contains every application detail you've entered **and the
names and emails of every recommender** — third parties who have not
consented to public disclosure. If you push it to a public fork, every
position, application status, and recommender contact becomes
permanently public, and git history rewrites are partial and slow.
Always run `git status` before staging, and never `git add -A` without
checking what's about to be committed.

The `exports/` files are **generated** — every successful save in the app
rewrites them. Editing them by hand has no effect; the next write
overwrites your edits.

---

## Backup and restore

The database is a single file. Backup is a single copy.

**Back up** (do this before any significant change, weekly minimum):

```bash
# Stop the app first (Ctrl+C in the running terminal).
cp postdoc.db postdoc.db.backup.$(date +%Y%m%d)
```

The dated suffix lets you keep multiple snapshots. Copy the file
somewhere outside the project folder (cloud storage, external drive)
if you want disaster-recovery protection.

**Restore** from a backup:

```bash
# Stop the app first.
cp postdoc.db.backup.YYYYMMDD postdoc.db
# Restart the app.
streamlit run app.py
```

**If you lose `postdoc.db` entirely** but still have the `exports/`
markdown files, you have a human-readable record of every position,
application, and recommender — but the app cannot import markdown back
into the database. Re-entry is manual. Treat exports as a safety net,
not a primary backup.

---

## Updating your installation

When the upstream repo ships a new release, pull the latest code. The
command below assumes a clean working tree — if you've edited project
files yourself, commit or stash them first to avoid a merge conflict.

```bash
cd academic-application-tracker
git pull
source .venv/bin/activate
pip install -r requirements.txt   # in case dependency versions changed
streamlit run app.py
```

Your `postdoc.db` is preserved across updates. `database.init_db()`
runs on every app start and auto-adds any known missing columns —
notably, any new document-requirement type added to the config. You do
not need to run a migration command manually. Breaking schema changes
are called out in [`CHANGELOG.md`](../../CHANGELOG.md) with a
`**Migration:**` block.

Skim `CHANGELOG.md` before pulling a new version to see what changed.

---

## Troubleshooting

**"Address already in use" / port 8501 taken.**
Another Streamlit instance is running, or a different process holds the
port. Either stop the other process or pick a different port:

```bash
streamlit run app.py --server.port 8502
```

**`streamlit: command not found`.**
The virtual environment is not activated, or you're in the wrong folder.
Run `cd academic-application-tracker && source .venv/bin/activate`, then
retry.

**`pip install` fails on a fresh clone.**
Upgrade pip first (`python -m pip install --upgrade pip`), then retry. If
it still fails, check that your Python version is 3.11 or newer
(`python3 --version`).

**App starts but shows an error on the dashboard.**
Stop the app, back up `postdoc.db`, then file an issue at
[github.com/YuZh98/academic-application-tracker/issues](https://github.com/YuZh98/academic-application-tracker/issues)
with the error text. Schema corruption is rare but can happen if the
file is edited by another tool while the app is running.

---

## Uninstall

The app has no system-level installer. To remove it:

```bash
# Back up postdoc.db first if you want to keep your data.
cd ..
rm -rf academic-application-tracker
```

The `.venv/` folder inside is the bulk of the disk usage (~200 MB);
deleting the whole project folder reclaims all of it.

---

## What's next

- For app features and daily-use workflow, see the main [`README.md`](../../README.md).
- For contributing code, see [`CONTRIBUTING.md`](../../CONTRIBUTING.md) and [`GUIDELINES.md`](../../GUIDELINES.md).
- For architecture and design rationale, see [`DESIGN.md`](../../DESIGN.md).
