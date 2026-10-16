#!/usr/bin/env python3
"""Import a LinkedIn data archive: python3 importers/linkedin.py <archive.zip or folder> <brain>

Reads Connections, Profile, Positions and messages CSVs. Connections join the brain's one people list
(people.jsonl), messages its interactions log (interactions.jsonl): in network/, or in memory/people/ when
the brain has no network domain. Profile and positions go to memory/profile/. A missing or unreadable
file is reported and skipped. No network."""
import csv
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import merge_people, replace_interactions, require_brain, write_text, write_yaml  # noqa: E402

# file -> columns that identify its header row (LinkedIn puts a "Notes:" preamble above some headers)
FILES = {
    "connections.csv": {"first name", "last name"},
    "profile.csv": {"first name", "headline"},
    "positions.csv": {"company name", "title"},
    "messages.csv": {"from", "content"},
}


def _read_members(archive):
    """Return {lowercase basename: text} without extracting anything to disk."""
    archive = Path(archive)
    found = {}
    if archive.is_dir():
        for p in archive.rglob("*.csv"):
            found.setdefault(p.name.lower(), p.read_bytes())
    else:
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if not info.is_dir() and info.filename.lower().endswith(".csv"):
                    found.setdefault(info.filename.replace("\\", "/").split("/")[-1].lower(), zf.read(info))
    return {k: v.decode("utf-8-sig", errors="replace") for k, v in found.items()}


def parse_rows(text, required):
    """Skip any preamble, find the header row, return a list of dicts. None if no header."""
    rows = list(csv.reader(io.StringIO(text, newline="")))
    for i, row in enumerate(rows):
        cells = [c.strip().lower() for c in row]
        if required <= set(cells):
            header = [c.strip() for c in row]
            out = []
            for r in rows[i + 1:]:
                if not any(c.strip() for c in r):
                    continue
                out.append({h: (r[j].strip() if j < len(r) else "") for j, h in enumerate(header)})
            return out
    return None


def _get(row, *names):
    lower = {k.lower(): v for k, v in row.items()}
    for n in names:
        if lower.get(n.lower()):
            return lower[n.lower()]
    return ""


def run(archive, brain):
    brain = require_brain(brain)
    members = _read_members(archive)
    result = {"connections": 0, "positions": 0, "messages": 0, "profile": False, "skipped": []}
    parsed = {}
    for name, required in FILES.items():
        if name not in members:
            result["skipped"].append({"file": name, "reason": "not in the archive"})
            continue
        rows = parse_rows(members[name], required)
        if rows is None:
            result["skipped"].append({"file": name, "reason": "header row not found"})
            continue
        parsed[name] = rows

    if "connections.csv" in parsed:
        people = [{
            "name": f"{_get(r, 'First Name')} {_get(r, 'Last Name')}".strip(),
            "company": _get(r, "Company"),
            "position": _get(r, "Position"),
            "emails": [_get(r, "Email Address")],
            "url": _get(r, "URL"),
            "connected_on": _get(r, "Connected On"),
        } for r in parsed["connections.csv"]]
        merge_people(brain, "linkedin", people)
        result["connections"] = len(people)

    if "profile.csv" in parsed and parsed["profile.csv"]:
        p = parsed["profile.csv"][0]
        lines = [f"# {_get(p, 'First Name')} {_get(p, 'Last Name')}".rstrip(), ""]
        for label, key in (("Headline", "Headline"), ("Industry", "Industry"), ("Location", "Geo Location")):
            if _get(p, key):
                lines.append(f"- {label}: {_get(p, key)}")
        if _get(p, "Summary"):
            lines += ["", _get(p, "Summary")]
        write_text(brain, "memory/profile/linkedin-profile.md", "\n".join(lines) + "\n")
        result["profile"] = True

    if "positions.csv" in parsed:
        pos = [{
            "company": _get(r, "Company Name"),
            "title": _get(r, "Title"),
            "location": _get(r, "Location"),
            "started": _get(r, "Started On"),
            "finished": _get(r, "Finished On"),
            "description": _get(r, "Description"),
            "source": "linkedin",
        } for r in parsed["positions.csv"]]
        write_yaml(brain, "memory/profile/linkedin-positions.yaml", pos,
                   "LinkedIn positions. Written by importers/linkedin.py; re-running replaces this file.")
        result["positions"] = len(pos)

    if "messages.csv" in parsed:
        msgs = []
        for i, r in enumerate(parsed["messages.csv"], 1):
            when = _get(r, "DATE")
            msgs.append({
                "id": f"linkedin_message_{i:05d}",
                "type": "linkedin_message",
                "date": when[:10],
                "time": when[11:16] or None,
                "conversation": _get(r, "CONVERSATION TITLE") or _get(r, "CONVERSATION ID"),
                "from": _get(r, "FROM"),
                "to": _get(r, "TO"),
                "subject": _get(r, "SUBJECT"),
                "content": _get(r, "CONTENT"),
            })
        replace_interactions(brain, "linkedin", msgs)
        result["messages"] = len(msgs)
    return result


def main(argv):
    if len(argv) != 3:
        raise SystemExit("Usage: python3 importers/linkedin.py <archive.zip> <brain-folder>")
    try:
        r = run(argv[1], argv[2])
    except (OSError, zipfile.BadZipFile) as e:
        raise SystemExit(f"Could not read the LinkedIn archive: {e}")
    print(f"LinkedIn: {r['connections']} connections, {r['positions']} positions, "
          f"{r['messages']} messages, profile {'imported' if r['profile'] else 'not found'}.")
    for s in r["skipped"]:
        print(f"Skipped {s['file']}: {s['reason']}.")


if __name__ == "__main__":
    main(sys.argv)
