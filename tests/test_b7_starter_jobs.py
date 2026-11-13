"""B7: the week-one skills answer the seven week-one questions, and each answer can be traced to a file
that exists. Checked against the sample brain (made-up people, built only by running the importers).

No AI runs here. Each question gets a scripted stand-in answer, worked out from the files the job tells
the AI to read: if the job points at the wrong folder, or the sample holds nothing that answers it, this
fails. Whether a real AI phrases the answer well is for the clean-machine run, not an offline test."""
import json
import re
import unittest
from pathlib import Path

import nonet

nonet.install()

CORE = Path(__file__).resolve().parents[1]
SAMPLE = CORE / "sample" / "brain"
TEMPLATE = CORE / "template"
OWNER = "Alex Example"  # the made-up person the sample brain belongs to (in every one of their chats)

QUESTIONS = {
    "whats-on-my-plate": "What is on my plate this week?",
    "who-to-reply-to-first": "Who should I reply to first?",
    "who-do-i-know-at": "Who do I know at <an organisation I name>?",
    "draft-in-my-voice": "Draft a message in my voice.",
    "what-am-i-putting-off": "What have I been putting off?",
    "prep-my-next-meeting": "Prep me for my next meeting.",
    "who-have-i-gone-quiet-with": "Who have I gone quiet with?",
}
SETUP = {"mine-my-context": "Who am I, as far as my own files show?"}  # the skill that comes before the starters
MESSAGE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \d{2}:\d{2} \*\*(.+?)\*\*: (.*)$")


def field(text, name):
    m = re.search(rf"^{name}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def job(brain, name):
    return (brain / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def reads(brain, name):
    return [p.strip() for p in field(job(brain, name), "Read").split(",")]


def data_files(brain, rel):
    p = brain / rel
    if p.is_file():
        return [p]
    return [f for f in sorted(p.rglob("*")) if f.is_file() and f.name != "README.md"]


def chat_messages(brain, media=False):
    """(file, date, speaker, text) for every WhatsApp message in the brain. A photo or file someone sent
    still counts as them speaking last; it is skipped only when we want words (media=False)."""
    out = []
    for f in sorted((brain / "memory/conversations/whatsapp").glob("*.md")):
        for line in f.read_text(encoding="utf-8").splitlines():
            m = MESSAGE.match(line)
            if m and (media or "omitted" not in m.group(3)):
                out.append((f, m.group(1), m.group(2), m.group(3)))
    return out


def connections(brain):
    """(name, company) from the brain's merged people list."""
    rows = [json.loads(line) for line in (brain / "network/people.jsonl").read_text(encoding="utf-8").splitlines()]
    return [(r["name"], r["company"]) for r in rows]


def meetings(brain):
    """(date, time, title, with) for every meeting in the brain's calendar file."""
    text = (brain / "memory/calendar/events.yaml").read_text(encoding="utf-8")
    out = []
    for block in re.split(r"^- ", text, flags=re.MULTILINE)[1:]:
        date = re.search(r'^date: "(\d{4}-\d{2}-\d{2})"', block, re.MULTILINE).group(1)
        time = re.search(r"^  time: (.+)$", block, re.MULTILINE).group(1).strip('"')
        title = re.search(r'^  title: "(.*)"', block, re.MULTILINE).group(1)
        out.append((date, time, title, re.findall(r'^    - "(.+)"$', block, re.MULTILINE)))
    return out


def interactions(brain):
    return [json.loads(line) for line in (brain / "network/interactions.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]


def involved(row):
    """Everyone a line of interactions.jsonl involves, besides the owner of the brain."""
    names = list(row.get("with", [])) + [row.get("from"), row.get("to")]
    return {n for n in names if n and n != OWNER}


def people_by_name(brain):
    rows = [json.loads(line) for line in (brain / "network/people.jsonl").read_text(encoding="utf-8").splitlines()]
    return {r["name"]: r for r in rows}


def last_contact(brain, name, before):
    """The person's most recent line in interactions.jsonl dated before <before>, or None."""
    rows = [r for r in interactions(brain) if name in involved(r) and r["date"] < before]
    return max(rows, key=lambda r: (r["date"], r.get("time") or "")) if rows else None


def gone_quiet(brain, today, days=60, top=5):
    """Key people (most lines in interactions.jsonl) whose last contact is <days> or more before <today>,
    most lines first: what the who-have-i-gone-quiet-with skill tells the AI to work out."""
    from datetime import date
    counts = {}
    for r in interactions(brain):
        for n in involved(r):
            counts[n] = counts.get(n, 0) + 1
    out = []
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        last = last_contact(brain, name, today)
        if last and (date.fromisoformat(today) - date.fromisoformat(last["date"])).days >= days:
            out.append((name, n, last))
    return out[:top]


class StarterJobs(unittest.TestCase):
    def assertTraced(self, name, files):
        """Every file an answer came from exists, holds data, and sits where the job says to read."""
        self.assertTrue(files, f"{name}: no file to trace the answer to")
        allowed = [SAMPLE / rel for rel in reads(SAMPLE, name)]
        for f in files:
            self.assertTrue(f.is_file(), f)
            self.assertTrue(any(f == a or a in f.parents for a in allowed),
                            f"{name}: answer came from {f.relative_to(SAMPLE)}, which the job does not tell the AI to read")

    def test_one_skill_per_week_one_question(self):
        for brain in (TEMPLATE, SAMPLE):
            found = {p.parent.name: field(p.read_text(encoding="utf-8"), "Question")
                     for p in (brain / "skills").glob("*/SKILL.md")}
            self.assertEqual(found, {**QUESTIONS, **SETUP}, brain)

    def test_every_skill_has_the_header_the_claude_app_reads(self):
        for name in {**QUESTIONS, **SETUP}:
            text = job(TEMPLATE, name)
            head = text.split("---")[1] if text.startswith("---\n") else ""
            self.assertIn(f"\nname: {name}\n", head, name)
            self.assertRegex(head, r"\ndescription: \S.{40,}", name)

    def test_every_job_names_its_sources_and_never_acts_for_the_person(self):
        for name in {**QUESTIONS, **SETUP}:
            text = job(TEMPLATE, name)
            self.assertIn("file", field(text, "Show your sources") or "", name)
            self.assertTrue(field(text, "Never"), name)
            self.assertIn(field(text, "Cadence"), ("daily", "weekly", "monthly", "as-needed"), name)

    def test_everything_a_job_reads_exists_in_the_sample(self):
        for name in {**QUESTIONS, **SETUP}:
            for rel in reads(SAMPLE, name):
                self.assertTrue((SAMPLE / rel).exists(), f"{name} reads {rel}, which a brain does not have")
                if rel.startswith("memory/"):
                    self.assertTrue(data_files(SAMPLE, rel), f"{name}: the sample has nothing in {rel}")

    def test_live_sources_are_app_connectors_listed_in_tools_not_a_folder(self):
        """There is no connections/ folder any more. A connector the person turns on in their AI app (a
        calendar, mail) is listed in tools/TOOLS.md, and the skills that need live data read that list, so
        someone whose diary lives in a connected calendar is not told their week is empty."""
        for brain in (TEMPLATE, SAMPLE):
            self.assertFalse((brain / "connections").exists(), brain)
            self.assertIn("## Connectors that are on", (brain / "tools/TOOLS.md").read_text(encoding="utf-8"))
            for name in ("whats-on-my-plate", "who-to-reply-to-first", "prep-my-next-meeting",
                         "who-have-i-gone-quiet-with"):
                self.assertIn("tools/TOOLS.md", reads(brain, name), f"{name} in {brain.name}")
            for name in {**QUESTIONS, **SETUP}:
                self.assertNotIn("connections/", job(brain, name), name)

    def test_whats_on_my_plate(self):
        events = SAMPLE / "memory/calendar/events.yaml"
        text = events.read_text(encoding="utf-8")
        dates = re.findall(r'^- date: "(\d{4}-\d{2}-\d{2})"', text, re.MULTILINE)
        self.assertTrue(dates and re.search(r'^  title: "\S', text, re.MULTILINE))
        self.assertTraced("whats-on-my-plate", [events])

    def test_who_should_i_reply_to_first(self):
        last = {}
        for f, _, speaker, _ in chat_messages(SAMPLE, media=True):
            last[f] = speaker
        waiting = {f: who for f, who in last.items() if who != OWNER}
        self.assertEqual({f.name: who for f, who in waiting.items()}, {"allotment-group.md": "Sam Sample"})
        self.assertTraced("who-to-reply-to-first", list(waiting))

    def test_who_do_i_know_at_an_organisation(self):
        people = [n for n, company in connections(SAMPLE) if company == "Demo Analytics"]
        self.assertEqual(people, ["Priya Demo"])
        self.assertTraced("who-do-i-know-at", [SAMPLE / "network/people.jsonl"])

    def test_draft_a_message_in_my_voice(self):
        mine = [(f, text) for f, _, speaker, text in chat_messages(SAMPLE) if speaker == OWNER]
        self.assertGreaterEqual(len(mine), 2, "the job asks for two or three of my own messages to copy")
        self.assertTraced("draft-in-my-voice", sorted({f for f, _ in mine}))

    def test_what_have_i_been_putting_off(self):
        mine = sorted((date, f) for f, date, speaker, _ in chat_messages(SAMPLE) if speaker == OWNER)
        self.assertTrue(mine, "no messages of mine to find a promise in")
        self.assertIn("## Goals this quarter", (SAMPLE / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertTraced("what-am-i-putting-off", [f for _, f in mine] + [SAMPLE / "CLAUDE.md"])


    def test_prep_my_next_meeting(self):
        """On 6 Feb 2024 the next meeting is the 8 Feb weekly sync. Both people in it are in the people list,
        each has an earlier conversation or meeting to recall, and one of them has a chat with my own words in."""
        today = "2024-02-06"
        upcoming = sorted(m for m in meetings(SAMPLE) if m[0] > today)
        date, time, title, attendees = upcoming[0]
        self.assertEqual((date, time, title, sorted(attendees)), ("2024-02-08", "10:00", "Weekly sync",
                                                                  ["Priya Demo", "Sam Sample"]))
        people = people_by_name(SAMPLE)
        self.assertEqual([people[a]["id"] for a in sorted(attendees)], ["person_priya_demo", "person_sam_sample"])
        last = {a: last_contact(SAMPLE, a, today) for a in attendees}
        self.assertEqual({a: (r["date"], r["type"]) for a, r in last.items()},
                         {"Priya Demo": ("2024-02-05", "whatsapp"), "Sam Sample": ("2024-02-01", "meeting")})
        chat = SAMPLE / last["Priya Demo"]["file"]
        mine = [text for f, _, speaker, text in chat_messages(SAMPLE) if f == chat and speaker == OWNER]
        self.assertTrue(mine, "no words of mine in the chat to find a promise in")
        self.assertIn("## Goals this quarter", (SAMPLE / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertTraced("prep-my-next-meeting", [SAMPLE / "memory/calendar/events.yaml",
                                                   SAMPLE / "network/people.jsonl",
                                                   SAMPLE / "network/interactions.jsonl", chat,
                                                   SAMPLE / "CLAUDE.md"])

    def test_prep_says_so_when_someone_is_not_in_the_brain(self):
        text = job(TEMPLATE, "prep-my-next-meeting")
        self.assertIn('"not in the brain"', text)
        self.assertIn("about 200 words", text)
        self.assertIn("Three questions", text)
        self.assertIn("calendar connector", text)
        self.assertNotIn("Ada Nobody", people_by_name(SAMPLE))  # a name that must come back as no match

    def test_who_have_i_gone_quiet_with(self):
        """Ranked by how often we were in touch, kept only past 60 days of silence."""
        quiet = gone_quiet(SAMPLE, "2024-06-15")
        self.assertEqual([(name, last["date"]) for name, _, last in quiet],
                         [("Priya Demo", "2024-02-08"), ("Sam Sample", "2024-03-15"), ("Jo Placeholder", "2024-04-10")])
        self.assertEqual([name for name, _, _ in gone_quiet(SAMPLE, "2024-05-01")], ["Priya Demo"])
        self.assertEqual(gone_quiet(SAMPLE, "2024-02-10"), [])
        self.assertTrue(all(last.get("title") or last.get("content") for _, _, last in quiet), "no topic to name")
        mine = [(f, text) for f, _, speaker, text in chat_messages(SAMPLE) if speaker == OWNER]
        self.assertGreaterEqual(len(mine), 2, "the draft copies my style from two of my own messages")
        self.assertTraced("who-have-i-gone-quiet-with", [SAMPLE / "network/interactions.jsonl",
                                                         SAMPLE / "network/people.jsonl"]
                          + sorted({f for f, _ in mine}))

    def test_gone_quiet_only_drafts_in_my_voice(self):
        text = job(TEMPLATE, "who-have-i-gone-quiet-with")
        self.assertIn("skills/draft-in-my-voice/SKILL.md", reads(TEMPLATE, "who-have-i-gone-quiet-with"))
        for must in ("60 days", "top 5", "Show the drafts only"):
            self.assertIn(must, text)
        self.assertRegex(field(text, "Never"), r"^send, post or schedule")

    def test_every_starter_skill_is_listed_in_every_index(self):
        """A skill nobody can find is a skill nobody runs: each one is in SKILLS.md, the routing table in
        AGENTS.md and the brain.yaml manifest, in the template and the sample, and counted in the kit's guides."""
        for brain in (TEMPLATE, SAMPLE):
            skills_md = (brain / "skills/SKILLS.md").read_text(encoding="utf-8")
            agents = (brain / "AGENTS.md").read_text(encoding="utf-8").split("## Routing table", 1)[1].split("\n## ", 1)[0]
            manifest = (brain / "brain.yaml").read_text(encoding="utf-8")
            for name in {**QUESTIONS, **SETUP}:
                self.assertIn(f"`{name}/`", skills_md, f"{name} missing from {brain.name}/skills/SKILLS.md")
                self.assertIn(f"skills/{name}/SKILL.md", agents, f"{name} missing from {brain.name}/AGENTS.md")
                self.assertIn(f"  - skills/{name}/SKILL.md\n", manifest, f"{name} missing from {brain.name}/brain.yaml")
            self.assertIn("Eight skills ship with the brain", skills_md)
        # 16 Oct 2026: the guides said "seven starter skills" while eight ship. Every count is the total.
        words = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
        for guide in ("README.md", "INSTRUCTIONS.md"):
            text = (CORE / guide).read_text(encoding="utf-8")
            counts = re.findall(r"\b(five|six|seven|eight|nine) (?:starter )?skills", text)
            self.assertTrue(counts, guide)
            self.assertEqual({words[c] for c in counts}, {len(QUESTIONS) + len(SETUP)}, guide)
        self.assertIn("prep me for my next meeting, who have I gone quiet with",
                      (CORE / "INSTRUCTIONS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
