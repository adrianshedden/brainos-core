#!/usr/bin/env python3
"""Turn an answer into one page in the AI Ops style, saved in the brain and readable offline.

python3 skills/show-it-visually/make_page.py <brain> <answer.md or -> [--name "<words>"] [--open] [--print]
(on Windows, use py instead of python3; "-" reads the answer from the input instead of a file)

The answer is plain text in this shape:

    # One sentence that says the point
    One or two lines of summary, saying only what the points below show.

    ## A short section heading
    - One fact in plain words. (source: memory/calendar/events.yaml)

Every point ends with (source: <file or connector>). If any point has no source, nothing is saved and
the points are listed. The page is saved as views/<YYYY-MM-DD>-<name>.html in the brain, with style.css
pasted in, so it needs no internet. An existing page is never overwritten: -2, -3... is added instead.
--open opens the saved page. --print shows the page instead of saving it (for an app that draws pages
in the chat). Nothing here uses the internet or sends the page anywhere."""
import html
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
MONTHS = ("January February March April May June July August September October November December").split()
POINT = re.compile(r"^[-*]\s+(?P<text>.*?)\s*\(\s*sources?:\s*(?P<src>[^()]+?)\s*\)\s*\.?\s*$", re.IGNORECASE)
USAGE = 'Usage: python3 skills/show-it-visually/make_page.py <brain> <answer.md or -> [--name "<words>"] [--open] [--print]'


def long_date(day):
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def parse(text):
    """(headline, summary, [(heading, [(fact, source)])], problems). Problems are plain sentences."""
    headline, summary, sections, problems = None, [], [], []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# ") and headline is None and not sections:
            headline = line[2:].strip()
        elif line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif line.startswith(("- ", "* ")):
            m = POINT.match(line)
            src = m.group("src").strip("` ") if m else ""
            if not m or not m.group("text") or not src:
                problems.append(f"line {n} has no source. End it with (source: <file>): {line[2:]}")
                continue
            if not sections:
                sections.append(("", []))
            sections[-1][1].append((m.group("text"), src))
        elif headline is not None and not sections:
            summary.append(line)
        else:
            problems.append(f"line {n} is not a point. Write each fact as - <fact> (source: <file>): {line}")
    if headline is None:
        problems.append("there is no headline. Start with # and one sentence that says the point.")
    for heading, points in sections:
        if not points:
            problems.append(f"the section \"{heading}\" has no points.")
    if not sections:
        problems.append("there are no points. Add at least one: - <fact> (source: <file>)")
    return headline, " ".join(summary), sections, problems


def inline(text):
    """Escape the text, then keep `code` and **bold**."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)


def render(answer, today=None):
    """The finished page as text. Raises SystemExit with the problems if the answer is not ready."""
    headline, summary, sections, problems = parse(answer)
    if problems:
        raise SystemExit("Not made: " + " ".join(problems))
    today = today or date.today()
    sources = list(dict.fromkeys(src for _, points in sections for _, src in points))
    blocks = []
    for heading, points in sections:
        items = "\n".join(f'      <li>{inline(fact)}<span class="src"><span class="src__k">Source</span>'
                          f"{html.escape(src)}</span></li>" for fact, src in points)
        title = f"\n    <h2>{inline(heading)}</h2>" if heading else ""
        blocks.append(f'  <section class="card">{title}\n    <ul class="points">\n{items}\n    </ul>\n  </section>')
    page = (HERE / "page.html").read_text(encoding="utf-8")
    page = re.sub(r"\n\s*<!-- shape:.*?-->", "", page, flags=re.DOTALL)
    slots = {
        "STYLE": (HERE / "style.css").read_text(encoding="utf-8").strip(),
        "TITLE": html.escape(re.sub(r"[`*]", "", headline)),
        "LABEL": f"From your brain · {long_date(today)}",
        "HEADLINE": inline(headline),
        "SUMMARY": inline(summary),
        "SECTIONS": "\n".join(blocks),
        "SOURCES": "\n".join(f'      <li class="chip">{html.escape(s)}</li>' for s in sources),
        "MADE": f"Made on {long_date(today)} from the files in your brain. Each point names the file it came from.",
    }
    if not summary:
        page = page.replace('\n    <p class="lede">[[SUMMARY]]</p>', "")
    # One pass over the template only, so words in the answer are never taken for a slot.
    return re.sub(r"\[\[([A-Z]+)\]\]", lambda m: slots.get(m.group(1), m.group(0)), page)


def slug(words):
    parts = re.findall(r"[a-z0-9]+", words.lower())[:5]
    return "-".join(parts)[:50].strip("-") or "page"


def save(brain, page, name, today=None):
    """Write views/<date>-<name>.html in the brain, never over an existing page. Returns the path."""
    brain = Path(brain)
    if not (brain / "brain.yaml").is_file():
        raise SystemExit(f"Not made: {brain} is not a brain folder (it has no brain.yaml). Run this from your brain folder.")
    views = brain / "views"
    views.mkdir(exist_ok=True)
    stem = f"{(today or date.today()).isoformat()}-{slug(name)}"
    path, n = views / f"{stem}.html", 2
    while path.exists():
        path, n = views / f"{stem}-{n}.html", n + 1
    path.write_text(page, encoding="utf-8")
    return path


def open_page(path):
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        elif os.name == "nt":
            os.startfile(str(path))  # noqa: S606 (opens the file in the person's own browser)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def main(argv):
    args = argv[1:]
    flags = {a for a in args if a in ("--open", "--print")}
    args = [a for a in args if a not in flags]
    name = None
    if "--name" in args:
        i = args.index("--name")
        if i + 1 >= len(args):
            raise SystemExit(USAGE)
        name = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        raise SystemExit(USAGE)
    brain, source = args
    answer = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    page = render(answer)
    if "--print" in flags:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(page)
        return
    headline = parse(answer)[0]
    path = save(brain, page, name or headline)
    rel = path.relative_to(Path(brain)).as_posix()
    points = page.count('<span class="src">')
    print(f"Saved your page: {rel} ({points} points, each with its source). It works offline.")
    if "--open" in flags and not open_page(path):
        print(f"Could not open it by itself: double-click {rel} in your brain folder to see it.")


if __name__ == "__main__":
    main(sys.argv)
