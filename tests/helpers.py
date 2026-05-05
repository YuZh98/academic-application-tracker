# tests/helpers.py
# Shared AppTest helpers — wrap `at.get('<element>')` for element types
# that AppTest 1.56 does not surface via a typed accessor (link_button,
# download_button as of Streamlit 1.57). Each helper returns the
# UnknownElement instances Streamlit produces for those elements; the
# caller then reads `.proto.<field>` to verify rendered properties.
#
# Lift candidates surface as "we use this in two test files" — these
# four helpers were duplicated across tests/test_recommenders_page.py
# (link button + mailto helpers, Phase 5 T6) and tests/test_export_page.py
# (download button helpers, Phase 6 T5). Phase 7 cleanup CL3 hoists them
# here so future tests (CL4 polish work, post-CL5 cohesion-smoke,
# ongoing tier work) reach for one place.
#
# Architecture rule (DESIGN §2): this module imports
# `streamlit.testing.v1` (AppTest type) and `urllib.parse` only — no
# project-internal imports. Pure test utility.

from urllib.parse import parse_qs, urlparse

from streamlit.testing.v1 import AppTest


def link_buttons(at: AppTest) -> list:
    """All link buttons on the page, as UnknownElement instances. Each
    has ``.proto.label`` and ``.proto.url`` attributes.

    AppTest 1.56 has no typed `at.link_button` accessor — link buttons
    surface via `at.get('link_button')` whose `.proto` carries the
    LinkButton protobuf with `.label`, `.url`, `.id` fields."""
    return list(at.get("link_button"))


def decode_mailto(url: str) -> dict[str, str]:
    """Parse a ``mailto:?subject=…&body=…`` URL into a {'subject', 'body'}
    dict with the values URL-decoded. Verifies the scheme so a malformed
    URL surfaces a clear AssertionError rather than silently returning
    empty values."""
    parsed = urlparse(url)
    assert parsed.scheme == "mailto", (
        f"Compose URL must use the mailto: scheme; got {url!r}"
    )
    qs = parse_qs(parsed.query, keep_blank_values=True)
    return {
        "subject": qs.get("subject", [""])[0],
        "body":    qs.get("body",    [""])[0],
    }


def download_buttons(at: AppTest) -> list:
    """All download buttons on the page, as UnknownElement instances.
    AppTest 1.56 has no typed `at.download_button` accessor — they
    surface via `at.get('download_button')` whose `.proto` carries
    the DownloadButton protobuf with `.label`, `.disabled`, `.url`,
    `.id` fields.

    Note: the bytes content (`data` arg) and file_name arg are NOT on
    the proto — they're stored behind a mock media URL. Tests that
    pin those two contracts use source-grep on `pages/4_Export.py`
    instead of element-tree assertions."""
    return list(at.get("download_button"))


def download_button(at: AppTest, filename: str):
    """Look up the download button for a given filename by its locked
    widget key (`f"export_download_{filename}"`). Returns the matching
    UnknownElement (raises AssertionError if missing)."""
    target_key = f"export_download_{filename}"
    matching = [b for b in download_buttons(at) if b.proto.id.endswith(target_key)]
    assert matching, (
        f"Expected a download button with key {target_key!r}; "
        f"got button ids: {[b.proto.id for b in download_buttons(at)]!r}"
    )
    return matching[0]
