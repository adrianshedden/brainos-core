#!/usr/bin/env python3
"""Import an Apple Contacts export: python3 importers/apple_contacts.py <file.vcf or folder> <brain>

On a Mac: open Contacts, select all your cards, then File > Export > Export vCard... and drop the
.vcf file here. Apple Calendar is a separate drop: export each calendar as .ics from Calendar's
File > Export menu and use importers/calendar_ics.py.

Reads vCard 2.1, 3.0 and 4.0, the three versions Contacts and the phone address books write.
Photos and other binary blocks are skipped; a card with no readable name is reported, never fatal.
Everyone joins the brain's one people list (people.jsonl, in network/ or memory/people/).
No network: the file is read on this machine and written into the brain folder only."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import merge_people, require_brain  # noqa: E402

# Properties whose value is a picture, a sound or a key: never useful as text, often megabytes of base64.
BINARY = {"PHOTO", "LOGO", "SOUND", "KEY"}
QUOTED_PRINTABLE = "quoted-printable"


def _split_unquoted(s, sep):
    """Split on sep, ignoring separators inside a "quoted" parameter value."""
    parts, cur, quoted = [], "", False
    for ch in s:
        if ch == '"':
            quoted = not quoted
        if ch == sep and not quoted:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return parts + [cur]


def _split_head(line):
    """('NAME;PARAMS', 'value') at the first colon outside quotes, or (None, None)."""
    quoted = False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch == ":" and not quoted:
            return line[:i], line[i + 1:]
    return None, None


def unfold(text):
    """One list entry per logical vCard line.

    vCard 3.0/4.0 wrap long values by starting the next line with a space or tab. vCard 2.1
    quoted-printable values wrap with a trailing '=' and no leading space, so both are rejoined here."""
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if out and line[:1] in (" ", "\t"):
            out[-1] += line[1:]
        elif out and out[-1].endswith("=") and QUOTED_PRINTABLE in (_split_head(out[-1])[0] or "").lower():
            out[-1] = out[-1][:-1] + line
        else:
            out.append(line.rstrip())
    return out


def _unquote_printable(value):
    """Decode =XX byte escapes. The bytes are collected before decoding: one accented character is
    several =XX escapes, and decoding them one at a time turns it into mojibake."""
    raw, i = bytearray(), 0
    while i < len(value):
        if value[i] == "=" and re.fullmatch(r"[0-9A-Fa-f]{2}", value[i + 1:i + 3] or "x"):
            raw += bytes([int(value[i + 1:i + 3], 16)])
            i += 3
        else:
            raw += value[i].encode("utf-8")
            i += 1
    return raw.decode("utf-8", errors="replace")


def _unescape(value):
    """vCard text escapes: \\n is a line break, \\, \\; and \\\\ are the literal characters."""
    out, i = "", 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            out += "\n" if value[i + 1] in "nN" else value[i + 1]
            i += 2
        else:
            out += value[i]
            i += 1
    return out


def _params(bits):
    """{PARAM: [values]}. vCard 2.1 writes bare types (TEL;WORK;VOICE:), 3.0 writes TYPE=WORK."""
    params = {}
    for bit in bits:
        if "=" in bit:
            key, value = bit.split("=", 1)
        else:
            key, value = "TYPE", bit
        for one in _split_unquoted(value.strip(), ","):
            one = one.strip().strip('"')
            if one:
                params.setdefault(key.strip().upper(), []).append(one)
    return params


def parse_cards(text):
    """[{PROPERTY: [(params, value), ...]}], one dict per BEGIN:VCARD block."""
    cards, cur = [], None
    for line in unfold(text):
        if line.strip().upper() == "BEGIN:VCARD":
            cur = {}
            continue
        if line.strip().upper() == "END:VCARD":
            if cur:
                cards.append(cur)
            cur = None
            continue
        if cur is None:
            continue
        head, value = _split_head(line)
        if head is None:
            continue
        bits = _split_unquoted(head, ";")
        # Apple groups related lines with an "item1." prefix (item1.EMAIL, item1.X-ABLabel).
        name = bits[0].strip().split(".")[-1].upper()
        params = _params(bits[1:])
        encodings = [e.upper() for e in params.get("ENCODING", [])]
        if name in BINARY or "B" in encodings or "BASE64" in encodings:
            continue
        if QUOTED_PRINTABLE.upper() in encodings:
            value = _unquote_printable(value)
        cur.setdefault(name, []).append((params, _unescape(value).strip()))
    return cards


def _entries(card, name):
    """[(params, value)] for a property, dropping empty values."""
    return [(p, v) for p, v in card.get(name, []) if v.strip()]


def _preferred(params):
    """vCard 3.0 marks the main email or number TYPE=PREF, vCard 4.0 marks it PREF=1. Parameter
    values are case-insensitive, and Contacts writes `type=pref` in lower case."""
    return "PREF" in [t.upper() for t in params.get("TYPE", [])] or bool(params.get("PREF"))


def _values(card, name):
    """Every value of a property, preferred one first, in order, without repeats."""
    entries = _entries(card, name)
    preferred = [v for p, v in entries if _preferred(p)]
    out = []
    for v in preferred + [v for _, v in entries]:
        if v not in out:
            out.append(v)
    return out


def _first(card, name):
    return next(iter(_values(card, name)), "")


def _structured(value):
    """A ';'-separated compound value such as N: or ORG:."""
    return [p.strip() for p in _split_unquoted(value, ";")]


def _name(card):
    fn = _first(card, "FN")
    if fn:
        return fn
    parts = _structured(_first(card, "N"))  # family;given;middle;prefix;suffix
    ordered = [parts[i] for i in (3, 1, 2, 0, 4) if i < len(parts) and parts[i]]
    return " ".join(ordered).strip()


def person(card):
    """One contact, or None when the card has no name to file it under."""
    name = _name(card)
    if not name:
        return None
    org = _structured(_first(card, "ORG"))
    emails = [e.lower() for e in _values(card, "EMAIL")]
    phones = _values(card, "TEL")
    return {
        "name": name,
        "company": org[0] if org else "",
        "department": org[1] if len(org) > 1 else "",
        "position": _first(card, "TITLE"),
        "email": emails[0] if emails else "",
        "emails": emails,
        "phone": phones[0] if phones else "",
        "phones": phones,
        "url": _first(card, "URL"),
        "birthday": _first(card, "BDAY"),
        "note": _first(card, "NOTE"),
        "source": "apple-contacts",
    }


def _read_exports(export):
    """[(filename, text)] for a .vcf file or a folder of them."""
    export = Path(export)
    files = sorted(p for p in export.rglob("*") if p.is_file() and p.suffix.lower() in (".vcf", ".vcard")) \
        if export.is_dir() else [export]
    return [(p.name, p.read_bytes().decode("utf-8-sig", errors="replace")) for p in files]


def run(export, brain):
    brain = require_brain(brain)
    people, skipped, nameless = [], [], 0
    seen = set()
    for filename, text in _read_exports(export):
        cards = parse_cards(text)
        if not cards:
            skipped.append({"file": filename, "reason": "no vCard found in it"})
            continue
        for card in cards:
            p = person(card)
            if not p:
                nameless += 1
                continue
            # The same card exported twice (two files, or a card and its copy) is one person.
            key = (p["name"].lower(), p["email"], p["phone"])
            if key in seen:
                continue
            seen.add(key)
            people.append(p)
    people.sort(key=lambda p: (p["name"].lower(), p["email"]))
    merge_people(brain, "apple-contacts", [{k: v for k, v in p.items() if k not in ("email", "phone", "source")}
                                           for p in people])
    return {"people": len(people), "with_email": sum(1 for p in people if p["email"]),
            "with_phone": sum(1 for p in people if p["phone"]), "nameless": nameless, "skipped": skipped}


def main(argv):
    if len(argv) != 3:
        raise SystemExit("Usage: python3 importers/apple_contacts.py <file.vcf or folder> <brain-folder>")
    try:
        r = run(argv[1], argv[2])
    except OSError as e:
        raise SystemExit(f"Could not read the contacts export: {e}")
    print(f"Apple Contacts: {r['people']} people ({r['with_email']} with an email address, "
          f"{r['with_phone']} with a phone number).")
    if r["nameless"]:
        print(f"Skipped {r['nameless']} cards with no name on them.")
    for s in r["skipped"]:
        print(f"Skipped {s['file']}: {s['reason']}.")


if __name__ == "__main__":
    main(sys.argv)
