#!/usr/bin/env python3
"""Keep a brain's level 1 the same at every AI's front door.

  python3 scripts/level1.py check <brain>   exit 1, and say where, if the copies differ
  python3 scripts/level1.py sync <brain>    copy CLAUDE.md's words to GEMINI.md and the top of AGENTS.md

Level 1 (what the brain is, who it is for, how to start, the rules) is written once in the kit
(template/LEVEL1.md). create_brain.py copies it word for word to three front doors, because each AI
opens a different one by itself: CLAUDE.md (Claude), GEMINI.md (Gemini) and a marked block at the very
top of AGENTS.md (Codex in the ChatGPT app, Cursor and most others). In a brain, CLAUDE.md is the copy
you edit; sync carries the change to the other two. Plain Python 3, no internet, changes nothing on check.
"""
import sys
from pathlib import Path

START = ("<!-- BrainOS level 1: start. The same words as CLAUDE.md and GEMINI.md. "
         "To change them, edit CLAUDE.md, then run: python3 scripts/level1.py sync . -->")
END = "<!-- BrainOS level 1: end. Level 2 starts below. -->"
DOORS = ("CLAUDE.md", "GEMINI.md", "AGENTS.md")
USAGE = "Usage: python3 scripts/level1.py check|sync <brain-folder>"


def block(level1):
    """The level 1 block that opens AGENTS.md."""
    return f"{START}\n\n{level1.strip()}\n\n{END}\n"


def join(level1, level2):
    """AGENTS.md: the level 1 block, then the level 2 manual."""
    return block(level1) + "\n" + level2.lstrip()


def split(agents):
    """AGENTS.md -> (level 1 words, level 2 manual). (None, agents) when the block is missing or broken."""
    if not agents.startswith(START) or END not in agents:
        return None, agents
    inner, rest = agents[len(START):].split(END, 1)
    return inner.strip(), rest.lstrip("\n")


def check(brain):
    """A list of plain-English problems. Empty means every front door says the same level 1."""
    brain = Path(brain)
    problems = []
    texts = {}
    for name in DOORS:
        try:
            texts[name] = (brain / name).read_text(encoding="utf-8")
        except OSError:
            problems.append(f"{name} is missing")
    if problems:
        return problems
    claude = texts["CLAUDE.md"].strip()
    if texts["GEMINI.md"].strip() != claude:
        problems.append("GEMINI.md does not match CLAUDE.md")
    inner, _ = split(texts["AGENTS.md"])
    if inner is None:
        problems.append("AGENTS.md does not start with the level 1 block")
    elif inner != claude:
        problems.append("the level 1 block at the top of AGENTS.md does not match CLAUDE.md")
    return problems


def sync(brain):
    """Copy CLAUDE.md to GEMINI.md and the AGENTS.md block. Level 2 in AGENTS.md is kept as it is."""
    brain = Path(brain)
    level1 = (brain / "CLAUDE.md").read_text(encoding="utf-8").strip() + "\n"
    agents_path = brain / "AGENTS.md"
    agents = agents_path.read_text(encoding="utf-8") if agents_path.is_file() else ""
    _, level2 = split(agents)
    (brain / "GEMINI.md").write_text(level1, encoding="utf-8")
    agents_path.write_text(join(level1, level2), encoding="utf-8")
    return check(brain)


def main(argv):
    if len(argv) != 3 or argv[1] not in ("check", "sync"):
        raise SystemExit(USAGE)
    problems = (check if argv[1] == "check" else sync)(argv[2])
    if problems:
        print("Level 1 copies differ:\n- " + "\n- ".join(problems)
              + "\nFix: edit CLAUDE.md, then run python3 scripts/level1.py sync .")
        return 1
    print("Level 1 is the same in CLAUDE.md, GEMINI.md and the top of AGENTS.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
