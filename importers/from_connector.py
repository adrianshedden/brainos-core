#!/usr/bin/env python3
"""Save what an AI read through live connectors: python3 importers/from_connector.py <brain> <file.json>

For the AI. After you read a live connection (calendar, email, Drive, WhatsApp through Beeper, Notion,
Slack...), write who and when into a JSON file, then run this. It merges into the brain's one people list
and interactions log, the same files and the same merge the export importers use (importers/common.py).

The JSON file:
  {"people":       [{"name": "Sam Lee", "email": "sam@example.com", "phone": "+44 7700 900123",
                     "source": "gmail"}],
   "interactions": [{"when": "2026-10-19T09:30", "with": ["Sam Lee"], "channel": "email",
                     "summary": "Agreed the launch date", "source": "gmail"}]}
- people: name or email is needed; email and phone are optional. interactions: when, with and channel
  are needed; summary is optional. Every entry needs a source: use the id from connections.yaml
  (google-calendar, gmail, google-drive, outlook-calendar, outlook-mail, onedrive, whatsapp, notion,
  slack, other-custom), not the name of the tool in between. It may end with the day it was read
  ("google-calendar, 2026-10-21", as SETUP.md writes it): that is the same source.
- when: YYYY-MM-DD, optionally followed by a time (2026-10-19T09:30 or 2026-10-19 09:30).

What it keeps, and what it never keeps:
- Append-only. Nothing already in the brain is changed or removed, and reading the same thing twice adds
  nothing: people are recognised by email, phone or name like every importer, and an interaction by its
  source, date, time, who and channel.
- Never whole messages: only a short summary (one line, at most 200 characters). Any other field in the
  JSON (a message body, a subject, an attachment) is dropped.
- Every line says where it came from and when: lines are saved under "<source>-live" (for example
  gmail-live), so a live read never mixes with an export of the same thing, and each carries read_on,
  the day it was read. People lines also carry source and confidence, like the rest of the brain.
- If anything in the file is wrong, it says what in one plain line and changes nothing.
- No network: it reads the JSON file on this machine and writes into the brain folder only."""
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import merge_people, people_home, replace_interactions, require_brain, slugify  # noqa: E402

SUMMARY_MAX = 200
LIVE = "-live"
# A source may carry the day it was read, as SETUP.md writes it ("google-calendar, 2026-10-21"): that day is
# already kept as read_on, so it is taken off the source and every read of one source stays under one id.
READ_DAY = re.compile(r"[\s,;:(-]*\d{4}-\d{2}-\d{2}\)?\s*$")

WHEN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$")
USAGE = "Usage: python3 importers/from_connector.py <brain-folder> <file.json>"


class BadFile(Exception):
    """The JSON file cannot be used. The message is one plain line for the person."""


def live_source(text):
    """'Google Calendar' or 'google-calendar, 2026-10-21' -> 'google-calendar-live'. The same id however the
    AI spelled it, with or without the day it was read."""
    s = slugify(READ_DAY.sub("", text), "")
    if s.endswith(LIVE):
        s = s[: -len(LIVE)]
    return s + LIVE if s else ""


def _text(v):
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else ""


def _strings(v):
    """A string or a list of strings -> list of non-empty strings, or None if it is something else."""
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        return None
    return [x for x in map(_text, v) if x]


def _when(v):
    """(date, time or None) from a when value, or None if it cannot be read."""
    m = WHEN.match(v.strip()) if isinstance(v, str) else None
    if not m:
        return None
    y, mo, d, hh, mm = m.groups()
    try:
        day = date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None
    if hh is not None and not (int(hh) < 24 and int(mm) < 60):
        return None
    return day, (f"{hh}:{mm}" if hh is not None else None)


def _summary(v):
    s = _text(v)
    return s if len(s) <= SUMMARY_MAX else s[: SUMMARY_MAX - 3].rstrip() + "..."


def parse(raw, today):
    """Check the whole file before anything is written. Returns ({source: [person]}, {source: [row]})."""
    try:
        data = json.loads(raw)
    except ValueError as e:
        line = f" (line {e.lineno}, column {e.colno})" if hasattr(e, "lineno") else ""
        raise BadFile(f"The file is not valid JSON{line}.")
    if not isinstance(data, dict) or not ({"people", "interactions"} & set(data)):
        raise BadFile('The file must be one JSON object with a "people" list, an "interactions" list, or both.')
    people, talks = {}, {}
    for key in ("people", "interactions"):
        items = data.get(key, [])
        if not isinstance(items, list):
            raise BadFile(f'"{key}" must be a list.')
        for n, item in enumerate(items, 1):
            where = f"Entry {n} in {key}"
            if not isinstance(item, dict):
                raise BadFile(f"{where} is not an object.")
            src = live_source(item.get("source")) if isinstance(item.get("source"), str) else ""
            if not src:
                raise BadFile(f'{where} has no "source" (for example "gmail").')
            if key == "people":
                name, emails, phones = _text(item.get("name")), _strings(item.get("email") or []), _strings(item.get("phone") or [])
                if emails is None or phones is None:
                    raise BadFile(f'{where} has an "email" or "phone" that is not text.')
                if not name and not emails:
                    raise BadFile(f'{where} has neither a "name" nor an "email".')
                person = {"name": name, "emails": [e.lower() for e in emails], "phones": phones, "read_on": today}
                people.setdefault(src, []).append({k: v for k, v in person.items() if v not in ("", [])})
            else:
                when, who, channel = _when(item.get("when")), _strings(item.get("with")), slugify(item.get("channel") or "", "")
                if when is None:
                    raise BadFile(f'{where} has a "when" that cannot be read: use YYYY-MM-DD, optionally with a time.')
                if not who:
                    raise BadFile(f'{where} has no "with" (who it was with).')
                if not channel:
                    raise BadFile(f'{where} has no "channel" (for example "email" or "meeting").')
                row = {"type": channel, "date": when[0], "time": when[1], "with": who, "read_on": today}
                if _summary(item.get("summary")):
                    row["summary"] = _summary(item.get("summary"))
                talks.setdefault(src, []).append(row)
    return people, talks


def _lines(path):
    return common._read_jsonl(path)  # the shared reader: a hand-broken line is skipped, never fatal


def _tidy(path, src):
    """Drop empty values from what <src> said about each person. merge_people leaves an empty phones list
    when it folds two reads of the same person together; without this, reading the same thing twice
    would change the file."""
    people = _lines(path)
    for p in people:
        said = p.get("from", {}).get(src)
        if isinstance(said, dict):
            p["from"][src] = {k: v for k, v in said.items() if v not in ("", None, [])}
    common._write_jsonl(path, people)


def _talk_key(row):
    return (row.get("date"), row.get("time"), tuple(sorted(w.lower() for w in row.get("with", []))), row.get("type"))


def run(brain, json_file, today=None):
    """Merge one JSON file of live reads into <brain>. Raises BadFile, having written nothing."""
    brain = require_brain(brain)
    today = today or date.today().isoformat()
    try:
        raw = Path(json_file).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise BadFile("The file is not text. Save the JSON as plain UTF-8 text.")
    people, talks = parse(raw, today)

    home = Path(brain) / people_home(brain)
    result = {"people": 0, "new_people": 0, "interactions": 0, "new_interactions": 0, "sources": []}
    before = len(_lines(home / "people.jsonl"))
    for src in sorted(people):
        # merge_people replaces what a source said, so hand it everything this source said before plus the
        # new entries: nothing is lost, and the same person read twice folds into one.
        earlier = [p["from"][src] for p in _lines(home / "people.jsonl") if src in p.get("from", {})]
        _tidy(merge_people(brain, src, earlier + people[src]), src)
        result["people"] += len(people[src])
    result["new_people"] = len(_lines(home / "people.jsonl")) - before

    for src in sorted(talks):
        rows = _lines(home / "interactions.jsonl")
        earlier = [r for r in rows if r.get("source") == src]
        seen, ids = {_talk_key(r) for r in earlier}, {r.get("id") for r in rows}
        new = []
        for row in talks[src]:
            if _talk_key(row) in seen:
                continue
            seen.add(_talk_key(row))
            base = "_".join(x for x in (slugify(src, "live").replace("-", "_"), row["date"],
                                        (row["time"] or "").replace(":", ""), row["type"],
                                        slugify(" ".join(row["with"]), "someone").replace("-", "_")) if x)
            rid, n = base, 2
            while rid in ids:
                rid, n = f"{base}_{n}", n + 1
            ids.add(rid)
            new.append(dict({"id": rid}, **{k: v for k, v in row.items() if v is not None}))
        if new:
            replace_interactions(brain, src, earlier + new)
        result["interactions"] += len(talks[src])
        result["new_interactions"] += len(new)
    result["sources"] = sorted(set(people) | set(talks))
    return result


def _args(argv):
    """<brain> <file.json>. The other order works too, since the brain is the folder with brain.yaml."""
    if len(argv) != 3:
        raise SystemExit(USAGE)
    a, b = argv[1], argv[2]
    if not (Path(a) / "brain.yaml").is_file() and (Path(b) / "brain.yaml").is_file():
        a, b = b, a
    return a, b


def main(argv):
    brain, json_file = _args(argv)
    try:
        r = run(brain, json_file)
    except BadFile as e:
        raise SystemExit(f"{json_file}: {e} Nothing was changed.")
    except OSError as e:
        raise SystemExit(f"Could not read {json_file}: {e.strerror or e}. Nothing was changed.")
    print(f"From live connections ({', '.join(r['sources']) or 'nothing'}): {r['people']} people read, "
          f"{r['new_people']} new to the brain; {r['interactions']} conversations and meetings read, "
          f"{r['new_interactions']} new, {r['interactions'] - r['new_interactions']} already there.")


if __name__ == "__main__":
    main(sys.argv)
