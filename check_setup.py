#!/usr/bin/env python3
"""Check you are ready to make or fill a brain: python3 check_setup.py <brain-folder>

Read-only: it changes nothing and never touches the network. It says, in plain English:
- whether this Python is new enough;
- whether the kit files it needs are here;
- whether <brain-folder> is a brain already, or empty and ready for create_brain.py;
- what each file in <brain-folder>/exports/ looks like, and the exact importer line to run for it;
- one next step, in the build-along order: check, choose domains, create the brain, import, mine my
  context, first skills.

It always finishes with exit code 0, whatever it finds. Only wrong arguments stop it."""
import shlex
import sys
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT / "importers"))
import linkedin  # noqa: E402
import whatsapp  # noqa: E402
import x_export  # noqa: E402

MIN_PYTHON = (3, 8)
NEEDED = ["create_brain.py", "template/brain.yaml", "template/CLAUDE.md", "template/AGENTS.md", "importers/common.py",
          "importers/linkedin.py", "importers/whatsapp.py", "importers/calendar_ics.py",
          "importers/apple_contacts.py", "importers/x_export.py"]
# Files that are ours, or the computer's own, in exports/: never reported.
OURS = {"readme.md", ".ds_store"}
SNIFF_BYTES = 64 * 1024

# kind -> (what it is, in plain words; importer script)
KINDS = {
    "linkedin": ("a LinkedIn data archive", "importers/linkedin.py"),
    "x": ("an X (Twitter) archive", "importers/x_export.py"),
    "whatsapp": ("a WhatsApp chat export", "importers/whatsapp.py"),
    "calendar": ("a calendar export", "importers/calendar_ics.py"),
    "contacts": ("an Apple Contacts export", "importers/apple_contacts.py"),
}


def _is_whatsapp_text(head):
    lines = [whatsapp._clean(line) for line in head.splitlines()[:40]]
    return any(whatsapp.IOS.match(line) or whatsapp.ANDROID.match(line) for line in lines if line)


def kind_of_members(names, read):
    """What a set of files (inside a .zip, or an unzipped folder) adds up to. <names> are their paths;
    read(name) returns the first bytes of one. None if it is nothing BrainOS reads."""
    base = {n.replace("\\", "/").split("/")[-1].lower(): n for n in names}
    if any(f in base for f in linkedin.FILES):
        return "linkedin"
    if any(pattern.match(b) for b in base for _, pattern in x_export.ROLES):
        return "x"
    for b, n in base.items():
        if b.endswith(".txt") and (b == "_chat.txt" or b.startswith("whatsapp chat")
                                   or _is_whatsapp_text(read(n).decode("utf-8-sig", errors="replace"))):
            return "whatsapp"
    if any(b.endswith(".ics") for b in base):
        return "calendar"
    return None


def _head(path):
    with open(path, "rb") as f:
        return f.read(SNIFF_BYTES)


def kind_of(path):
    """(kind or None, a note for the person or ""). Reads at most the start of each file."""
    path = Path(path)
    suffix = path.suffix.lower()
    try:
        if path.is_dir():
            files = [p for p in path.rglob("*") if p.is_file()]
            names = [p.relative_to(path).as_posix() for p in files]
            kind = kind_of_members(names, lambda n: _head(path / n))
            if kind is None and any(p.suffix.lower() in (".vcf", ".vcard") for p in files):
                kind = "contacts"
            return kind, ""
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as zf:
                names = [i.filename for i in zf.infolist() if not i.is_dir() and "__MACOSX/" not in i.filename]

                def read(n):
                    with zf.open(n) as f:
                        return f.read(SNIFF_BYTES)
                kind = kind_of_members(names, read)
                if kind is None and any(n.lower().endswith((".vcf", ".vcard")) for n in names):
                    return None, "a .zip of contact cards: unzip it first, then check again"
                return kind, ""
        head = _head(path).decode("utf-8-sig", errors="replace")
    except (OSError, zipfile.BadZipFile) as e:
        return None, f"could not be opened ({e.__class__.__name__})"
    if suffix in (".vcf", ".vcard") or head.lstrip().upper().startswith("BEGIN:VCARD"):
        return "contacts", ""
    if suffix in (".ics", ".ical") or head.lstrip().upper().startswith("BEGIN:VCALENDAR"):
        return "calendar", ""
    if suffix == ".txt" and _is_whatsapp_text(head):
        return "whatsapp", ""
    if path.name.lower() in linkedin.FILES:
        return None, "one file from a LinkedIn archive: put the whole .zip here instead"
    return None, ""


def importer_line(kind, export, brain):
    script = KIT / KINDS[kind][1]
    return " ".join(shlex.quote(str(a)) for a in ("python3", script, export, brain))


def brain_state(folder):
    """One of: missing, empty, brain, not-empty. Plus the declared files a brain is missing."""
    folder = Path(folder)
    if not folder.exists():
        return "missing"
    if not folder.is_dir():
        return "not-empty"
    if (folder / "brain.yaml").is_file():
        return "brain"
    if all(p.name in ("exports", ".DS_Store") for p in folder.iterdir()):
        return "empty"
    return "not-empty"


def report(folder):
    """The lines to print, in order. Changes nothing."""
    folder = Path(folder).expanduser().resolve()
    out = ["BrainOS setup check. Nothing is changed by this check.", ""]
    py = ".".join(map(str, sys.version_info[:3]))
    old_python = sys.version_info[:2] < MIN_PYTHON
    out.append(f"Python: {py}. " + ("Too old: BrainOS needs Python 3.8 or newer." if old_python else "Good."))

    missing = [rel for rel in NEEDED if not (KIT / rel).is_file()]
    out.append(f"Kit: {'these files are missing: ' + ', '.join(missing) if missing else 'all the files it needs are here'} ({KIT}).")

    state = brain_state(folder)
    out.append("Brain folder: " + {
        "missing": f"{folder} does not exist yet. create_brain.py will make it.",
        "empty": f"{folder} is empty and ready for create_brain.py.",
        "brain": f"{folder} is a brain.",
        "not-empty": f"{folder} already has other things in it and is not a brain. "
                     "create_brain.py needs a new or empty folder.",
    }[state])

    exports = folder / "exports"
    found, unknown = [], []
    if exports.is_dir():
        items = sorted((p for p in exports.iterdir() if p.name.lower() not in OURS and not p.name.startswith(".")),
                       key=lambda p: p.name.lower())
        out += ["", f"Exports in {exports}:"]
        if not items:
            out.append("- None yet.")
        for p in items:
            kind, note = kind_of(p)
            if kind:
                found.append(p)
                out.append(f"- {p.name}: looks like {KINDS[kind][0]}. Import it with:")
                out.append(f"    {importer_line(kind, p, folder)}")
                if kind == "whatsapp" and not whatsapp.saved_names(folder):
                    out.append("    First ask the person, once, for their own name as it shows in their WhatsApp chats, "
                               "and add --me \"<that name>\" to the line above, so they are never listed as a contact.")
            else:
                unknown.append(p)
                out.append(f"- {p.name}: not recognised" + (f", {note}." if note else
                                                           ". BrainOS cannot read this file. Leave it or remove it."))
    elif state == "brain":
        out += ["", f"No exports folder at {exports}."]

    out.append("")
    if missing:
        step = "Download the BrainOS kit again: some of its files are missing."
    elif old_python:
        step = "Install a newer Python 3 (3.8 or later), then run this check again."
    elif state in ("missing", "empty"):
        line = " ".join(shlex.quote(str(a)) for a in ("python3", KIT / "create_brain.py", folder, "--domains", "network"))
        step = (f"Choose the personal domains that fit you (network, work, knowledge, family, health, finance; "
                f"network holds the people you know), then make the brain: {line}")
    elif state == "not-empty":
        step = "Choose a new, empty folder for the brain, then run this check again with that folder."
    elif not exports.is_dir():
        step = f"Make a folder called exports inside {folder}, put your export files in it, then run this check again."
    elif found:
        step = ("Run the import lines above, one at a time. Then ask your AI to use the mine-my-context skill "
                "(skills/mine-my-context/SKILL.md), then try the first skills.")
    elif unknown:
        step = ("None of the files in exports is one BrainOS can read. Add a LinkedIn, WhatsApp, calendar, "
                "Apple Contacts or X export, then run this check again.")
    else:
        step = f"Put your export files in {exports}, then run this check again."
    out.append(f"Next step: {step}")
    return out


def main(argv, out=print):
    if len(argv) != 1 or argv[0].startswith("-"):
        raise SystemExit("Usage: python3 check_setup.py <brain-folder>")
    for line in report(argv[0]):
        out(line)


if __name__ == "__main__":
    main(sys.argv[1:])
