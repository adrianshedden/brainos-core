#!/usr/bin/env python3
"""Save how far the setup has got, so the person can stop and carry on later (in any AI app).

  python3 kit/progress.py <brain> show
  python3 kit/progress.py <brain> step <n>                       the next step to do, 1 to 9
  python3 kit/progress.py <brain> pick <id> [<id> ...]           sources the person chose (from connections.yaml)
  python3 kit/progress.py <brain> connected <id> <how>           how: builtin, custom, local, cli or export
  python3 kit/progress.py <brain> pending "<what>" "<say_when_arrives>"
  python3 kit/progress.py <brain> arrived "<what>"               a pending item came in: take it off the list
  python3 kit/progress.py <brain> app <name>                     claude, chatgpt, cursor, opencode, orca, terminal, other
  python3 kit/progress.py <brain> done

On Windows, type `py` instead of `python3`. Each command prints one plain line. The progress lives in
<brain>/setup.yaml, which only this script writes, so every AI app writes it the same way. It is made
the first time any command runs (the brain itself must exist first: create_brain.py makes it).
Running the same command twice gives the same file. Plain Python 3, nothing to install, no internet."""
import datetime
import json
import os
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
FILE = "setup.yaml"
# The nine steps: number -> (id, plain name). SETUP.md has one heading per step, in this order.
STEPS = {
    1: ("one-line", "Find or make the brain"),
    2: ("choose", "Choose what to connect"),
    3: ("connect", "Connect them"),
    4: ("pull-in", "Pull everything in"),
    5: ("domains", "Choose the domains"),
    6: ("review", "Review what it learned"),
    7: ("skills", "Skills"),
    8: ("schedule", "Scheduled jobs"),
    9: ("done", "The first real answer"),
}
APPS = {"claude": "the Claude app", "chatgpt": "the ChatGPT app (Codex)", "cursor": "Cursor",
        "opencode": "OpenCode", "orca": "Orca", "terminal": "a terminal", "other": "another AI app"}
HOWS = ("builtin", "custom", "local", "cli", "export")
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
KEYS = ("kit_version", "app", "step", "picks", "connected", "pending", "done")
HEADER = "# BrainOS setup progress. Written only by kit/progress.py: run it again rather than editing this file."
USAGE = ("Usage: python3 kit/progress.py <brain> show | step <n> | pick <id> [<id> ...] | connected <id> <how> | "
         "pending \"<what>\" \"<say_when_arrives>\" | arrived \"<what>\" | app <name> | done")
# Plain words YAML would read as something other than text, so they are written in quotes.
YAML_WORDS = {"null", "true", "false", "yes", "no", "on", "off", "y", "n", "~"}


class SetupFileError(Exception):
    """setup.yaml is there but cannot be read."""


def kit_version():
    """The kit's version from its VERSION file, as three numbers ("2.0" -> "2.0.0")."""
    try:
        raw = (KIT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        raw = ""
    parts = [p for p in raw.split(".") if p.isdigit()][:3]
    return ".".join(parts + ["0"] * (3 - len(parts))) if parts else "2.0.0"


def fresh():
    return {"kit_version": kit_version(), "app": None, "step": 1, "picks": [], "connected": {}, "pending": [],
            "done": False}


# ---- reading -------------------------------------------------------------------------------------------

def _scalar(text, where):
    s = text.strip()
    if s.startswith('"'):
        try:
            return json.loads(s)
        except ValueError:
            raise SetupFileError(f"{where}: a quoted value is not closed properly")
    if s.startswith("'"):
        if len(s) < 2 or not s.endswith("'"):
            raise SetupFileError(f"{where}: a quoted value is not closed properly")
        return s[1:-1].replace("''", "'")
    s = re.sub(r"\s+#.*$", "", s)
    if s in ("", "~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s == "[]":
        return []
    if s == "{}":
        return {}
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(p, where) for p in s[1:-1].split(",") if p.strip()]
    return s


def _key_value(text, where):
    """'key: value' -> (key, value text). The key may be in quotes."""
    m = re.match(r'^("(?:[^"\\]|\\.)*"|\'[^\']*\'|[^:#]+?)\s*:(?:\s+(.*))?$', text)
    if not m:
        raise SetupFileError(f"{where}: expected 'name: value'")
    key = m.group(1)
    if key[0] in "\"'":
        key = _scalar(key, where)
    return key, (m.group(2) or "")


def parse(text):
    """setup.yaml text -> dict with every key. Raises SetupFileError, saying where, when it cannot."""
    data = fresh()
    data["kit_version"] = None
    block = None  # the top-level key whose indented lines follow
    item = None   # the current pending item, or the current connected entry
    for n, raw in enumerate(text.splitlines(), 1):
        where = f"line {n}"
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw[:len(raw) - len(raw.lstrip())]:
            raise SetupFileError(f"{where}: uses a tab to indent")
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0:
            key, value = _key_value(line, where)
            block, item = None, None
            if value.strip() == "" or value.strip().startswith("#"):
                block = key
                data[key] = {"connected": {}, "picks": [], "pending": []}.get(key)
            else:
                data[key] = _scalar(value, where)
        elif block == "picks" and line.startswith("-"):
            data["picks"].append(_scalar(line[1:], where))
        elif block == "pending" and line.startswith("- "):
            item = {}
            data["pending"].append(item)
            key, value = _key_value(line[2:].strip(), where)
            item[key] = _scalar(value, where)
        elif block == "pending" and item is not None and indent >= 4:
            key, value = _key_value(line, where)
            item[key] = _scalar(value, where)
        elif block == "connected" and indent == 2:
            key, value = _key_value(line, where)
            item = data["connected"].setdefault(str(key), {})
            if value.strip() and _scalar(value, where) not in ({}, None):
                raise SetupFileError(f"{where}: expected the details of {key} on the lines below")
        elif block == "connected" and item is not None and indent >= 4:
            key, value = _key_value(line, where)
            item[key] = _scalar(value, where)
        else:
            raise SetupFileError(f"{where}: not a line this file should have")
    _validate(data)
    return data


def _validate(data):
    if not isinstance(data.get("step"), int) or isinstance(data["step"], bool) or not 1 <= data["step"] <= 9:
        raise SetupFileError("step must be a whole number from 1 to 9")
    if data.get("app") is not None and not isinstance(data["app"], str):
        raise SetupFileError("app must be a name")
    if not isinstance(data.get("picks"), list) or not all(isinstance(p, str) for p in data["picks"]):
        raise SetupFileError("picks must be a list of names")
    if not isinstance(data.get("connected"), dict):
        raise SetupFileError("connected must list each source with how and at")
    for name, entry in data["connected"].items():
        if not isinstance(entry, dict) or not isinstance(entry.get("how"), str):
            raise SetupFileError(f"connected: {name} needs a how")
        if entry.get("at") is not None:
            entry["at"] = str(entry["at"])
    if not isinstance(data.get("pending"), list):
        raise SetupFileError("pending must be a list")
    for entry in data["pending"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("what"), str):
            raise SetupFileError("each pending item needs a what")
        entry["say_when_arrives"] = "" if entry.get("say_when_arrives") is None else str(entry["say_when_arrives"])
    if not isinstance(data.get("done"), bool):
        raise SetupFileError("done must be true or false")
    if data.get("kit_version") is not None:
        data["kit_version"] = str(data["kit_version"])


def load(brain):
    """The saved progress of <brain>, or None if there is no setup.yaml yet. Read-only."""
    path = Path(brain) / FILE
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        raise SetupFileError(f"it could not be opened ({e.__class__.__name__})")
    return parse(text)


# ---- writing -------------------------------------------------------------------------------------------

def _q(value):
    return json.dumps(value, ensure_ascii=False)


def _plain_or_q(value):
    """An id as it is when YAML reads it back as the same text, otherwise in quotes."""
    if ID.match(value) and value.lower() not in YAML_WORDS and not re.fullmatch(r"[\d-]+", value):
        return value
    return _q(value)


def dump(data):
    out = [HEADER,
           f"kit_version: {_q(data['kit_version'] or kit_version())}",
           f"app: {_plain_or_q(data['app']) if data['app'] else 'null'}",
           f"step: {data['step']}"]
    out.append("picks: []" if not data["picks"] else "picks:")
    out += [f"  - {_plain_or_q(p)}" for p in data["picks"]]
    out.append("connected: {}" if not data["connected"] else "connected:")
    for name, entry in data["connected"].items():
        out.append(f"  {_plain_or_q(name)}:")
        out.append(f"    how: {_plain_or_q(entry['how'])}")
        out.append(f"    at: {_q(entry.get('at') or '')}")
    out.append("pending: []" if not data["pending"] else "pending:")
    for entry in data["pending"]:
        out.append(f"  - what: {_q(entry['what'])}")
        out.append(f"    say_when_arrives: {_q(entry['say_when_arrives'])}")
    for key, value in data.items():  # anything a newer kit added and this one does not know: kept as it was
        if key not in KEYS and (value is None or isinstance(value, (str, int, bool))):
            name = key if re.fullmatch(r"[a-z][a-z0-9_]*", key) else _q(key)
            shown = ("null" if value is None else _q(value) if isinstance(value, str) else
                     "true" if value is True else "false" if value is False else str(value))
            out.append(f"{name}: {shown}")
    out.append(f"done: {'true' if data['done'] else 'false'}")
    return "\n".join(out) + "\n"


def save(brain, data):
    """Write setup.yaml in one go, so a crash never leaves half a file."""
    path = Path(brain) / FILE
    tmp = path.with_name("." + FILE + ".tmp")
    text = dump(data)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    try:
        os.replace(tmp, path)
    except OSError:  # a sync app (OneDrive, iCloud) can hold the old file for a moment
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        try:
            tmp.unlink()
        except OSError:
            pass


# ---- the commands ----------------------------------------------------------------------------------------

def step_name(n):
    return STEPS[n][1]


def plain(text):
    """One line: no line breaks, no runs of spaces."""
    return re.sub(r"\s+", " ", str(text)).strip()


def sentence(text):
    """Text that ends like a sentence."""
    text = plain(text)
    return text if not text or text[-1] in ".!?" else text + "."


def _known_sources():
    """The source ids in the kit's connections.yaml, or None if it is not there or not readable."""
    try:
        text = (KIT / "connections.yaml").read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    ids, inside = set(), False
    for line in text.splitlines():
        if re.match(r"^sources:\s*(#.*)?$", line):
            inside = True
        elif inside and re.match(r"^\S", line) and not line.startswith("#"):
            inside = False
        elif inside:
            m = re.match(r"^  ([a-z0-9][a-z0-9-]*)\s*:\s*(#.*)?$", line)
            if m:
                ids.add(m.group(1))
    return ids or None


def _check_ids(ids):
    bad = [i for i in ids if not ID.match(i)]
    if bad:
        raise SystemExit(f"Not saved: {', '.join(bad)} is not a source id. Use the ids in connections.yaml, "
                         "for example google-calendar or whatsapp (small letters, numbers and hyphens).")


def summary(data):
    """The show line."""
    if data["done"]:
        head = "Setup is finished: all nine steps are done."
    else:
        head = f"Next is step {data['step']} of 9: {step_name(data['step']).lower()}."
    app = APPS.get(data["app"], data["app"]) if data["app"] else "not recorded yet"
    picked = ", ".join(data["picks"]) or "none yet"
    connected = ", ".join(f"{k} ({v['how']})" for k, v in data["connected"].items()) or "none yet"
    waiting = "; ".join(p["what"] for p in data["pending"]) or "nothing"
    return plain(f"{head} App: {app}. Picked: {picked}. Connected: {connected}. Still on its way: {waiting}.")


def run(brain, command, args, today=None):
    """Do one command on <brain>. Returns the one line to print. Raises SystemExit with a plain line on a mistake."""
    brain = Path(brain).expanduser()
    if not brain.is_dir():
        raise SystemExit(f"Not saved: there is no folder at {brain}. Make the brain first (create_brain.py).")
    if not (brain / "brain.yaml").is_file():
        raise SystemExit(f"Not saved: {brain} is not a brain yet (it has no brain.yaml). "
                         "Make the brain first with create_brain.py, then run this again.")
    try:
        data = load(brain)
    except SetupFileError as e:
        raise SystemExit(f"Not saved: setup.yaml in {brain} could not be read ({e}). It was left as it is. "
                         "Rename it (for example to setup-old.yaml) and run this again to start a fresh one; "
                         "the brain itself is fine.")
    created = data is None
    if created:
        data = fresh()
    before = dump(data)
    today = today or datetime.date.today().isoformat()

    if command == "show":
        if args:
            raise SystemExit(USAGE)
        line = summary(data)
    elif command == "step":
        if len(args) != 1 or not re.fullmatch(r"\d", args[0]) or not 1 <= int(args[0]) <= 9:
            raise SystemExit("Not saved: give the next step as one number from 1 to 9, for example: step 3")
        data["step"], data["done"] = int(args[0]), False
        line = f"Saved: next is step {data['step']} of 9, {step_name(data['step']).lower()}."
    elif command == "pick":
        if not args:
            raise SystemExit("Not saved: name at least one source, for example: pick google-calendar whatsapp")
        ids = [a.strip().lower() for a in args if a.strip()]
        _check_ids(ids)
        for i in ids:
            if i not in data["picks"]:
                data["picks"].append(i)
        known = _known_sources()
        unknown = [i for i in ids if known is not None and i not in known]
        line = f"Saved: picked {', '.join(ids)} ({len(data['picks'])} picked in all)."
        if unknown:
            line += f" Check the spelling: {', '.join(unknown)} is not in connections.yaml."
    elif command == "connected":
        if len(args) != 2:
            raise SystemExit("Not saved: give the source and how it is connected, for example: "
                             "connected google-calendar builtin")
        source, how = args[0].strip().lower(), args[1].strip().lower()
        _check_ids([source])
        if how not in HOWS:
            raise SystemExit(f"Not saved: how must be one of {', '.join(HOWS)}.")
        old = data["connected"].get(source)
        data["connected"][source] = {"how": how, "at": old["at"] if old and old.get("how") == how and old.get("at")
                                     else today}
        if source not in data["picks"]:
            data["picks"].append(source)
        line = f"Saved: {source} is connected ({how}, {data['connected'][source]['at']})."
    elif command == "pending":
        if len(args) != 2 or not plain(args[0]):
            raise SystemExit('Not saved: give what is on its way and what to say when it arrives, for example: '
                             'pending "LinkedIn archive" "add my LinkedIn"')
        what, say = plain(args[0]), plain(args[1])
        for entry in data["pending"]:
            if entry["what"].lower() == what.lower():
                entry["say_when_arrives"] = say
                break
        else:
            data["pending"].append({"what": what, "say_when_arrives": say})
        line = f"Saved: still on its way: {what}." + (f" When it arrives, say: {sentence(say)}" if say else "")
    elif command == "arrived":
        if len(args) != 1 or not plain(args[0]):
            raise SystemExit('Not saved: name what arrived, as it was saved, for example: arrived "LinkedIn archive"')
        what = plain(args[0])
        kept = [e for e in data["pending"] if e["what"].lower() != what.lower()]
        line = (f"Saved: {what} has arrived and is off the list." if len(kept) < len(data["pending"]) else
                f"Nothing to change: {what} was not on the list of things on their way.")
        data["pending"] = kept
    elif command == "app":
        if len(args) != 1 or args[0].strip().lower() not in APPS:
            raise SystemExit(f"Not saved: the app must be one of {', '.join(APPS)}.")
        data["app"] = args[0].strip().lower()
        line = f"Saved: working in {APPS[data['app']]}."
    elif command == "done":
        if args:
            raise SystemExit(USAGE)
        data["done"], data["step"] = True, 9
        line = "Saved: setup is finished. Paste the same line again any time to connect something new."
    else:
        raise SystemExit(USAGE)

    data["kit_version"] = kit_version()
    if created or dump(data) != before:
        save(brain, data)
    if created:
        line = "Started saving progress in setup.yaml. " + line
    return plain(line)


def main(argv, out=print):
    if len(argv) < 2 or argv[0].startswith("-"):
        raise SystemExit(USAGE)
    out(run(argv[0], argv[1].lower(), argv[2:]))


if __name__ == "__main__":
    try:  # a Windows console may not show every letter: never fail over that
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    main(sys.argv[1:])
