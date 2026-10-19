#!/usr/bin/env python3
"""Create an empty brain:          python3 create_brain.py <folder> [--domains network,work,family]
Add domains to a brain you have: python3 create_brain.py <brain> --add family,health

<folder> must be new or empty. It may already hold an exports/ folder of export files: those are kept.

Every brain has the spine (CLAUDE.md, GEMINI.md, AGENTS.md, DOMAINS.md) and five core domains: automations, memory,
scripts, skills and tools, each with its own {DOMAIN}.md. --domains adds personal domains from the
library in template/domains/ (default: network, the home for the people you know). --domains none adds
no personal domain: imported people then go to memory/people/.

--add puts more personal domains from the same library into a brain that already exists: each gets its
folder and {DOMAIN}.md, a line in the routing table and file index of AGENTS.md, a row in DOMAINS.md and
its place in brain.yaml, exactly as creation writes them. It never overwrites a file, never touches
level 1, and running it again changes nothing. Adding network to a brain made without it moves the
importers' people.jsonl and interactions.jsonl from memory/people/ into network/, where the importers
now write.

Level 1 is written once, in template/LEVEL1.md, and copied word for word to every AI's front door:
CLAUDE.md, GEMINI.md and a marked block at the top of AGENTS.md (see level1.py). The folder may already
hold a kit/ folder (this kit, downloaded there by the setup) and setup.yaml (the saved setup progress):
both are kept and left untouched."""
import re
import shutil
import sys

import level1
from pathlib import Path

KIT = Path(__file__).resolve().parent
TEMPLATE = KIT / "template"
LIBRARY = TEMPLATE / "domains"
# What a folder may already hold and still count as empty: the person's exports, the kit, the saved
# setup progress (written by kit/progress.py before the brain exists), and the Finder's own file.
# .git: Orca makes every new folder a git repository (it saves versions); that is fine for a brain.
MAY_HOLD = {"exports", "kit", "setup.yaml", ".DS_Store", ".git"}
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
NONE_YET = "| (none yet) | | |"
# The importers' own people files: in memory/people/ until the brain has a network domain (importers/common.py).
PEOPLE_FILES = ("people.jsonl", "interactions.jsonl")
NOT_IN_LIBRARY = 'Nothing was changed. For an area not on this list, follow "Adding a domain" in DOMAINS.md.'
DOMAINS_LINE = re.compile(r"^domains:[ \t]*\[([^\]\n]*)\][ \t]*$", re.M)


def command(*args):
    """One line to run, as check_setup.py prints it: `py` and double quotes on Windows, `python3` elsewhere."""
    from check_setup import command as line
    return line(*args)


def usage():
    py = command()
    return (f"Usage: {py} create_brain.py <folder> [--domains network,work,family], "
            f"or to add domains to a brain you have: {py} create_brain.py <brain> --add family,health")


def ready_for_brain(dest):
    """True if <dest> does not exist yet, or is a folder holding nothing but MAY_HOLD."""
    dest = Path(dest)
    if not dest.exists():
        return True
    return dest.is_dir() and all(p.name in MAY_HOLD for p in dest.iterdir()) \
        and all(not (dest / d).exists() or (dest / d).is_dir() for d in NOT_BRAIN)


def parse_domains(text, nothing="Nothing was created."):
    """'network,work' -> ['network', 'work']; 'none' -> []. Unknown names are refused."""
    names = [] if text.strip().lower() == "none" else [n.strip().lower() for n in text.split(",") if n.strip()]
    unknown = [n for n in names if n not in DOMAINS]
    if unknown:
        raise SystemExit(f"Unknown domain: {', '.join(unknown)}. Choose from: {', '.join(DOMAINS)} "
                         f"(or none). {nothing}")
    return list(dict.fromkeys(names))


# ---- The lines each personal domain adds to the spine: one place, used by creation and by --add ----

def doc(name):
    """network -> network/NETWORK.md"""
    return f"{name}/{name.upper()}.md"


def file_line(name):
    return f"  - {doc(name)}"


def domain_row(name):
    return f"| {name} | `{doc(name)}` | {DOMAINS[name][0]} |"


def route_row(name):
    return f"| {DOMAINS[name][1]} | Read `{doc(name)}` first |"


def index_line(name):
    return f"{name + '/':<19}{name.upper()}.md, {DOMAINS[name][2]}"


def values(domains):
    """What each {{PLACEHOLDER}} in the template becomes for a brain with these personal <domains>."""
    return {
        "PEOPLE": "network/" if "network" in domains else "memory/people/",
        "DOMAIN_LIST": "[" + ", ".join(domains) + "]",
        "PERSONAL_FILES": "\n".join(file_line(n) for n in domains),
        "PERSONAL_DOMAINS": "\n".join(domain_row(n) for n in domains) or NONE_YET,
        "PERSONAL_ROUTES": "\n".join(route_row(n) for n in domains),
        "PERSONAL_INDEX": "\n".join(index_line(n) for n in domains),
    }


def _render(path, values):
    """Fill the {{PLACEHOLDERS}}. A placeholder with nothing to say takes its whole line with it."""
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}" + ("\n" if not value else ""), value)
        text = text.replace("{{" + key + "}}", value)
    path.write_text(text, encoding="utf-8")


def _place_domain(brain, name, fill):
    """Make <name>/ and its {DOMAIN}.md from the library. An existing file is never replaced. True if written."""
    (brain / name).mkdir(exist_ok=True)
    target = brain / doc(name)
    if target.exists():
        return False
    shutil.copy(LIBRARY / f"{name}.md", target)
    _render(target, fill)
    return True


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
    fill = values(domains)
    for name in domains:
        (dest / name).mkdir(exist_ok=True)
        shutil.copy(LIBRARY / f"{name}.md", dest / doc(name))
    for path in sorted(dest.rglob("*.md")) + [dest / "brain.yaml"]:
        if path.relative_to(dest).parts[0] not in NOT_BRAIN:
            _render(path, fill)
    problems = level1.check(dest)
    if problems:  # cannot happen unless the template is broken; never hand over a brain with mismatched doors
        raise SystemExit("Level 1 copies differ: " + "; ".join(problems))
    return dest


# ---- --add: more personal domains for a brain that already exists ----

def _table(lines, heading):
    """(first, last) line numbers of the first Markdown table under <heading>, or None."""
    head = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if head is None:
        return None
    first = head + 1
    while first < len(lines) and not lines[first].startswith("|"):
        if lines[first].startswith("#"):
            return None
        first += 1
    if first >= len(lines):
        return None
    last = first
    while last + 1 < len(lines) and lines[last + 1].startswith("|"):
        last += 1
    return first, last


def _cell(row):
    """The first cell of a table row, trimmed."""
    parts = row.split("|")
    return parts[1].strip() if len(parts) > 2 else ""


def _brain_yaml_with(text, names):
    """(brain.yaml with <names> in its domains and files lists, the names that were missing from either)."""
    found = DOMAINS_LINE.search(text)
    if not found:
        raise SystemExit("Not adding domains: brain.yaml has no 'domains: [...]' line to add them to. "
                         "Nothing was changed.")
    have = [d.strip().strip("'\"") for d in found.group(1).split(",") if d.strip()]
    changed = {n for n in names if n not in have}
    text = text[:found.start()] + "domains: [" + ", ".join(have + [n for n in names if n not in have]) + "]" \
        + text[found.end():]
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("files:")), None)
    if start is None:
        raise SystemExit("Not adding domains: brain.yaml has no files list to add them to. Nothing was changed.")
    last, i = start, start + 1
    while i < len(lines) and (lines[i].startswith(("  - ", "#", " ")) or not lines[i].strip()):
        if lines[i].startswith("  - "):
            last = i
        i += 1
    declared = {line[4:].strip() for line in lines[start + 1:last + 1] if line.startswith("  - ")}
    missing = [n for n in names if doc(n) not in declared]
    lines[last + 1:last + 1] = [file_line(n) for n in missing]
    return "\n".join(lines), changed | set(missing)


def _domains_md_with(text, names):
    """(DOMAINS.md with a row for each of <names> in the personal domains table, the names it lacked)."""
    lines = text.split("\n")
    heading = next((line.strip() for line in lines if line.startswith("## Personal domains")), None)
    span = _table(lines, heading) if heading else None
    if span is None:
        raise SystemExit("Not adding domains: DOMAINS.md has no personal domains table to add them to. "
                         "Nothing was changed.")
    first, last = span
    rows = lines[first:last + 1]
    have = {_cell(r) for r in rows[2:]}
    missing = [n for n in names if n not in have]
    if missing:
        lines[first:last + 1] = [r for r in rows if _cell(r) != _cell(NONE_YET)] + [domain_row(n) for n in missing]
    return "\n".join(lines), set(missing)


def _level2_with(level2, names):
    """(the level 2 manual in AGENTS.md with each of <names> in its routing table and file index, the names
    it lacked)."""
    lines = level2.split("\n")
    span = _table(lines, "## Routing table")
    if span is None:
        raise SystemExit("Not adding domains: AGENTS.md has no routing table to add them to. Nothing was changed.")
    first, last = span
    missing = [n for n in names if not any(f"`{doc(n)}`" in row for row in lines[first:last + 1])]
    lines[last + 1:last + 1] = [route_row(n) for n in missing]
    changed = set(missing)
    head = next((i for i, line in enumerate(lines) if line.strip() == "## File index"), None)
    fences = [i for i, line in enumerate(lines) if head is not None and i > head and line.startswith("```")]
    if len(fences) >= 2:  # a brain whose file index was taken out still gets its routing lines
        block = lines[fences[0] + 1:fences[1]]
        unlisted = [n for n in names if not any(line.startswith(n + "/") for line in block)]
        lines[fences[1]:fences[1]] = [index_line(n) for n in unlisted]
        changed |= set(unlisted)
    return "\n".join(lines), changed


def add_domains(folder, domains):
    """Add the personal <domains> (a list of names) to the brain in <folder>.

    Returns (added, already_there, people_moved): the names that changed something, the names the brain
    already had in full, and the people files moved from memory/people/ into network/."""
    brain = Path(folder)
    names = parse_domains(",".join(domains) or "none", NOT_IN_LIBRARY)
    if not names:
        raise SystemExit(f"Name at least one domain to add: {', '.join(DOMAINS)}. Nothing was changed.")
    if not (brain / "brain.yaml").is_file():
        raise SystemExit(f"Not adding domains: {brain} is not a brain yet (it has no brain.yaml). Nothing was "
                         "changed. Make the brain first: "
                         + command(KIT / "create_brain.py", brain, "--domains", ",".join(names)))
    problems = level1.check(brain)
    if problems:
        sync = brain / "scripts" / "level1.py"
        raise SystemExit("Not adding domains: level 1 copies differ (" + "; ".join(problems) + "). Nothing was "
                         "changed. Put them right first, then add again: "
                         + command(sync if sync.is_file() else KIT / "level1.py", "sync", brain))

    # Work out every change first, so a brain that cannot take them is refused with nothing changed.
    paths = {name: brain / name for name in ("brain.yaml", "DOMAINS.md", "AGENTS.md")}
    before = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    words, level2 = level1.split(before["AGENTS.md"])
    yaml_text, changed = _brain_yaml_with(before["brain.yaml"], names)
    domains_text, more = _domains_md_with(before["DOMAINS.md"], names)
    changed |= more
    level2, more = _level2_with(level2, names)
    changed |= more
    # Adding network to a brain made without it: the importers write people to network/ from now on
    # (importers/common.py), so their files and the brain's own words for where people live go there too.
    switch_people = "network" in names and not (brain / "network").is_dir()
    skills = {}
    if switch_people:
        level2 = level2.replace("memory/people/", "network/")
        for skill in sorted((brain / "skills").glob("*/SKILL.md")):
            text = skill.read_text(encoding="utf-8")
            if "memory/people/" in text:
                skills[skill] = text.replace("memory/people/", "network/")
    after = {"brain.yaml": yaml_text, "DOMAINS.md": domains_text, "AGENTS.md": level1.join(words, level2)}

    every = [d.strip().strip("'\"") for d in DOMAINS_LINE.search(yaml_text).group(1).split(",") if d.strip()]
    for name in names:
        if _place_domain(brain, name, values(every)):
            changed.add(name)
    moved = []
    if switch_people:
        for file in PEOPLE_FILES:
            old, new = brain / "memory" / "people" / file, brain / "network" / file
            if old.is_file() and not new.exists():
                old.replace(new)
                moved.append(file)
    for name, path in paths.items():
        if after[name] != before[name]:
            path.write_text(after[name], encoding="utf-8")
    for path, text in skills.items():
        path.write_text(text, encoding="utf-8")
    problems = level1.check(brain)
    if problems:  # cannot happen: only level 2 was edited
        raise SystemExit("Level 1 copies differ after adding domains: " + "; ".join(problems))
    return [n for n in names if n in changed], [n for n in names if n not in changed], moved


def main(argv):
    args, domains, add = argv[1:], None, None
    for flag in ("--domains", "--add"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                raise SystemExit(usage())
            value = args[i + 1]
            del args[i:i + 2]
            if flag == "--domains":
                domains = parse_domains(value)
            else:
                add = parse_domains(value, NOT_IN_LIBRARY)
    if len(args) != 1 or args[0].startswith("-") or (domains is not None and add is not None):
        raise SystemExit(usage())
    if add is not None:
        added, already, moved = add_domains(args[0], add)
        brain = Path(args[0]).expanduser().absolute()  # "." from inside the brain reads as its full path
        if not added:
            print(f"Nothing to add: the brain in {brain} already has {', '.join(already)}. Nothing was changed.")
            return
        print(f"Added {', '.join(added)} to the brain in {brain}: a folder and instruction file each, "
              "and a line in AGENTS.md, DOMAINS.md and brain.yaml."
              + (f" Already there: {', '.join(already)}." if already else "")
              + (" Your people list moved from memory/people into network." if moved else "")
              + " Level 1 is unchanged.")
        return
    dest = create_brain(args[0], domains)
    chosen = ", ".join(DEFAULT_DOMAINS if domains is None else domains) or "none"
    print(f"Created an empty brain in {dest} with personal domains: {chosen}. "
          f"Level 1 is in CLAUDE.md, GEMINI.md and the top of AGENTS.md. Put export files in {dest / 'exports'}.")


if __name__ == "__main__":
    main(sys.argv)
