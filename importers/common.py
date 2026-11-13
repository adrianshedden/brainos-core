"""Shared helpers for the importers. Standard library only; no network."""
import json
import re
from pathlib import Path


def require_brain(brain):
    brain = Path(brain)
    if not (brain / "brain.yaml").is_file():
        raise SystemExit(f"{brain} is not a brain folder (no brain.yaml). Create one with create_brain.py first.")
    return brain


def slugify(text, fallback="untitled"):
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s[:60] or fallback


def _scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(str(v), ensure_ascii=False)  # a JSON string is a valid YAML string


def dump_yaml(obj, indent=0):
    """Minimal YAML writer for lists, dicts and scalars."""
    pad = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return pad + "{}\n"
        out = ""
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                out += f"{pad}{k}:\n{dump_yaml(v, indent + 1)}"
            elif isinstance(v, (dict, list)):
                out += f"{pad}{k}: {'{}' if isinstance(v, dict) else '[]'}\n"
            else:
                out += f"{pad}{k}: {_scalar(v)}\n"
        return out
    if isinstance(obj, list):
        if not obj:
            return pad + "[]\n"
        out = ""
        for item in obj:
            if isinstance(item, (dict, list)) and item:
                inner = dump_yaml(item, indent + 1)
                out += f"{pad}-{inner[len(pad) + 1:]}" if isinstance(item, dict) else f"{pad}-\n{inner}"
            else:
                out += f"{pad}- {_scalar(item) if not isinstance(item, (dict, list)) else ('{}' if isinstance(item, dict) else '[]')}\n"
        return out
    return pad + _scalar(obj) + "\n"


def write_text(brain, relpath, text):
    path = Path(brain) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_yaml(brain, relpath, obj, header=None):
    text = (f"# {header}\n" if header else "") + dump_yaml(obj)
    return write_text(brain, relpath, text)


# ---- People and interactions: one merged list across every importer ----------------------------
# People go to network/people.jsonl when the brain has a network domain, else memory/people/people.jsonl.
# Interactions (messages, meetings) go next to them in interactions.jsonl. One JSON object per line, no
# header line: every line carries `source` and `confidence`. Re-importing replaces only that source's lines.

BASE_CONFIDENCE = {"whatsapp": "medium"}  # a WhatsApp name is however the person is saved in a phone


def people_home(brain):
    brain = Path(brain)
    return "network" if (brain / "network").is_dir() else "memory/people"


def _read_jsonl(path):
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                row = json.loads(line)
            except ValueError:
                continue  # a hand-broken line is dropped rather than stopping the import
            if isinstance(row, dict):
                out.append(row)
    return out


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def _norm_name(name):
    return re.sub(r"\s+", " ", str(name or "")).strip().lower()


def _norm_phone(phone):
    digits = re.sub(r"\D", "", str(phone or ""))
    return digits[-10:] if len(digits) >= 7 else ""


def _keys(entry):
    """Ways to recognise the same person: any email, any phone, and the name."""
    keys = {("email", e.lower()) for e in entry.get("emails", []) if e}
    keys |= {("phone", p) for p in map(_norm_phone, entry.get("phones", [])) if p}
    if _norm_name(entry.get("name")):
        keys.add(("name", _norm_name(entry["name"])))
    return keys


def _joined_strongly(parts):
    """True if every source's entry links to the others through a shared email or phone, not the name alone."""
    strong = [{k for k in _keys(p) if k[0] != "name"} for p in parts]
    reached, grew = set(strong[0]), True
    done = {0}
    while grew:
        grew = False
        for i, keys in enumerate(strong):
            if i not in done and keys & reached:
                done.add(i)
                reached |= keys
                grew = True
    return len(done) == len(parts)


def _recompute(person):
    """The merged fields come from what each source said (`from`). Any other field (notes, tags) is kept."""
    parts = [person["from"][s] for s in sorted(person["from"])]
    first = lambda k: next((p[k] for p in parts if p.get(k)), "")  # noqa: E731
    person["name"] = first("name")
    for k in ("company", "position", "url"):
        person[k] = first(k)
    # in order of the sources, each source's preferred one first
    person["emails"] = list(dict.fromkeys(e.lower() for p in parts for e in p.get("emails", []) if e))
    person["phones"] = list(dict.fromkeys(ph for p in parts for ph in p.get("phones", []) if ph))
    person["source"] = sorted(person["from"])
    # medium: the only word on this person is a WhatsApp display name, or sources joined by name alone
    weak = all(BASE_CONFIDENCE.get(s) == "medium" for s in person["from"]) or not _joined_strongly(parts)
    person["confidence"] = "medium" if weak else "high"
    return person


def merge_people(brain, source, entries):
    """Add one importer's people to the merged list. <entries>: dicts with name and any of emails, phones,
    company, position, url, plus extra fields kept under that source. Re-importing the same source replaces
    what it said before; ids never change for a person already in the list. Returns the file written."""
    path = Path(brain) / people_home(brain) / "people.jsonl"
    people = _read_jsonl(path)
    for p in people:
        p.setdefault("from", {}).pop(source, None)
        if p["from"]:
            _recompute(p)
    # Recognise people by what the other sources say. Someone only this source knew keeps their old
    # details just long enough to be recognised again, so their id does not change.
    index = {}
    for p in sorted(people, key=lambda p: not p["from"]):
        for k in _keys({"name": p.get("name"), "emails": p.get("emails", []), "phones": p.get("phones", [])}):
            index.setdefault(k, p)
    ids = {p.get("id") for p in people}
    for e in entries:
        if not _norm_name(e.get("name")) and not e.get("emails"):
            continue
        e = {k: v for k, v in e.items() if v not in ("", None, [])}
        keys = _keys(e)
        strong = [index[k] for k in keys if k[0] != "name" and k in index]
        match = strong[0] if strong else index.get(("name", _norm_name(e.get("name"))))
        if match is not None and source in match["from"] and not strong and keys - {("name", _norm_name(e.get("name")))}:
            match = None  # same name, different details, same source: two people who share a name
        if match is not None and source in match["from"]:
            prev = match["from"][source]  # the same source names this person twice: fold together
            for k in ("emails", "phones"):
                prev[k] = list(dict.fromkeys(prev.get(k, []) + e.get(k, [])))
            for k, v in e.items():
                prev.setdefault(k, v)
        elif match is not None:
            match["from"][source] = e
        else:
            base = "person_" + slugify(e.get("name") or e["emails"][0], "someone").replace("-", "_")
            pid, n = base, 2
            while pid in ids:
                pid, n = f"{base}_{n}", n + 1
            ids.add(pid)
            match = {"id": pid, "from": {source: e}}
            people.append(match)
        _recompute(match)
        for k in _keys(match):
            index.setdefault(k, match)
    people = [_recompute(p) for p in people if p["from"]]
    people.sort(key=lambda p: (_norm_name(p.get("name")), p["id"]))
    _write_jsonl(path, people)
    return path


def replace_interactions(brain, source, rows):
    """Put one importer's interactions in the log, replacing what that source wrote before. Every row
    gets source and confidence. Rows from other sources, and lines added by hand, are kept."""
    path = Path(brain) / people_home(brain) / "interactions.jsonl"
    kept = [r for r in _read_jsonl(path) if r.get("source") != source]
    new = [dict(r, source=source, confidence=r.get("confidence", "high")) for r in rows]
    out = kept + new
    out.sort(key=lambda r: (str(r.get("date") or ""), str(r.get("time") or ""), str(r.get("id") or "")))
    _write_jsonl(path, out)
    return path
