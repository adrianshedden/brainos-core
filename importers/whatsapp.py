#!/usr/bin/env python3
"""Import WhatsApp chat exports: python3 importers/whatsapp.py <export> <brain>

<export> is a chat .txt, a .zip of them, or a folder of them (loose .txt files, .zip exports, or both).
iPhone ("[15/03/2024, 09:41:22] Name: hi") and Android ("15/03/2024, 09:41 - Name: hi") layouts both
work. Odd lines never stop the run. No network.

Naming: Android names the file after the chat ("WhatsApp Chat with Sam.txt"). iPhone always calls it
_chat.txt and names the .zip after the chat ("WhatsApp Chat - Sam.zip"), so a generic file name takes
its chat name from the .zip, or from the unzipped folder. Each chat is saved as one file, named after
the chat. Re-importing the same chat replaces its file. A different chat with the same name is never
overwritten: it is saved with a number on the end (sam-2.md), and the printout says so.

Everyone in the chats joins the brain's one people list (people.jsonl) and each chat joins the
interactions log (interactions.jsonl): both in network/, or in memory/people/ when the brain has no
network domain. You are never listed as one of your own contacts. Before it writes anything, the importer
needs your own name as it shows in your WhatsApp chats, from (in this order):
  --me "<your name>"            given once; remembered in brain.yaml (whatsapp_names) for every later import
  brain.yaml whatsapp_names     set by an earlier --me
  the Name line in CLAUDE.md    used only when that exact name is one of the people in the chats
With none of these it stops, changes nothing, and asks which of the names in the chats is yours."""
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import dump_yaml, merge_people, replace_interactions, require_brain, slugify, write_text  # noqa: E402

D = r"(?P<d>\d{1,4}[./-]\d{1,2}[./-]\d{1,4})"
T = r"(?P<t>\d{1,2}[:.]\d{2}(?::\d{2})?(?:\s?[AaPp]\.?[Mm]\.?)?)"
IOS = re.compile(rf"^\[{D},?\s+{T}\]\s?(?P<rest>.*)$")
ANDROID = re.compile(rf"^{D},?\s+{T}\s+-\s(?P<rest>.*)$")


def _clean(line):
    return line.replace(" ", " ").replace("\xa0", " ").lstrip("‎‏﻿").rstrip("\r\n")


def _split_date(d):
    return [int(x) for x in re.split(r"[./-]", d)]


def _order(dates):
    """Decide day-first, month-first or year-first for a whole chat from its unambiguous dates."""
    parts = [_split_date(d) for d in dates]
    if any(len(re.split(r"[./-]", d)[0]) == 4 for d in dates):
        return "ymd"
    if any(p[0] > 12 for p in parts):
        return "dmy"
    if any(p[1] > 12 for p in parts):
        return "mdy"
    return "dmy"


def _parse_when(d, t, order):
    """Return ('YYYY-MM-DD', 'HH:MM') or (None, None) when it cannot be read."""
    try:
        a, b, c = _split_date(d)
        y, m, dd = (a, b, c) if order == "ymd" else ((c, b, a) if order == "dmy" else (c, a, b))
        if y < 100:
            y += 2000
        day = date(y, m, dd)
        mt = re.match(r"(\d{1,2})[:.](\d{2})(?:[:.]\d{2})?\s?([AaPp])?", t)
        hh, mm = int(mt.group(1)), int(mt.group(2))
        if mt.group(3):
            hh = hh % 12 + (12 if mt.group(3).lower() == "p" else 0)
        if hh > 23 or mm > 59:
            return None, None
        return day.isoformat(), f"{hh:02d}:{mm:02d}"
    except (ValueError, AttributeError):
        return None, None


def parse_chat(text):
    """Return (messages, system_count). Each message: dict(date, time, sender, text)."""
    raw = []  # [d, t, rest] then continuation lines appended to rest
    for line in text.splitlines():
        line = _clean(line)
        m = IOS.match(line) or ANDROID.match(line)
        if m:
            raw.append([m.group("d"), m.group("t"), m.group("rest")])
        elif raw:
            raw[-1][2] += "\n" + line  # continuation, or a line with no timestamp
    order = _order([r[0] for r in raw]) if raw else "dmy"
    messages, system = [], 0
    for d, t, rest in raw:
        if ": " not in rest.split("\n")[0] or "end-to-end encrypted" in rest:
            system += 1
            continue
        sender, body = rest.split(": ", 1)
        day, hhmm = _parse_when(d, t, order)
        messages.append({"date": day, "time": hhmm, "sender": sender.strip(), "text": body})
    return messages, system


# File names that say nothing about which chat is inside (iPhone's _chat.txt above all).
GENERIC = {"_chat", "chat", "whatsapp chat", ""}
PREFIX = re.compile(r"^WhatsApp Chat(\s+with|\s*-)?\s*", re.I)


def _is_generic(stem):
    return PREFIX.sub("", stem).strip().lower() in GENERIC


def _chat_name(filename, container=None):
    """The chat's name. A generic file name (_chat.txt) takes the name of the .zip or folder it came in."""
    stem = Path(filename).stem
    if _is_generic(stem) and container and not _is_generic(container):
        stem = container
    return PREFIX.sub("", stem).strip() or "chat"


def _from_zip(zpath):
    out = []
    with zipfile.ZipFile(zpath) as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            if info.filename.lower().endswith(".txt") and not info.is_dir() and "__MACOSX/" not in info.filename:
                name = info.filename.replace("\\", "/").split("/")[-1]
                out.append((name, zf.read(info).decode("utf-8-sig", errors="replace"), _chat_name(name, zpath.stem)))
    return out


def _read_exports(export):
    """Return [(filename, text, chat name)] for a .txt, a .zip of .txt files, or a folder of either."""
    export = Path(export)
    out = []
    if export.is_dir():
        for p in sorted(export.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() == ".txt":
                folder = p.parent.name if PREFIX.match(p.parent.name) else None  # an unzipped iPhone export
                out.append((p.name, p.read_bytes().decode("utf-8-sig", errors="replace"), _chat_name(p.name, folder)))
            elif p.suffix.lower() == ".zip" and zipfile.is_zipfile(p):
                out.extend(_from_zip(p))
    elif zipfile.is_zipfile(export):
        out.extend(_from_zip(export))
    else:
        parent = export.parent.name if PREFIX.match(export.parent.name) else None
        out.append((export.name, export.read_bytes().decode("utf-8-sig", errors="replace"), _chat_name(export.name, parent)))
    return out


def _front_value(text, key):
    """One value from a chat file's front matter, or None."""
    for line in text.split("\n---", 1)[0].splitlines():
        if line.startswith(f"{key}: "):
            try:
                return json.loads(line[len(key) + 2:])
            except ValueError:
                return None
    return None


def _slot(brain, name, opens_with, taken):
    """The file for this chat: its own file if it was imported before, else the first free name.
    Never a file that holds a different chat. <taken> maps the names used in this run to their chat."""
    base, n = slugify(name, "chat"), 1
    while True:
        slug = base if n == 1 else f"{base}-{n}"
        path = Path(brain) / "memory/conversations/whatsapp" / f"{slug}.md"
        if slug in taken:
            if taken[slug] == (name, opens_with):
                return slug
        elif not path.is_file():
            return slug
        else:
            old = path.read_text(encoding="utf-8")
            if _front_value(old, "chat") == name and _front_value(old, "opens_with") in (None, opens_with):
                return slug  # the same chat, imported again
        n += 1


def _front(text):
    """The front matter of a saved chat: scalars, and the participants list."""
    out, key = {}, None
    for line in text.split("\n---", 1)[0].splitlines()[1:]:
        if line.startswith("  - ") and key:
            try:
                out[key].append(json.loads(line[4:]))
            except ValueError:
                pass
        elif ": " in line or line.endswith(":"):
            key, _, value = line.partition(":")
            value = value.strip()
            try:
                out[key] = json.loads(value) if value else []
            except ValueError:
                out[key] = value
    return out


class NeedOwnName(Exception):
    """The importer cannot tell which name in the chats is the person's own, so it asks instead of guessing.
    <names> are everyone who wrote in the chats; <likely> is the one name in every chat, if there is one."""

    def __init__(self, names, likely=None):
        self.names, self.likely = sorted(names), likely
        super().__init__(self.question())

    def question(self):
        hint = f' It is probably "{self.likely}", the one name in every chat.' if self.likely else ""
        return ("Which of these names is yours, as it shows in your WhatsApp chats? "
                + ", ".join(f'"{n}"' for n in self.names) + "." + hint
                + " Nothing was imported. Run the import again with --me \"<your name>\": it is remembered,"
                " so you are never listed as one of your own contacts and are not asked again.")


OWN = "whatsapp_names"


def _clean_names(me):
    return [n.strip() for n in ([me] if isinstance(me, str) else me or []) if n and n.strip()]


def saved_names(brain):
    """The person's own WhatsApp names saved in brain.yaml by an earlier --me, or []."""
    y = Path(brain) / "brain.yaml"
    for line in (y.read_text(encoding="utf-8").splitlines() if y.is_file() else []):
        if line.startswith(f"{OWN}:"):
            try:
                value = json.loads(line.split(":", 1)[1].strip() or "[]")
            except ValueError:
                return []
            return _clean_names(value if isinstance(value, list) else [value])
    return []


def save_names(brain, names):
    """Remember the person's own WhatsApp names in brain.yaml, keeping any saved before."""
    y = Path(brain) / "brain.yaml"
    if not y.is_file():
        return
    keep = saved_names(brain)
    for n in names:
        if n.lower() not in {k.lower() for k in keep}:
            keep.append(n)
    line = f"{OWN}: {json.dumps(keep, ensure_ascii=False)}"
    lines = y.read_text(encoding="utf-8").splitlines()
    at = next((i for i, l in enumerate(lines) if l.startswith(f"{OWN}:")), None)
    if at is None:
        lines.append(line)
    else:
        lines[at] = line
    y.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _claude_md_name(brain):
    """The Name line in CLAUDE.md ("- Name: Sam Jones (source ...)"), or None while it is not known yet."""
    f = Path(brain) / "CLAUDE.md"
    for line in (f.read_text(encoding="utf-8").splitlines() if f.is_file() else []):
        m = re.match(r"^\s*-\s*Name:\s*(.+)$", line)
        if m:
            name = re.split(r"\s*[(\[]|\.\s*$", m.group(1).strip(), maxsplit=1)[0].strip().rstrip(".")
            return None if not name or name.lower().startswith("not known") else name
    return None


def own_names(brain, me, participants, chat_sets):
    """The person's own names, lower case. Raises NeedOwnName when nothing says which name is theirs."""
    given = _clean_names(me)
    if given:
        return {n.lower() for n in given + saved_names(brain)}
    saved = saved_names(brain)
    if saved:
        return {n.lower() for n in saved}
    named = _claude_md_name(brain)
    if named and named.lower() in {p.lower() for p in participants}:
        return {named.lower()}
    everywhere = set.intersection(*chat_sets) if len(chat_sets) >= 2 else set()
    raise NeedOwnName(participants, next(iter(everywhere)) if len(everywhere) == 1 else None)


def _update_people(brain, mine):
    """Rebuild WhatsApp's lines in people.jsonl and interactions.jsonl from every chat saved in the brain,
    so chats imported one at a time all count. The person's own names (<mine>, lower case) are never a contact."""
    chats = []
    for f in sorted((Path(brain) / "memory/conversations/whatsapp").glob("*.md")):
        front = _front(f.read_text(encoding="utf-8"))
        if front.get("source") == "whatsapp" and isinstance(front.get("participants"), list):
            chats.append((f.stem, front))
    people = {}
    for slug, f in chats:
        for name in f["participants"]:
            if name.lower() not in mine:
                people.setdefault(name, []).append(slug)
    merge_people(brain, "whatsapp", [{"name": n, "chats": s} for n, s in sorted(people.items())])
    replace_interactions(brain, "whatsapp", [{
        "id": f"whatsapp_{slug}", "type": "whatsapp", "date": f.get("last"), "first": f.get("first"),
        "title": f.get("chat"), "kind": f.get("kind"), "messages": f.get("messages"),
        "with": [n for n in f["participants"] if n.lower() not in mine],
        "file": f"memory/conversations/whatsapp/{slug}.md"} for slug, f in chats])


def _saved_chat_sets(brain):
    out = []
    for f in sorted((Path(brain) / "memory/conversations/whatsapp").glob("*.md")):
        front = _front(f.read_text(encoding="utf-8"))
        if front.get("source") == "whatsapp" and isinstance(front.get("participants"), list):
            out.append(set(front["participants"]))
    return out


def run(export, brain, me=None):
    """Import the chats. Raises NeedOwnName, having written nothing, if the person's own name is not known."""
    brain = require_brain(brain)
    result = {"chats": 0, "messages": 0, "groups": 0, "one_to_one": 0, "undated": 0, "skipped": []}
    taken, result["renamed"] = {}, []
    parsed = []
    for filename, text, name in _read_exports(export):
        messages, system = parse_chat(text)
        if not messages:
            result["skipped"].append({"file": filename, "reason": "no messages found"})
            continue
        parsed.append((filename, text, name, messages))
    if not parsed:
        return result
    new_sets = [{m["sender"] for m in msgs} for _, _, _, msgs in parsed]
    mine = own_names(brain, me, set().union(*new_sets), new_sets + _saved_chat_sets(brain))
    if _clean_names(me):
        save_names(brain, _clean_names(me))
    for filename, text, name, messages in parsed:
        senders = sorted({m["sender"] for m in messages})
        is_group = len(senders) >= 3 or "created group" in text.lower()
        first = messages[0]
        opens_with = f"{first['date'] or 'undated'} {first['time'] or ''} {first['sender']}".strip()
        slug = _slot(brain, name, opens_with, taken)
        taken[slug] = (name, opens_with)
        if slug != slugify(name, "chat"):
            result["renamed"].append({"chat": name, "file": f"{slug}.md"})
        dates = sorted(m["date"] for m in messages if m["date"])
        front = {
            "chat": name, "kind": "group" if is_group else "one-to-one", "source": "whatsapp",
            "messages": len(messages), "participants": senders,
            "first": dates[0] if dates else None, "last": dates[-1] if dates else None,
            "opens_with": opens_with,
        }
        body = ["---", dump_yaml(front).rstrip("\n"), "---", "", f"# WhatsApp: {name}", ""]
        for m in messages:
            when = f"{m['date'] or 'undated'} {m['time'] or ''}".strip()
            text_ = m["text"].replace("\n", "\n  ")
            body.append(f"- {when} **{m['sender']}**: {text_}")
        write_text(brain, f"memory/conversations/whatsapp/{slug}.md", "\n".join(body) + "\n")
        result["chats"] += 1
        result["messages"] += len(messages)
        result["groups" if is_group else "one_to_one"] += 1
        result["undated"] += sum(1 for m in messages if not m["date"])
    if result["chats"]:
        _update_people(brain, mine)
    return result


USAGE = "Usage: python3 importers/whatsapp.py <export> <brain-folder> [--me \"<your name in the chats>\"]"


def main(argv):
    args, me = argv[1:], []
    while "--me" in args:
        i = args.index("--me")
        if i + 1 >= len(args):
            raise SystemExit(USAGE)
        me.append(args[i + 1])
        del args[i:i + 2]
    if len(args) != 2:
        raise SystemExit(USAGE)
    try:
        r = run(args[0], args[1], me)
    except NeedOwnName as ask:
        raise SystemExit(ask.question())
    except (OSError, zipfile.BadZipFile) as e:
        raise SystemExit(f"Could not read the WhatsApp export: {e}")
    print(f"WhatsApp: {r['chats']} chats ({r['groups']} group, {r['one_to_one']} one-to-one), "
          f"{r['messages']} messages, {r['undated']} without a readable date.")
    for c in r["renamed"]:
        print(f"Note: another chat is already saved as \"{c['chat']}\", so this one is saved as {c['file']}.")
    for s in r["skipped"]:
        print(f"Skipped {s['file']}: {s['reason']}.")


if __name__ == "__main__":
    main(sys.argv)
