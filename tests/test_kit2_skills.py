"""Kit 2.0 skills (19 Oct 2026): morning-brief, weekly-review and show-it-visually, and the AI Ops page style
the visual skill pastes into every page.

Like B7, no AI runs here. Each skill follows the kit's skill format, reads only files a brain has, and gets a
scripted stand-in answer worked out from the sample brain, so every point traces to a file the skill tells the
AI to read. The page maker is run for real: it renders a sample answer with a source on every fact, works
with no internet, refuses a fact with no source, and never overwrites a page."""
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # never leave a compiled file in template/skills: it would ship in every brain

import nonet  # noqa: E402
from test_b7_starter_jobs import (OWNER, ROUTINES, SAMPLE, TEMPLATE, chat_messages, data_files,  # noqa: E402
                                  field, gone_quiet, interactions, involved, job, meetings, reads)
from test_no_network import FORBIDDEN  # noqa: E402

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
import check_brain  # noqa: E402
import jobs  # noqa: E402
from create_brain import create_brain  # noqa: E402

VISUAL = TEMPLATE / "skills" / "show-it-visually"
sys.path.insert(0, str(VISUAL))
import make_page  # noqa: E402

CADENCE = {"morning-brief": "daily", "weekly-review": "weekly", "show-it-visually": "as-needed"}
URL = re.compile(r"(?:https?:)?//[\w.-]+|url\(|@import|@font-face|<link\b|<script\b|<img\b|<iframe\b", re.IGNORECASE)
POINT_LI = re.compile(r'<li>(?P<fact>.*?)<span class="src"><span class="src__k">Source</span>(?P<src>[^<]*)</span></li>')


def morning_brief(brain, today):
    """The stand-in brief: today's meetings, who spoke last in a chat as of today, and one meeting to prepare."""
    on = sorted((m for m in meetings(brain) if m[0] == today), key=lambda m: m[1])
    last = {}
    for f, day, speaker, _ in chat_messages(brain, media=True):
        if day <= today:
            last[f] = (day, speaker)
    waiting = sorted((f, day, who) for f, (day, who) in last.items() if who != OWNER)
    return on, waiting[:3]


def brief_as_answer(on, waiting):
    """The brief written in the shape show-it-visually asks for: a point per fact, each ending with its source."""
    cal = "memory/calendar/events.yaml"
    lines = [f"# {len(on)} meeting today, and {len(waiting)} chat waiting on you",
             "Today's meetings, who spoke last, and the one thing to get ready.", "", "## What's on"]
    lines += [f"- {time} {title}, with {', '.join(who)}. (source: {cal})" for _, time, title, who in on]
    lines += ["", "## Who to reply to"]
    lines += [f"- {who} spoke last in {f.stem.replace('-', ' ')} on {day}. (source: {f.relative_to(SAMPLE).as_posix()})"
              for f, day, who in waiting]
    lines += ["", "## One thing to prepare", f"- Get ready for **{on[0][2]}** at {on[0][1]}. (source: {cal})"]
    return "\n".join(lines) + "\n"


class Kit2SkillFormat(unittest.TestCase):
    def test_each_skill_has_the_header_and_lines_the_spec_asks_for(self):
        """skills/SKILLS.md, "Making a new skill": a name and description header, then Question, Cadence,
        Read, What to do, Show your sources and Never."""
        for brain in (TEMPLATE, SAMPLE):
            for name, question in ROUTINES.items():
                text = job(brain, name)
                head = text.split("---")[1] if text.startswith("---\n") else ""
                self.assertIn(f"\nname: {name}\n", head, name)
                self.assertRegex(head, r"\ndescription: \S.{40,}", name)
                self.assertEqual(field(text, "Question"), question, name)
                self.assertEqual(field(text, "Cadence"), CADENCE[name], name)
                self.assertTrue(reads(brain, name), name)
                self.assertIn("\nWhat to do:", text, name)
                self.assertIn("file", field(text, "Show your sources") or "", name)
                self.assertTrue(field(text, "Never"), name)
                self.assertNotIn("connections/", text, name)
                self.assertNotIn("{{", job(SAMPLE, name), name)

    def test_everything_a_skill_reads_exists_in_a_brain(self):
        for name in ROUTINES:
            for rel in reads(SAMPLE, name):
                self.assertTrue((SAMPLE / rel).exists(), f"{name} reads {rel}, which a brain does not have")
                if rel.startswith("memory/"):
                    self.assertTrue(data_files(SAMPLE, rel), f"{name}: the sample has nothing in {rel}")

    def test_live_sources_come_from_the_connectors_listed_in_tools(self):
        for brain in (TEMPLATE, SAMPLE):
            for name in ("morning-brief", "weekly-review"):
                self.assertIn("tools/TOOLS.md", reads(brain, name), name)
                self.assertIn("connector", job(brain, name), name)

    def test_listed_in_the_skills_index_and_declared_in_the_manifest(self):
        for brain in (TEMPLATE, SAMPLE):
            skills_md = (brain / "skills/SKILLS.md").read_text(encoding="utf-8")
            manifest = (brain / "brain.yaml").read_text(encoding="utf-8")
            for name in ROUTINES:
                self.assertIn(f"`{name}/`", skills_md, f"{name} missing from {brain.name}/skills/SKILLS.md")
                for f in sorted((TEMPLATE / "skills" / name).iterdir()):
                    self.assertIn(f"  - skills/{name}/{f.name}\n", manifest, f"{f.name} not declared in brain.yaml")

    def test_a_new_brain_has_them_with_their_cadence_and_checks_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            found = jobs.jobs(brain)
            for name, cadence in CADENCE.items():
                self.assertEqual(found.get(name), cadence, name)
            self.assertEqual(check_brain.check(brain), [])
            self.assertFalse((brain / "views").exists(), "views/ is made the first time a page is saved, not before")
            self.assertEqual(sorted(p.name for p in (brain / "skills" / "show-it-visually").iterdir()),
                             ["SKILL.md", "make_page.py", "page.html", "style.css"])

    def test_brief_and_review_never_send_and_the_page_never_leaves_the_computer(self):
        for name in ("morning-brief", "weekly-review"):
            never = field(job(TEMPLATE, name), "Never")
            self.assertRegex(never, r"^send, reply, post", name)
            self.assertIn("Never invent", never, name)
        never = field(job(TEMPLATE, "show-it-visually"), "Never")
        for must in ("invent", "offline", "publish", "send", "never overwrite"):
            self.assertIn(must, never)


class MorningBrief(unittest.TestCase):
    def test_a_sample_morning_is_traced_to_files_the_skill_reads(self):
        """15 Mar 2024 in the sample: one meeting (the team offsite with Sam), and Sam spoke last in the
        allotment group three days before. Every point comes from a file morning-brief reads."""
        on, waiting = morning_brief(SAMPLE, "2024-03-15")
        self.assertEqual([(m[2], m[3]) for m in on], [("Team offsite", ["Sam Sample"])])
        self.assertEqual([(f.name, day, who) for f, day, who in waiting],
                         [("allotment-group.md", "2024-03-12", "Sam Sample")])
        allowed = [SAMPLE / rel for rel in reads(SAMPLE, "morning-brief")]
        for f in [SAMPLE / "memory/calendar/events.yaml"] + [f for f, _, _ in waiting]:
            self.assertTrue(any(f == a or a in f.parents for a in allowed), f)

    def test_a_quiet_day_says_so_and_names_the_next_thing(self):
        on, _ = morning_brief(SAMPLE, "2024-02-09")
        self.assertEqual(on, [])
        self.assertTrue([m for m in meetings(SAMPLE) if m[0] > "2024-02-09"], "a next thing to name")
        text = job(TEMPLATE, "morning-brief")
        for must in ("If nothing is on today, say so", "about 150 words", "Up to three people", "One thing to prepare"):
            self.assertIn(must, text)


class WeeklyReview(unittest.TestCase):
    def test_this_week_and_who_has_gone_quiet_come_from_the_files(self):
        today = date(2024, 2, 10)
        week = [m for m in meetings(SAMPLE) if (today - date.fromisoformat(m[0])).days in range(7)]
        self.assertEqual([(m[0], m[2]) for m in week], [("2024-02-08", "Weekly sync")])
        touched = {n for r in interactions(SAMPLE) if (today - date.fromisoformat(r["date"])).days in range(7)
                   for n in involved(r)}
        self.assertEqual(touched, {"Priya Demo", "Sam Sample"})
        # 30 days for the weekly look; the monthly who-have-i-gone-quiet-with skill keeps its 60.
        self.assertEqual([n for n, _, _ in gone_quiet(SAMPLE, "2024-04-20", days=30, top=3)], ["Priya Demo", "Sam Sample"])
        self.assertEqual([n for n, _, _ in gone_quiet(SAMPLE, "2024-04-20", days=60, top=3)], ["Priya Demo"])
        self.assertIn("nothing in the last 30 days", job(TEMPLATE, "weekly-review"))

    def test_saves_one_dated_line_shaped_like_the_rest_of_memory_and_keeps_the_old_lines(self):
        text = job(TEMPLATE, "weekly-review")
        shape = re.search(r"`(\{\"date\": .*?\})`", text).group(1)
        line = json.loads(shape.replace("<today>", "2024-02-10"))
        memory = (TEMPLATE / "memory/MEMORY.md").read_text(encoding="utf-8")
        documented = re.search(r"- `events.jsonl`: `(\{.*?\})`", memory).group(1)
        self.assertEqual(list(line), list(json.loads(documented.replace("high|medium|low", "medium"))))
        self.assertTrue(line["event"].startswith("Weekly review") and "Top three for next week" in line["event"])
        self.assertTrue(line["source"].startswith("weekly-review skill"))
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "b"
            shutil.copytree(SAMPLE, brain)
            events = brain / "memory/events.jsonl"
            events.write_text('{"date": "2024-02-01", "event": "Started my brain", "source": "you said so", '
                              '"confidence": "high"}\n', encoding="utf-8")
            before = events.read_text(encoding="utf-8")
            with events.open("a", encoding="utf-8") as f:  # what the skill asks: add one line at the end
                f.write(json.dumps(line) + "\n")
            after = events.read_text(encoding="utf-8")
            self.assertTrue(after.startswith(before), "an earlier line was changed")
            rows = [json.loads(r) for r in after.splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(r.get("source") and r.get("confidence") in ("high", "medium", "low") for r in rows))
        for must in ("show me the line and ask before saving", "Never change or delete an earlier line"):
            self.assertIn(must, text)


class StyleFile(unittest.TestCase):
    def setUp(self):
        self.css = (VISUAL / "style.css").read_text(encoding="utf-8")
        self.page = (VISUAL / "page.html").read_text(encoding="utf-8")

    def test_no_internet_needed(self):
        """No web font, linked file, picture or script: the page must open with no connection."""
        for name, text in (("style.css", self.css), ("page.html", self.page)):
            self.assertEqual(URL.findall(text), [], name)
        self.assertLess(len(self.css.encode("utf-8")), 8000, "keep the style one small file")

    def test_built_from_the_ai_ops_tokens_in_light_and_dark(self):
        for token in ("#f2f0ea", "#14140f", "#1f5c45", "#eae7de", "#d9d5c8", "#6b6658", "#3a3730"):
            self.assertIn(token, self.css)
        self.assertRegex(self.css, r'--font-display: "Archivo Narrow", "Arial Narrow",[^;]*sans-serif;')
        self.assertRegex(self.css, r"\.label \{[^}]*font-family: var\(--font-mono\)[^}]*text-transform: uppercase")
        self.assertRegex(self.css, r"\.points > li::before \{[^}]*width: 6px; height: 6px; background: var\(--accent\)")
        self.assertIn("@media (prefers-color-scheme: dark)", self.css)
        light = set(re.findall(r"(--[\w-]+):", self.css.split("@media (prefers-color-scheme: dark)")[0]))
        dark_auto = re.search(r':root:not\(\[data-theme="light"\]\) \{(.*?)\}', self.css, re.DOTALL).group(1)
        dark_set = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', self.css, re.DOTALL).group(1)
        colours = {v for v in light if v not in ("--font-display", "--font-body", "--font-mono", "--reading")
                   and not v.startswith("--radius")}
        for block in (dark_auto, dark_set):
            self.assertEqual(set(re.findall(r"(--[\w-]+):", block)), colours)

    def test_the_template_has_every_slot_the_page_maker_fills(self):
        for slot in ("TITLE", "STYLE", "LABEL", "HEADLINE", "SUMMARY", "SECTIONS", "SOURCES", "MADE"):
            self.assertIn(f"[[{slot}]]", self.page, slot)
        self.assertIn('<html lang="en-GB">', self.page)


class PageMaker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.brain = Path(self.tmp.name) / "brain"
        shutil.copytree(SAMPLE, self.brain)
        self.answer = brief_as_answer(*morning_brief(SAMPLE, "2024-03-15"))

    def run_cli(self, *args, answer=None):
        return subprocess.run([sys.executable, "-B", str(VISUAL / "make_page.py"), *args],
                              input=self.answer if answer is None else answer, capture_output=True, text=True,
                              cwd=self.brain, encoding="utf-8")

    def test_renders_a_sample_answer_with_a_source_on_every_fact(self):
        page = make_page.render(self.answer, today=date(2026, 10, 19))
        facts = [line for line in self.answer.splitlines() if line.startswith("- ")]
        points = POINT_LI.findall(page)
        self.assertEqual(len(points), len(facts), "one point on the page for each fact, each with its source")
        allowed = [SAMPLE / rel for rel in reads(SAMPLE, "morning-brief")]
        for fact, src in points:
            self.assertTrue(fact.strip() and src.strip(), (fact, src))
            self.assertTrue((SAMPLE / src).is_file(), f"the source {src} is not a file in the brain")
            self.assertTrue(any(SAMPLE / src == a or a in (SAMPLE / src).parents for a in allowed), src)
        sources = re.findall(r'<li class="chip">([^<]+)</li>', page)
        self.assertEqual(sources, list(dict.fromkeys(src for _, src in points)), "the foot lists every file once")
        self.assertIn((VISUAL / "style.css").read_text(encoding="utf-8").strip(), page, "the style is pasted in whole")
        self.assertIn("<h1>1 meeting today, and 1 chat waiting on you</h1>", page)
        self.assertIn("From your brain · 19 October 2026", page)
        self.assertIn("<strong>Team offsite</strong>", page)
        self.assertNotIn("[[", page)
        self.assertNotIn("shape:", page)
        self.assertEqual(URL.findall(page), [], "the page loads nothing from the internet")

    def test_saves_in_views_with_the_date_and_never_overwrites(self):
        page = make_page.render(self.answer, today=date(2026, 10, 19))
        first = make_page.save(self.brain, page, "My morning, 19 Oct!", today=date(2026, 10, 19))
        second = make_page.save(self.brain, page, "My morning, 19 Oct!", today=date(2026, 10, 19))
        self.assertEqual(first.relative_to(self.brain).as_posix(), "views/2026-10-19-my-morning-19-oct.html")
        self.assertEqual(second.name, "2026-10-19-my-morning-19-oct-2.html")
        self.assertEqual(first.read_text(encoding="utf-8"), page)

    def test_the_command_line_saves_reports_and_prints(self):
        r = self.run_cli(".", "-", "--name", "morning brief")
        self.assertEqual(r.returncode, 0, r.stderr)
        saved = sorted((self.brain / "views").glob("*-morning-brief.html"))
        self.assertEqual(len(saved), 1)
        self.assertIn(f"Saved your page: views/{saved[0].name} (3 points, each with its source). It works offline.",
                      r.stdout)
        r = self.run_cli("--print", ".", "-")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("<!doctype html>"))
        self.assertEqual(len(list((self.brain / "views").iterdir())), 1, "--print saves nothing")

    def test_a_fact_with_no_source_is_refused_and_nothing_is_saved(self):
        answer = self.answer + "- Priya will bring the slides.\n"
        r = self.run_cli(".", "-", answer=answer)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("has no source. End it with (source: <file>): Priya will bring the slides.", r.stderr)
        self.assertFalse((self.brain / "views").exists())
        for bad in ("# A headline\n- A fact with no source.\n",
                    "# A headline\n- A fact. (source: )\n",
                    "No headline here\n- A fact. (source: memory/calendar/events.yaml)\n",
                    "# A headline\n## A section with nothing in it\n",
                    "# A headline\n## Section\nA loose sentence with no source.\n"):
            with self.assertRaises(SystemExit):
                make_page.render(bad)

    def test_refuses_a_folder_that_is_not_a_brain(self):
        page = make_page.render(self.answer)
        with self.assertRaises(SystemExit) as cm:
            make_page.save(Path(self.tmp.name), page, "x")
        self.assertIn("is not a brain folder", str(cm.exception))

    def test_words_in_the_answer_are_shown_as_words_never_run(self):
        answer = ('# A <script>alert(1)</script> headline\n'
                  '- Sam wrote "<b>[[MADE]]</b>" & left. (source: memory/conversations/whatsapp/allotment-group.md)\n')
        page = make_page.render(answer)
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("&lt;b&gt;[[MADE]]&lt;/b&gt;", page, "an answer's words are never taken for a slot")

    def test_uses_no_network_code(self):
        tree = ast.parse((VISUAL / "make_page.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                self.assertNotIn(n.split(".")[0], FORBIDDEN, f"make_page.py imports {n}")


if __name__ == "__main__":
    unittest.main()
