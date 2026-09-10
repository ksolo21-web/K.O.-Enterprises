#!/usr/bin/env python3
"""Static checks for territory-card automatic trigger coverage."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
CASES = ROOT / "examples" / "trigger-cases.json"

REQUIRED_DESCRIPTION_TERMS = (
    "automatically use this skill",
    "territory card",
    "territory map",
    "territory boundary",
    "work-inside-only",
    "work-both-sides",
    "missing territory coverage",
    "old territory-card conversion",
)

NEGATIVE_BOUNDARIES = (
    "geopolitical territories",
    "fantasy maps",
    "ordinary navigation",
    "sales-territory",
)


def extract_description(text: str) -> str:
    match = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    description = extract_description(text)
    errors = []
    if not description:
        errors.append("missing frontmatter description")
    for term in REQUIRED_DESCRIPTION_TERMS:
        if term not in description:
            errors.append(f"description missing required positive trigger term: {term}")
    for term in NEGATIVE_BOUNDARIES:
        if term not in description:
            errors.append(f"description missing negative boundary term: {term}")

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if len(cases.get("positive", [])) < 8:
        errors.append("need at least 8 positive trigger cases")
    if len(cases.get("negative", [])) < 5:
        errors.append("need at least 5 negative trigger cases")
    if len(cases.get("boundary", [])) < 2:
        errors.append("need at least 2 boundary trigger cases")

    report = {"status": "PASS" if not errors else "FAIL", "errors": errors}
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
