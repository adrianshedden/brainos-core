#!/usr/bin/env python3
"""Check a brain folder: python3 tests/check_brain.py <brain>
Every file declared in brain.yaml exists, CLAUDE.md and AGENTS.md are readable, and no personal
identifiers (the owner's names, emails, paths, chat IDs) appear anywhere in the folder."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import level1  # noqa: E402

# Not the brain's own text: the person's raw exports and the downloaded kit. Never scanned as brain files.
NOT_BRAIN = ("exports", "kit")

PERSONAL = [r"\badrian\b", r"\brian\b", r"shedden", r"hotmail", r"/users/", r"@s\.whatsapp\.net", r"@g\.us",
            r"@lid\b", r"metafactory", r"metanova", r"!\w+:beeper", r"\bbeeper\b"]


def declared_files(brain):
    out, inside = [], False
    for line in (Path(brain) / "brain.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("files:"):
            inside = True
        elif inside and line.startswith("  - "):
            out.append(line[4:].strip())
        elif inside and line.strip() and not line.startswith(("#", " ")):
            inside = False
    return out


def check(brain):
    brain = Path(brain)
    problems = []
    if not (brain / "brain.yaml").is_file():
        return ["brain.yaml is missing"]
    declared = declared_files(brain)
    if not declared:
        problems.append("brain.yaml declares no files")
    for rel in declared:
        if not (brain / rel).is_file():
            problems.append(f"declared file missing: {rel}")
    problems += level1.check(brain)
    for spine in ("CLAUDE.md", "GEMINI.md", "AGENTS.md"):
        try:
            if len((brain / spine).read_text(encoding="utf-8").strip()) < 200:
                problems.append(f"{spine} is too short to be useful")
        except OSError:
            problems.append(f"{spine} is not readable")
    for p in sorted(brain.rglob("*.md")):
        if p.relative_to(brain).parts[0] in NOT_BRAIN[1:]:
            continue
        if "{{" in p.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"unfilled placeholder in {p.relative_to(brain).as_posix()}")
    for p in sorted(brain.rglob("*")):
        if p.is_file() and p.relative_to(brain).parts[0] not in NOT_BRAIN[1:]:
            text = p.read_bytes().decode("utf-8", errors="replace").lower()
            for pat in PERSONAL:
                if re.search(pat, text) or re.search(pat, str(p.relative_to(brain)).lower()):
                    problems.append(f"personal identifier /{pat}/ found in {p.relative_to(brain).as_posix()}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 tests/check_brain.py <brain>")
    found = check(sys.argv[1])
    print("\n".join(found) if found else "Brain OK")
    sys.exit(1 if found else 0)
