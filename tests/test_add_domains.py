"""create_brain.py --add: more personal domains for a brain that already exists (setup step 5, and step 6
when the review suggests more). It writes exactly what creation would have written, never overwrites a
file, never touches level 1, and running it again changes nothing."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(CORE / "importers"))
import check_brain  # noqa: E402
import common  # noqa: E402
import create_brain as cb  # noqa: E402
import level1  # noqa: E402

SPINE = ("AGENTS.md", "DOMAINS.md", "brain.yaml")


def read(path):
    return Path(path).read_text(encoding="utf-8")


def snapshot(folder):
    """Every file under <folder> and its bytes."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def run_add(brain, names):
    return subprocess.run([sys.executable, str(CORE / "create_brain.py"), str(brain), "--add", names],
                          capture_output=True, text=True)


class AddDomains(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.brain = cb.create_brain(self.root / "brain")  # the default: network only

    def test_adds_folders_instruction_files_and_every_spine_line(self):
        r = run_add(self.brain, "work,family")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(r.stdout.strip().splitlines()), 1, "one plain line of output")
        self.assertIn("Added work, family", r.stdout)
        for name in ("work", "family"):
            self.assertEqual(read(self.brain / name / f"{name.upper()}.md"), read(CORE / "template/domains" / f"{name}.md"))
        _, level2 = level1.split(read(self.brain / "AGENTS.md"))
        routing = level2.split("## Routing table", 1)[1].split("\n## ", 1)[0]
        self.assertIn("| My work, a project or venture, its status or next step | Read `work/WORK.md` first |", routing)
        self.assertIn("| Family, home, a birthday or a family plan | Read `family/FAMILY.md` first |", routing)
        index = level2.split("## File index", 1)[1].split("```")[1]
        self.assertIn("work/              WORK.md, projects.yaml", index)
        self.assertIn("family/            FAMILY.md, family.yaml", index)
        self.assertIn("| family | `family/FAMILY.md` | Home and family life: people, dates, plans |", read(self.brain / "DOMAINS.md"))
        self.assertIn("domains: [network, work, family]", read(self.brain / "brain.yaml"))
        self.assertIn("  - family/FAMILY.md", read(self.brain / "brain.yaml"))
        self.assertEqual(level1.check(self.brain), [])
        self.assertEqual(check_brain.check(self.brain), [])

    def test_the_result_is_what_creation_writes(self):
        """Adding later gives the same spine as choosing the domains at the start."""
        run_add(self.brain, "work,family")
        made = cb.create_brain(self.root / "made", ["network", "work", "family"])
        for name in SPINE + ("CLAUDE.md", "GEMINI.md"):
            self.assertEqual(read(self.brain / name), read(made / name), name)

    def test_running_it_again_changes_nothing(self):
        self.assertEqual(run_add(self.brain, "work,health").returncode, 0)
        before = snapshot(self.brain)
        r = run_add(self.brain, "health,work,network")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), f"Nothing to add: the brain in {self.brain} already has health, work, "
                                           "network. Nothing was changed.")
        self.assertEqual(snapshot(self.brain), before)

    def test_never_overwrites_a_file_and_keeps_the_persons_own_edits(self):
        # The person (or their AI) already made a work folder by hand, wrote in it, filled in level 1
        # and added their own routing line.
        (self.brain / "work").mkdir()
        (self.brain / "work" / "WORK.md").write_text("# Work\n\nMy own words.\n", encoding="utf-8")
        (self.brain / "work" / "projects.yaml").write_text("- name: Launch\n", encoding="utf-8")
        claude = self.brain / "CLAUDE.md"
        claude.write_text(read(claude).replace("- Name: not known yet.", "- Name: Sam Example (you said so)"),
                          encoding="utf-8")
        self.assertEqual(level1.sync(self.brain), [])
        agents = self.brain / "AGENTS.md"
        agents.write_text(read(agents).replace("| Make a new skill | Read `skills/SKILLS.md` |",
                                               "| Make a new skill | Read `skills/SKILLS.md` |\n"
                                               "| My allotment | Read `allotment/ALLOTMENT.md` first |"),
                          encoding="utf-8")
        level1_before = {n: read(self.brain / n) for n in ("CLAUDE.md", "GEMINI.md")}
        r = run_add(self.brain, "work")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(read(self.brain / "work" / "WORK.md"), "# Work\n\nMy own words.\n")
        self.assertEqual(read(self.brain / "work" / "projects.yaml"), "- name: Launch\n")
        self.assertIn("| My allotment | Read `allotment/ALLOTMENT.md` first |", read(agents))
        self.assertIn("Read `work/WORK.md` first", read(agents))
        self.assertIn("Sam Example", level1.split(read(agents))[0])
        self.assertEqual({n: read(self.brain / n) for n in level1_before}, level1_before)
        self.assertEqual(check_brain.check(self.brain), [])

    def test_refuses_and_changes_nothing_when_level_1_copies_differ(self):
        gemini = self.brain / "GEMINI.md"
        gemini.write_text(read(gemini).replace("Name: not known yet.", "Name: Sam."), encoding="utf-8")
        before = snapshot(self.brain)
        r = run_add(self.brain, "work")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("level 1 copies differ", r.stderr)
        self.assertIn("level1.py sync", r.stderr)
        self.assertIn("Nothing was changed", r.stderr)
        self.assertEqual(snapshot(self.brain), before)

    def test_refuses_a_folder_that_is_not_a_brain_and_names_the_line_to_make_one(self):
        empty = self.root / "empty"
        empty.mkdir()
        r = run_add(empty, "work")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is not a brain yet", r.stderr)
        self.assertIn("create_brain.py", r.stderr)
        self.assertEqual(list(empty.iterdir()), [])

    def test_refuses_an_unknown_domain_and_points_to_adding_one_by_hand(self):
        before = snapshot(self.brain)
        r = run_add(self.brain, "work,allotment")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Unknown domain: allotment", r.stderr)
        self.assertIn('"Adding a domain" in DOMAINS.md', r.stderr)
        self.assertEqual(snapshot(self.brain), before)

    def test_refuses_add_with_domains_or_without_a_name(self):
        for args in (["--add", "work", "--domains", "network"], ["--add"], ["--add", "none"]):
            r = subprocess.run([sys.executable, str(CORE / "create_brain.py"), str(self.brain), *args],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, args)

    def test_adding_network_later_moves_the_people_list_where_the_importers_now_write(self):
        bare = cb.create_brain(self.root / "bare", [])
        people = bare / "memory" / "people"
        people.mkdir(parents=True)
        (people / "people.jsonl").write_text('{"id": "person_sam", "source": "you", "confidence": "high"}\n',
                                             encoding="utf-8")
        self.assertEqual(common.people_home(bare), "memory/people")
        r = run_add(bare, "network,work")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("people list moved", r.stdout)
        self.assertEqual(common.people_home(bare), "network")
        self.assertIn("person_sam", read(bare / "network" / "people.jsonl"))
        self.assertFalse((people / "people.jsonl").exists())
        made = cb.create_brain(self.root / "made", ["network", "work"])
        for rel in SPINE + ("skills/mine-my-context/SKILL.md", "skills/prep-my-next-meeting/SKILL.md"):
            self.assertEqual(read(bare / rel), read(made / rel), rel)
        self.assertEqual(check_brain.check(bare), [])

    def test_a_folder_holding_saved_setup_progress_still_counts_as_empty(self):
        """kit/progress.py may write setup.yaml before the brain exists; creation must keep it."""
        dest = self.root / "fresh"
        dest.mkdir()
        (dest / "setup.yaml").write_text('kit_version: "2.0.0"\nstep: 1\n', encoding="utf-8")
        brain = cb.create_brain(dest)
        self.assertEqual(read(brain / "setup.yaml"), 'kit_version: "2.0.0"\nstep: 1\n')
        self.assertEqual(check_brain.check(brain), [])

    def test_printed_lines_follow_check_setup_so_windows_gets_py(self):
        """One place decides python3 or py: check_setup.command. create_brain prints through it."""
        import check_setup
        fake = lambda *args: "py " + " ".join(f'"{a}"' for a in args) if args else "py"  # noqa: E731
        with mock.patch.object(check_setup, "command", fake):
            self.assertTrue(cb.usage().startswith("Usage: py create_brain.py"))
            empty = self.root / "empty"
            empty.mkdir()
            with self.assertRaises(SystemExit) as stop:
                cb.add_domains(empty, ["work"])
            self.assertIn(f'py "{CORE / "create_brain.py"}" "{empty}"', str(stop.exception))
        self.assertTrue(cb.usage().startswith("Usage: py " if check_setup.os.name == "nt" else "Usage: python3 "))


if __name__ == "__main__":
    unittest.main()
