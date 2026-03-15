#!/usr/bin/env python3
"""Strip whole-line comments and emoji characters from text files in the repo.

Rules:
- Preserve shebang lines (first line starting with #!).
- Remove whole-line comments that start with '#' or '//' after optional whitespace.
- Remove HTML comments  from markdown files.
- Remove emoji characters using a Unicode regex.
- Operates on files with text-like extensions.
"""

from __future__ import annotations

import re
from pathlib import Path
import sys

TEXT_EXTS = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".dockerfile",
    "Dockerfile",
    ".ini",
    ".cfg",
    ".sh",
    ".env",
    ".gitignore",
    "",
}

RE_COMMENT = re.compile(r"^\s*(#|//).*$(\n)?", flags=re.MULTILINE)
RE_SHEBANG = re.compile(r"^#!")
RE_HTML_COMMENT = re.compile(r"", flags=re.DOTALL)
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF\U0001F1E6-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF]",
    flags=re.UNICODE,
)

ROOT = Path(__file__).resolve().parents[1]

def process_file(p: Path) -> bool:
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return False

    original = text

    lines = text.splitlines(keepends=True)
    out_lines = []
    for i, line in enumerate(lines):
        if i == 0 and RE_SHEBANG.match(line):
            out_lines.append(line)
            continue
        if re.match(r"^\s*(#|//)", line):
            continue
        out_lines.append(line)

    text = "".join(out_lines)
    text = RE_HTML_COMMENT.sub("", text)
    text = EMOJI_RE.sub("", text)

    if text != original:
        try:
            p.write_text(text, encoding="utf-8")
            return True
        except Exception:
            return False
    return False

def should_process(p: Path) -> bool:
    if p.is_dir():
        return False
    if p.name in {"LICENSE", "Makefile", "README.md"}:
        return True
    ext = p.suffix
    if p.name == "Dockerfile":
        return True
    if ext in TEXT_EXTS:
        return True
    return False

def main():
    changed = []
    for p in ROOT.rglob("*"):
        if not should_process(p):
            continue
        if process_file(p):
            changed.append(str(p.relative_to(ROOT)))
    print("Processed files:")
    for c in changed:
        print(" -", c)
    print(f"Total changed: {len(changed)}")

if __name__ == "__main__":
    main()
