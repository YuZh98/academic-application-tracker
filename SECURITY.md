# Security Policy

The Academic Application Tracker is a local-first, single-user
Streamlit app. The user runs it on their own machine against a local
SQLite database, so the threat surface is small. Even so, security
reports are welcome.

## Supported Versions

Only the current minor release line receives security updates. Older
versions are not patched; please upgrade.

| Version  | Supported          |
| -------- | ------------------ |
| 0.11.x   | Yes                |
| < 0.11   | No                 |

## Reporting a Vulnerability

Please report suspected vulnerabilities privately via GitHub's
security advisory form:

https://github.com/YuZh98/academic-application-tracker/security/advisories/new

Do **not** open a public issue or pull request for security bugs —
that exposes the problem before a fix is available.

This is a solo project with no SLA. Expect a best-effort response
within a few days. If a fix is warranted, it will land on the current
minor release line.

## Scope

In scope: application code shipped in this repo — `app.py`,
`pages/*.py`, `database.py`, `exports.py`, `config.py`.

Out of scope:

- The user's local SQLite database file and its contents
- The Python interpreter, operating system, or browser
- Third-party dependencies — report those upstream

## Acknowledgments

Reporters who would like public credit will be named in the release
notes for the version that ships the fix.
