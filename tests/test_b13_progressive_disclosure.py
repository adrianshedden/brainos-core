"""B13: the brain is set out by progressive disclosure. Level 1 CLAUDE.md, level 2
AGENTS.md, level 3 one {DOMAIN}.md per folder. Five core domains in every brain (automations, memory,
scripts, skills, tools), plus the personal domains the person chooses. brain / memory / hands is a mental
model only: never folders. People from every import are one merged list, every JSONL line says where it
came from and how sure it is, and mine-my-context turns the imports into confirmed context."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "importers"))
sys.path.insert(0, str(CORE))
import calendar_ics  # noqa: E402
import check_brain  # noqa: E402
import linkedin  # noqa: E402
import whatsapp  # noqa: E402
from create_brain import DOMAINS, create_brain  # noqa: E402

EX = CORE / "sample" / "exports"
SPINE = ("CLAUDE.md", "AGENTS.md", "DOMAINS.md")
CORE_DOMAINS = ("automations", "memory", "scripts", "skills", "tools")


def lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def routes(brain):
    """The routing table in AGENTS.md: the rows between its header and the next heading."""
    text = (brain / "AGENTS.md").read_text(encoding="utf-8")
    table = text.split("## Routing table", 1)[1].split("\n## ", 1)[0]
    return [row for row in table.splitlines() if row.startswith("| ") and not row.startswith("| When")]


class Spine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_spine_files_are_there_and_say_what_level_they_are(self):
        brain = create_brain(Path(self.tmp.name) / "b")
        for name in SPINE:
            self.assertTrue((brain / name).is_file(), name)
        claude = (brain / "CLAUDE.md").read_text(encoding="utf-8")
        for must in ("## Who this is for", "## How to start a session", "## Rules", "AGENTS.md",
                     "Only the person's own data", "processed by that provider", "`source`", "`confidence`"):
            self.assertIn(must, claude)
        agents = (brain / "AGENTS.md").read_text(encoding="utf-8")
        for must in ("## Routing table", "## File index", "## Conventions", "`source`", "`confidence`"):
            self.assertIn(must, agents)
        self.assertEqual(check_brain.check(brain), [])

    def test_five_core_domains_each_with_its_own_domain_file(self):
        brain = create_brain(Path(self.tmp.name) / "b", [])
        domains = (brain / "DOMAINS.md").read_text(encoding="utf-8")
        for name in CORE_DOMAINS:
            own = brain / name / f"{name.upper()}.md"
            self.assertTrue(own.is_file(), own)
            self.assertIn(f"`{name}/{name.upper()}.md`", domains)
            self.assertGreater(len(own.read_text(encoding="utf-8")), 200, own)

    def test_chosen_personal_domains_are_made_listed_and_routed(self):
        brain = create_brain(Path(self.tmp.name) / "b", ["network", "work", "family"])
        domains = (brain / "DOMAINS.md").read_text(encoding="utf-8")
        routed = "\n".join(routes(brain))
        index = (brain / "AGENTS.md").read_text(encoding="utf-8").split("## File index", 1)[1]
        declared = check_brain.declared_files(brain)
        for name in ("network", "work", "family"):
            own = f"{name}/{name.upper()}.md"
            self.assertTrue((brain / own).is_file(), own)
            self.assertIn(f"`{own}`", domains)
            self.assertIn(f"Read `{own}` first", routed)
            self.assertIn(f"\n{name}/ ", index)
            self.assertIn(own, declared)
            text = (brain / own).read_text(encoding="utf-8")
            for heading in ("## What goes in", "## What stays out", "## What's here"):
                self.assertIn(heading, text, own)
        for name in set(DOMAINS) - {"network", "work", "family"}:
            self.assertFalse((brain / name).exists(), name)
            self.assertNotIn(f"`{name}/{name.upper()}.md`", domains)
            self.assertNotIn(f"`{name}/{name.upper()}.md`", routed)
        self.assertEqual(check_brain.check(brain), [])

    def test_the_command_line_takes_domains_and_refuses_one_it_does_not_know(self):
        dest = Path(self.tmp.name) / "b"
        r = subprocess.run([sys.executable, str(CORE / "create_brain.py"), str(dest), "--domains", "work,health"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("personal domains: work, health", r.stdout)
        self.assertTrue((dest / "health" / "HEALTH.md").is_file())
        self.assertFalse((dest / "network").exists())
        other = Path(self.tmp.name) / "c"
        r = subprocess.run([sys.executable, str(CORE / "create_brain.py"), str(other), "--domains", "network,hobbies"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Unknown domain: hobbies", r.stderr)
        self.assertFalse(other.exists())

    def test_network_is_the_default_and_none_means_none(self):
        default = create_brain(Path(self.tmp.name) / "b")
        self.assertTrue((default / "network" / "NETWORK.md").is_file())
        bare = create_brain(Path(self.tmp.name) / "c", [])
        self.assertEqual(sorted(p.name for p in bare.iterdir() if p.is_dir()), sorted(CORE_DOMAINS + ("exports",)))
        self.assertIn("(none yet)", (bare / "DOMAINS.md").read_text(encoding="utf-8"))
        self.assertEqual(check_brain.check(bare), [])

    def test_no_brain_hands_or_connections_folders_and_no_hands_wording(self):
        for brain in (create_brain(Path(self.tmp.name) / "b", list(DOMAINS)), CORE / "sample" / "brain",
                      CORE / "template"):
            for gone in ("brain", "hands", "connections", "ai-tools"):
                self.assertFalse((brain / gone).exists(), f"{brain}: {gone}/")
            for f in brain.rglob("*.md"):
                text = f.read_text(encoding="utf-8").lower()
                if f.relative_to(brain).as_posix() == "README.md":
                    # the agreed shared line replaces brain/memory/hands (agreed 15 Oct 2026)
                    self.assertEqual(sum("hands" in line for line in text.splitlines()), 0, f)
                    self.assertIn("everything the ai remembers about you", text, f)
                else:
                    self.assertNotRegex(text, r"\bhands\b", f)
                    self.assertNotIn("connections/", text, f)


class People(unittest.TestCase):
    """LinkedIn, WhatsApp and the calendar all name Priya Demo. She is one person in one list."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zip = Path(self.tmp.name) / "li.zip"
        with zipfile.ZipFile(self.zip, "w") as zf:
            for f in sorted((EX / "linkedin").glob("*.csv")):
                zf.write(f, f.name)

    def import_all(self, brain, order=("linkedin", "whatsapp", "calendar")):
        for name in order:
            if name == "linkedin":
                linkedin.run(self.zip, brain)
            elif name == "whatsapp":
                whatsapp.run(EX / "whatsapp", brain, me="Alex Example")
            else:
                calendar_ics.run(EX / "calendar" / "calendar.ics", brain, me="alex@example.com")

    def test_people_merged_across_linkedin_whatsapp_and_calendar(self):
        brain = create_brain(Path(self.tmp.name) / "b")
        self.import_all(brain)
        people = lines(brain / "network" / "people.jsonl")
        names = [p["name"] for p in people]
        self.assertEqual(len(names), len(set(names)), names)  # nobody twice
        self.assertEqual(len({p["id"] for p in people}), len(people))
        priya = next(p for p in people if p["name"] == "Priya Demo")
        self.assertEqual(priya["source"], ["calendar", "linkedin", "whatsapp"])
        self.assertEqual(priya["emails"], ["priya@example.com"])
        self.assertEqual(priya["company"], "Demo Analytics")
        self.assertEqual(priya["from"]["calendar"]["meetings"], 7)
        self.assertEqual(priya["from"]["whatsapp"]["chats"], ["priya-demo"])
        self.assertNotIn("Alex Example", names)  # the owner is not their own contact
        self.assertFalse((brain / "memory" / "people").exists())

    def test_every_jsonl_line_has_source_and_confidence(self):
        brain = create_brain(Path(self.tmp.name) / "b")
        self.import_all(brain)
        files = sorted(brain.rglob("*.jsonl"))
        self.assertIn(brain / "network" / "people.jsonl", files)
        self.assertIn(brain / "network" / "interactions.jsonl", files)
        for f in files:
            for line in lines(f):
                self.assertTrue(line.get("source"), f"{f.name}: {line}")
                self.assertIn(line.get("confidence"), ("high", "medium", "low"), f"{f.name}: {line}")
        kinds = {r["type"] for r in lines(brain / "network" / "interactions.jsonl")}
        self.assertEqual(kinds, {"linkedin_message", "whatsapp", "meeting"})

    def test_re_import_is_idempotent_and_ids_are_stable(self):
        brain = create_brain(Path(self.tmp.name) / "b")
        self.import_all(brain)
        people, talks = (brain / "network" / "people.jsonl").read_bytes(), (brain / "network" / "interactions.jsonl").read_bytes()
        self.import_all(brain)
        self.assertEqual((brain / "network" / "people.jsonl").read_bytes(), people)
        self.assertEqual((brain / "network" / "interactions.jsonl").read_bytes(), talks)
        ids = {p["name"]: p["id"] for p in lines(brain / "network" / "people.jsonl")}
        self.import_all(brain, order=("calendar", "whatsapp", "linkedin"))
        self.assertEqual({p["name"]: p["id"] for p in lines(brain / "network" / "people.jsonl")}, ids)

    def test_a_note_added_by_hand_survives_a_re_import(self):
        brain = create_brain(Path(self.tmp.name) / "b")
        self.import_all(brain)
        path = brain / "network" / "people.jsonl"
        rows = lines(path)
        rows[0]["notes"] = "met at the allotment"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        self.import_all(brain)
        self.assertEqual(lines(path)[0]["notes"], "met at the allotment")

    def test_without_a_network_domain_people_go_to_memory_people(self):
        brain = create_brain(Path(self.tmp.name) / "b", ["work"])
        self.import_all(brain)
        self.assertFalse((brain / "network").exists())
        self.assertTrue(any(p["name"] == "Priya Demo" for p in lines(brain / "memory" / "people" / "people.jsonl")))
        self.assertTrue(lines(brain / "memory" / "people" / "interactions.jsonl"))
        self.assertIn("memory/people/people.jsonl", (brain / "AGENTS.md").read_text(encoding="utf-8"))

    def test_chats_imported_one_at_a_time_all_count(self):
        brain = create_brain(Path(self.tmp.name) / "b")
        for chat in sorted((EX / "whatsapp").glob("*.txt")):
            whatsapp.run(chat, brain, me="Alex Example")
        chats = [r for r in lines(brain / "network" / "interactions.jsonl") if r["type"] == "whatsapp"]
        self.assertEqual(sorted(r["file"] for r in chats), ["memory/conversations/whatsapp/allotment-group.md",
                                                            "memory/conversations/whatsapp/priya-demo.md"])
        self.assertNotIn("Alex Example", [p["name"] for p in lines(brain / "network" / "people.jsonl")])


class MineMyContext(unittest.TestCase):
    def test_the_skill_is_there_routed_and_follows_the_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            skill = brain / "skills" / "mine-my-context" / "SKILL.md"
            self.assertTrue(skill.is_file())
            self.assertIn("skills/mine-my-context/SKILL.md", "\n".join(routes(brain)))
            self.assertIn("mine-my-context", (brain / "CLAUDE.md").read_text(encoding="utf-8"))
            text = skill.read_text(encoding="utf-8")
            stages = [text.index(h) for h in ("## 1. Gather", "## 2. Make sense of it", "## 3. Confirm, then write")]
            self.assertEqual(stages, sorted(stages))  # extraction, then analysis, then populate
            read = re.search(r"^Read: (.+)$", text, re.M).group(1)
            for must in ("memory/", "network/"):
                self.assertIn(must, read)
            for must in ("at most five short questions", "CLAUDE.md", "{DOMAIN}.md", "memory/decisions.jsonl",
                         "source", "confidence", "Goals this quarter", "Key people", "personal domains"):
                self.assertIn(must, text)
            self.assertRegex(text, r"Never: invent a fact")

    def test_the_kit_runs_in_the_build_along_order(self):
        steps = ["check_setup.py", "Choose the personal domains", "create_brain.py <folder> --domains",
                 "Import whichever exports", "Mine my context", "First skills"]
        text = (CORE / "INSTRUCTIONS.md").read_text(encoding="utf-8")
        at = [text.index(s) for s in steps]
        self.assertEqual(at, sorted(at), "INSTRUCTIONS.md steps are out of order")
        readme = (CORE / "README.md").read_text(encoding="utf-8")
        at = [readme.index(s) for s in ("check_setup.py", "Choose your personal domains", "--domains",
                                        "importers/linkedin.py", "mine-my-context", "Try the eight skills")]
        self.assertEqual(at, sorted(at), "README.md steps are out of order")


if __name__ == "__main__":
    unittest.main()
