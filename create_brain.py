#!/usr/bin/env python3
"""Create an empty brain: python3 create_brain.py <folder> [--domains network,work,family]

<folder> must be new or empty. It may already hold an exports/ folder of export files: those are kept.

Every brain has the spine (CLAUDE.md, GEMINI.md, AGENTS.md, DOMAINS.md) and five core domains: automations, memory,
scripts, skills and tools, each with its own {DOMAIN}.md. --domains adds personal domains from the
library in template/domains/ (default: network, the home for the people you know). --domains none adds
no personal domain: imported people then go to memory/people/.

Level 1 is written once, in template/LEVEL1.md, and copied word for word to every AI's front door:
CLAUDE.md, GEMINI.md and a marked block at the top of AGENTS.md (see level1.py). The folder may already
hold a kit/ folder (this kit, downloaded there by the setup): it is kept and left untouched."""
import shutil
import sys

import level1
from pathlib import Path

KIT = Path(__file__).resolve().parent
TEMPLATE = KIT / "template"
LIBRARY = TEMPLATE / "domains"
# What a folder may already hold and still count as empty: the person's exports, and the Finder's own file.
MAY_HOLD = {"exports", "kit", ".DS_Store"}
# Folders in a brain that are not the brain's own text: never rendered, never checked as brain files.
NOT_BRAIN = {"exports", "kit"}
# Personal domains: what each holds, the requests AGENTS.md routes to it, and its files.
DOMAINS = {
    "network": ("People I know, and every conversation or meeting with them",
                "Someone I know, a contact, when we last spoke, an introduction",
                "people.jsonl, interactions.jsonl"),
    "work": ("My job, business or ventures, and their projects",
             "My work, a project or venture, its status or next step",
             "projects.yaml"),
    "knowledge": ("Notes, reading and references I want to reuse",
                  "A note, something I read, a how-to, a reference",
                  "<topic>.md, references.yaml"),
    "family": ("Home and family life: people, dates, plans",
               "Family, home, a birthday or a family plan",
               "family.yaml"),
    "health": ("My own health and fitness notes",
               "My health, fitness, habits or an appointment",
               "health.jsonl"),
    "finance": ("My money: bills, renewals, savings goals",
                "Money, a bill, a renewal or a savings goal",
                "finance.yaml"),
}
DEFAULT_DOMAINS = ["network"]
USAGE = "Usage: python3 create_brain.py <folder> [--domains network,work,family]"


def ready_for_brain(dest):
    """True if <dest> does not exist yet, or is a folder holding nothing but MAY_HOLD."""
    dest = Path(dest)
    if not dest.exists():
        return True
    return dest.is_dir() and all(p.name in MAY_HOLD for p in dest.iterdir()) \
        and all(not (dest / d).exists() or (dest / d).is_dir() for d in NOT_BRAIN)


def parse_domains(text):
    """'network,work' -> ['network', 'work']; 'none' -> []. Unknown names are refused."""
    names = [] if text.strip().lower() == "none" else [n.strip().lower() for n in text.split(",") if n.strip()]
    unknown = [n for n in names if n not in DOMAINS]
    if unknown:
        raise SystemExit(f"Unknown domain: {', '.join(unknown)}. Choose from: {', '.join(DOMAINS)} "
                         "(or none). Nothing was created.")
    return list(dict.fromkeys(names))


def _render(path, values):
    """Fill the {{PLACEHOLDERS}}. A placeholder with nothing to say takes its whole line with it."""
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}" + ("\n" if not value else ""), value)
        text = text.replace("{{" + key + "}}", value)
    path.write_text(text, encoding="utf-8")


def create_brain(folder, domains=None):
    """Make a brain in <folder> with the personal <domains>: a list of names, or None for the default."""
    dest = Path(folder)
    domains = list(DEFAULT_DOMAINS) if domains is None else parse_domains(",".join(domains) or "none")
    if not ready_for_brain(dest):
        raise SystemExit(f"Not creating a brain: {dest} already exists and is not empty. "
                         "Choose a new folder (it may hold an exports folder, nothing else).")
    shutil.copytree(TEMPLATE, dest, dirs_exist_ok=True,
                    ignore=lambda d, names: ["domains", "LEVEL1.md", "AGENTS.md"] if Path(d) == TEMPLATE else [])
    words = (TEMPLATE / "LEVEL1.md").read_text(encoding="utf-8")
    for door in ("CLAUDE.md", "GEMINI.md"):
        (dest / door).write_text(words, encoding="utf-8")
    (dest / "AGENTS.md").write_text(level1.join(words, (TEMPLATE / "AGENTS.md").read_text(encoding="utf-8")),
                                    encoding="utf-8")
    shutil.copy(KIT / "jobs.py", dest / "scripts" / "jobs.py")
    shutil.copy(KIT / "level1.py", dest / "scripts" / "level1.py")
    for name in domains:
        (dest / name).mkdir(exist_ok=True)
        shutil.copy(LIBRARY / f"{name}.md", dest / name / f"{name.upper()}.md")
    values = {
        "PEOPLE": "network/" if "network" in domains else "memory/people/",
        "DOMAIN_LIST": "[" + ", ".join(domains) + "]",
        "PERSONAL_FILES": "\n".join(f"  - {n}/{n.upper()}.md" for n in domains),
        "PERSONAL_DOMAINS": "\n".join(f"| {n} | `{n}/{n.upper()}.md` | {DOMAINS[n][0]} |" for n in domains)
                            or "| (none yet) | | |",
        "PERSONAL_ROUTES": "\n".join(f"| {DOMAINS[n][1]} | Read `{n}/{n.upper()}.md` first |" for n in domains),
        "PERSONAL_INDEX": "\n".join(f"{n + '/':<19}{n.upper()}.md, {DOMAINS[n][2]}" for n in domains),
    }
    for path in sorted(dest.rglob("*.md")) + [dest / "brain.yaml"]:
        if path.relative_to(dest).parts[0] not in NOT_BRAIN:
            _render(path, values)
    problems = level1.check(dest)
    if problems:  # cannot happen unless the template is broken; never hand over a brain with mismatched doors
        raise SystemExit("Level 1 copies differ: " + "; ".join(problems))
    return dest


def main(argv):
    args, domains = argv[1:], None
    if "--domains" in args:
        i = args.index("--domains")
        if i + 1 >= len(args):
            raise SystemExit(USAGE)
        domains = parse_domains(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1 or args[0].startswith("-"):
        raise SystemExit(USAGE)
    dest = create_brain(args[0], domains)
    chosen = ", ".join(DEFAULT_DOMAINS if domains is None else domains) or "none"
    print(f"Created an empty brain in {dest} with personal domains: {chosen}. "
          f"Level 1 is in CLAUDE.md, GEMINI.md and the top of AGENTS.md. Put export files in {dest / 'exports'}.")


if __name__ == "__main__":
    main(sys.argv)
