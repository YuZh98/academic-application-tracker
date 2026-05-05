# tests/test_helpers.py
# Smoke tests for tests/helpers.py — Phase 7 cleanup CL3 lift target.
#
# The four lifted functions are exercised in earnest by every test in
# tests/test_recommenders_page.py + tests/test_export_page.py (114
# tests across the two files). These tests are tiny import-compat +
# pure-logic smoke checks for the one helper (`decode_mailto`) that
# can be tested without a Streamlit AppTest fixture.
#
# `link_buttons` / `download_buttons` / `download_button` need a live
# AppTest instance to exercise — their existing call-site coverage in
# the page-test files is the load-bearing contract.

import pytest

from tests.helpers import (
    decode_mailto,
    download_button,
    download_buttons,
    link_buttons,
)


def test_imports_exist():
    """Smoke check that every name listed in the CL3 lift is callable
    after the refactor — guards against an accidental rename / drop
    on a future test-helpers cleanup."""
    assert callable(link_buttons)
    assert callable(decode_mailto)
    assert callable(download_buttons)
    assert callable(download_button)


def test_decode_mailto_extracts_subject_and_body():
    """Round-trip a vanilla `mailto:?subject=…&body=…` URL — the most
    common shape produced by the Recommenders-page Compose button
    (Phase 5 T6)."""
    assert decode_mailto("mailto:?subject=hi&body=there") == {
        "subject": "hi",
        "body": "there",
    }


def test_decode_mailto_url_decodes_values():
    """Subject + body fields go through urllib URL-decoding so spaces
    (encoded as `+` or `%20`) and special characters arrive as
    plain text. The Compose button URL-encodes its body via
    `urllib.parse.quote`, so this round-trip must invert it."""
    decoded = decode_mailto("mailto:?subject=Re%3A%20follow-up&body=hi%20there")
    assert decoded["subject"] == "Re: follow-up"
    assert decoded["body"] == "hi there"


def test_decode_mailto_handles_missing_fields():
    """A `mailto:` URL with no query string still parses — both fields
    default to empty rather than raising KeyError. Defensive against
    a future `mailto:user@example.com` bare form (no body / subject)."""
    assert decode_mailto("mailto:") == {"subject": "", "body": ""}


def test_decode_mailto_rejects_non_mailto_scheme():
    """The scheme assert is the helper's only safety net — it surfaces
    a clear AssertionError when a caller passes the wrong URL type
    (e.g., a `https://...` link button URL) rather than silently
    returning empty values."""
    with pytest.raises(AssertionError, match="mailto: scheme"):
        decode_mailto("https://example.com/?subject=hi")
