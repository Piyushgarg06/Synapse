"""Unit tests for the slop linter verifying it catches all mandated violations."""

import sys
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# pyrefly: ignore [missing-import]
from slop_lint import lint_markdown_file, lint_css_file, load_banned_terms


def test_slop_linter_catches_all_violations():
    fixtures_dir = SCRIPT_DIR / "test_fixtures"
    banned_terms = load_banned_terms()

    # Test markdown fixture
    bad_md = fixtures_dir / "bad_prose.md"
    hard_errs_md, _ = lint_markdown_file(bad_md, banned_terms)

    errs_text = " ".join(hard_errs_md).lower()
    assert "seamless" in errs_text, "Failed to catch banned term 'seamless'"
    assert "powerful" in errs_text, "Failed to catch banned term 'powerful'"
    assert "emoji" in errs_text, "Failed to catch emoji"
    assert "em dash" in errs_text, "Failed to catch em dash"
    assert "exclamation mark" in errs_text, "Failed to catch exclamation mark"
    assert "todo" in errs_text, "Failed to catch TODO"
    assert "lorem ipsum" in errs_text, "Failed to catch lorem ipsum"

    # Test CSS fixture
    bad_css = fixtures_dir / "bad_style.css"
    hard_errs_css, _ = lint_css_file(bad_css)

    css_errs_text = " ".join(hard_errs_css).lower()
    assert "background-clip: text" in css_errs_text, "Failed to catch background-clip: text"
    assert "#ff5f56" in css_errs_text, "Failed to catch terminal dot color #ff5f56"
    assert "backdrop-filter" in css_errs_text, "Failed to catch excessive backdrop-filter"

    print("Slop linter self-test PASSED: All violations caught accurately.")
    return 0


if __name__ == "__main__":
    sys.exit(test_slop_linter_catches_all_violations())
