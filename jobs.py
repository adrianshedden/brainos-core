#!/usr/bin/env python3
"""List the brain's skills, say which are due, and mark one done.

python3 scripts/jobs.py list <brain>                 (inside a brain; in the kit it is jobs.py)
python3 scripts/jobs.py done <brain> <skill-name>    for example: whats-on-my-plate

This is a to-do list for the skills, not the organiser. The organiser (one record per person, and
the "about me", "how I work" and tone pages drafted from the person's own material) is part of the
paid edition.
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

CADENCE_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}
CADENCE_RE = re.compile(r"^Cadence:\s*(daily|weekly|monthly|as-needed)\s*$", re.IGNORECASE)


def require_brain(brain):
    brain = Path(brain)
    if not (brain / "brain.yaml").is_file():
        raise SystemExit(f"{brain} is not a brain folder (no brain.yaml). Create one with create_brain.py first.")
    return brain


def jobs(brain):
    """Every skills/<name>/SKILL.md mapped to its declared cadence, default as-needed."""
    out = {}
    for f in sorted((Path(brain) / "skills").glob("*/SKILL.md")):
        cadence = "as-needed"
        for line in f.read_text(encoding="utf-8").splitlines():
            m = CADENCE_RE.match(line.strip())
            if m:
                cadence = m.group(1).lower()
                break
        out[f.parent.name] = cadence
    return out


def state_path(brain):
    return Path(brain) / "skills" / "jobs-state.json"


def a_date(value):
    """True if this is a date we wrote. A hand-edited or foreign value is ignored, not fatal."""
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def load_state(brain):
    """When each job was last marked done. An unreadable, hand-mangled or foreign state file counts
    as nothing done yet rather than crashing; the next `done` writes a clean one."""
    try:
        data = json.loads(state_path(brain).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {name: value for name, value in data.items() if a_date(value)}


def save_state(brain, state):
    state_path(brain).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_due(cadence, last_done, today):
    """None = no fixed cadence (as-needed); otherwise True/False."""
    if cadence == "as-needed":
        return None
    if last_done is None:
        return True
    return date.fromisoformat(last_done) + timedelta(days=CADENCE_DAYS[cadence]) <= today


def list_jobs(brain, today=None):
    today = today or date.today()
    brain = require_brain(brain)
    state = load_state(brain)
    rows = []
    for name, cadence in jobs(brain).items():
        last_done = state.get(name)
        due = is_due(cadence, last_done, today)
        if due is None:
            status = "no fixed cadence"
        elif due and last_done is None:
            status = "due (never done)"
        elif due:
            status = f"due (last done {last_done})"
        else:
            status = f"not due (last done {last_done})"
        rows.append((name, cadence, status))
    return rows


def _skill_name(text):
    """whats-on-my-plate, skills/whats-on-my-plate/SKILL.md and whats-on-my-plate.md all name one skill."""
    name = text.strip().rstrip("/")
    for suffix in ("/SKILL.md", ".md"):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name[len("skills/"):] if name.startswith("skills/") else name


def mark_done(brain, job, today=None):
    today = today or date.today()
    brain = require_brain(brain)
    available = jobs(brain)
    job = _skill_name(job)
    if job not in available:
        raise SystemExit(f"No such skill: {job}. Available: {', '.join(sorted(available)) or '(none)'}")
    state = load_state(brain)
    state[job] = today.isoformat()
    save_state(brain, state)
    return state[job]


def main(argv):
    if len(argv) < 3 or argv[1] not in ("list", "done"):
        raise SystemExit("Usage: python3 scripts/jobs.py list <brain>\n"
                          "   or: python3 scripts/jobs.py done <brain> <skill-name>")
    cmd, brain = argv[1], argv[2]
    if cmd == "list":
        rows = list_jobs(brain)
        if not rows:
            print("No skills in skills/ yet.")
        for name, cadence, status in rows:
            print(f"{name:<24} {cadence:<10} {status}")
    else:
        if len(argv) != 4:
            raise SystemExit("Usage: python3 scripts/jobs.py done <brain> <skill-name>")
        done_date = mark_done(brain, argv[3])
        print(f"Marked {argv[3]} done on {done_date}.")


if __name__ == "__main__":
    main(sys.argv)
