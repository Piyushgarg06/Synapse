"""Slop linter enforcing prose and design standards from sections 3 and 7.6."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
WEB_DIR = SCRIPT_DIR.parent
DOCS_DIR = WEB_DIR / "docs"
TERMS_FILE = SCRIPT_DIR / "slop_terms.txt"

# Emoji regex range
EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F"  # Emoticons
    r"\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    r"\U0001F680-\U0001F6FF"  # Transport & Map
    r"\U0001F1E0-\U0001F1FF"  # Flags
    r"\U00002702-\U000027B0"
    r"\U000024C2-\U0001F251"
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols
    r"\U0001FA70-\U0001FAFF"
    r"]",
    flags=re.UNICODE,
)

BANNED_CSS_COLORS = ["#ff5f56", "#ffbd2e", "#27c93f"]


def load_banned_terms() -> list[str]:
    """Load banned slop terms from text file."""
    if not TERMS_FILE.exists():
        return []
    terms = []
    with open(TERMS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("#"):
                terms.append(t)
    return terms


def strip_code_blocks(text: str) -> tuple[str, list[str]]:
    """Strip fenced code blocks and inline code, returning clean prose lines."""
    # Remove code fences
    in_fence = False
    clean_lines = []
    for line in text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        
        # Remove inline code `...`
        line_no_inline = re.sub(r"`[^`]*`", "", line)
        # Remove markdown image syntax ![alt](url)
        line_no_img = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line_no_inline)
        clean_lines.append(line_no_img)

    return "\n".join(clean_lines), clean_lines


def lint_markdown_file(path: Path, banned_terms: list[str]) -> tuple[list[str], list[str]]:
    """Lint a markdown file for hard errors and advisory flags."""
    hard_errors = []
    advisories = []

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{path}: Cannot read file: {e}"], []

    prose, lines = strip_code_blocks(content)

    # 1. Banned terms
    for term in banned_terms:
        # Match whole word / boundary where possible
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        matches = pattern.finditer(prose)
        for m in matches:
            hard_errors.append(f"{path}: Banned slop term '{term}' found in prose.")

    # 2. Emojis
    if EMOJI_PATTERN.search(prose):
        hard_errors.append(f"{path}: Emoji character found in prose.")

    # 3. Em dashes outside code
    if "—" in prose or "\u2014" in prose:
        hard_errors.append(f"{path}: Em dash ('—') found in prose. Use period, comma, colon, or parentheses.")

    # 4. Exclamation marks outside code
    for idx, line in enumerate(lines, 1):
        if "!" in line:
            hard_errors.append(f"{path}:{idx}: Exclamation mark found in prose/heading: '{line.strip()}'")

    # 5. Placeholders in content
    placeholders = ["lorem ipsum", "TODO", "FIXME", "coming soon", "placeholder"]
    for ph in placeholders:
        pattern = re.compile(rf"\b{re.escape(ph)}\b", re.IGNORECASE)
        if pattern.search(prose):
            hard_errors.append(f"{path}: Placeholder text '{ph}' found in content.")

    # Advisories:
    # Bold lead-in ratio on lists
    list_items = [l.strip() for l in lines if l.strip().startswith("- ") or l.strip().startswith("* ")]
    if list_items:
        bold_leadins = [l for l in list_items if re.match(r"^[-*]\s+\*\*[^*]+\*\*", l)]
        if len(bold_leadins) / len(list_items) > 0.25:
            advisories.append(f"{path}: More than 25% of list items have bold lead-ins ({len(bold_leadins)}/{len(list_items)}).")

    # Callout count
    callout_count = sum(1 for l in content.splitlines() if l.strip().startswith("::: ") or l.strip().startswith("> [!"))
    if callout_count > 2:
        advisories.append(f"{path}: More than 2 callouts on page ({callout_count} found).")

    # Headings as questions or colon teasers
    for line in lines:
        if line.strip().startswith("#"):
            h_text = line.strip().lstrip("#").strip()
            if h_text.endswith("?"):
                advisories.append(f"{path}: Heading phrased as question: '{h_text}'.")
            if ":" in h_text and not h_text.startswith("Command:") and not h_text.startswith("Step"):
                advisories.append(f"{path}: Heading contains colon teaser: '{h_text}'.")

    return hard_errors, advisories


def lint_css_file(path: Path) -> tuple[list[str], list[str]]:
    """Lint a CSS file for banned design slop patterns."""
    hard_errors = []
    advisories = []

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{path}: Cannot read CSS: {e}"], []

    # 1. background-clip: text (gradient text)
    if "background-clip: text" in content or "-webkit-background-clip: text" in content:
        hard_errors.append(f"{path}: Banned gradient-text pattern 'background-clip: text' found.")

    # 2. Terminal-dot colors
    for color in BANNED_CSS_COLORS:
        if color in content.lower():
            hard_errors.append(f"{path}: Banned terminal-dot color '{color}' found.")

    # 3. backdrop-filter count (allow at most 1 single logged exception for sticky header)
    backdrop_count = content.count("backdrop-filter:")
    if backdrop_count > 1:
        hard_errors.append(f"{path}: More than 1 backdrop-filter found in CSS ({backdrop_count} found). Max 1 allowed.")

    # Advisories:
    # Gradients between hue 240 and 330
    hsl_matches = re.findall(r"hsl\s*\(\s*(\d+)", content)
    for h in hsl_matches:
        val = int(h)
        if 240 <= val <= 330:
            advisories.append(f"{path}: Gradient / color in purple/magenta range (hsl hue {val}).")

    return hard_errors, advisories


def run_slop_lint(target_dir: Path | None = None) -> int:
    """Run slop linting over all docs and styles."""
    base = target_dir or WEB_DIR
    banned_terms = load_banned_terms()

    all_hard_errors = []
    all_advisories = []

    # Find markdown files
    md_files = list(base.glob("**/*.md"))
    # Exclude FACTS.md, DECISIONS.md, prompt files, test_fixtures, node_modules, and dist
    docs_md = [
        f for f in md_files
        if "node_modules" not in f.parts
        and "test_fixtures" not in f.parts
        and "dist" not in f.parts
        and f.name not in ("FACTS.md", "DECISIONS.md", "synapse_docs_site_prompt.md", "README.md")
    ]

    for md in docs_md:
        errs, advs = lint_markdown_file(md, banned_terms)
        all_hard_errors.extend(errs)
        all_advisories.extend(advs)

    # Find CSS files
    css_files = [
        f for f in base.glob("**/*.css")
        if "node_modules" not in f.parts
        and "test_fixtures" not in f.parts
        and "dist" not in f.parts
    ]
    for css in css_files:
        errs, advs = lint_css_file(css)
        all_hard_errors.extend(errs)
        all_advisories.extend(advs)

    print("=== SLOP LINTER RESULTS ===")
    if all_hard_errors:
        print(f"FAILED: {len(all_hard_errors)} hard failure(s) found:")
        for e in all_hard_errors:
            print(f"  [HARD] {e}")
    else:
        print("PASSED: 0 hard failures.")

    if all_advisories:
        print(f"\nADVISORY FLAGS ({len(all_advisories)} for manual review):")
        for a in all_advisories:
            print(f"  [WARN] {a}")
    else:
        print("Advisory review: clean (0 flags).")

    return 1 if all_hard_errors else 0


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    sys.exit(run_slop_lint(target))
