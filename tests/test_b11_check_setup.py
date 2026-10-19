"""B11: the setup check. Read-only, always exit 0 on good arguments, names every export in exports/
with the exact importer line to run, and gives one next step. No network."""
import shlex
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
sys.path.insert(0, str(CORE))
import check_setup  # noqa: E402
from create_brain import create_brain  # noqa: E402
import whatsapp  # noqa: E402

EX = CORE / "sample" / "exports"


def said(folder):
    lines = []
    check_setup.main([str(folder)], out=lines.append)
    return lines


def snapshot(folder):
    folder = Path(folder)
    if not folder.exists():
        return None
    return sorted((p.relative_to(folder).as_posix(), p.stat().st_mtime_ns, p.stat().st_size)
                  for p in folder.rglob("*"))


def zip_of(dest, files, arcname=lambda p: p.name):
    with zipfile.ZipFile(dest, "w") as zf:
        for f in files:
            zf.write(f, arcname(f))


def fill_exports(exports):
    """One of every export BrainOS reads, named the way the services name them, plus one it does not."""
    zip_of(exports / "Basic_LinkedInDataExport_10-15-2026.zip", sorted((EX / "linkedin").glob("*.csv")))
    zip_of(exports / "twitter-2026-10-15.zip", sorted((EX / "x" / "data").glob("*.js")),
           arcname=lambda p: f"data/{p.name}")
    shutil.copy(EX / "whatsapp" / "WhatsApp Chat with Priya Demo.txt", exports)
    zip_of(exports / "WhatsApp Chat - Allotment Group.zip", [EX / "whatsapp" / "WhatsApp Chat with Allotment Group.txt"],
           arcname=lambda p: "_chat.txt")
    shutil.copy(EX / "calendar" / "calendar.ics", exports)
    zip_of(exports / "me@example.com.ical.zip", [EX / "calendar" / "calendar.ics"], arcname=lambda p: "me@example.com.ics")
    shutil.copy(EX / "apple" / "contacts.vcf", exports)
    (exports / "holiday-photo.jpg").write_bytes(b"\xff\xd8\xff not an export")


EXPECTED = {
    "Basic_LinkedInDataExport_10-15-2026.zip": "linkedin.py",
    "twitter-2026-10-15.zip": "x_export.py",
    "WhatsApp Chat with Priya Demo.txt": "whatsapp.py",
    "WhatsApp Chat - Allotment Group.zip": "whatsapp.py",
    "calendar.ics": "calendar_ics.py",
    "me@example.com.ical.zip": "calendar_ics.py",
    "contacts.vcf": "apple_contacts.py",
}


class CheckSetup(unittest.TestCase):
    def test_missing_folder_is_reported_and_not_made(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "my-brain"
            lines = said(folder)
            text = "\n".join(lines)
            self.assertIn("does not exist yet", text)
            self.assertTrue(lines[-1].startswith("Next step: Choose the personal domains"), lines[-1])
            self.assertIn("make the brain:", lines[-1])
            self.assertIn("create_brain.py", lines[-1])
            self.assertIn("--domains network", lines[-1])
            self.assertFalse(folder.exists())

    def test_reports_python_and_kit(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = "\n".join(said(tmp))
            self.assertIn(f"Python: {sys.version_info[0]}.{sys.version_info[1]}", text)
            self.assertIn("all the files it needs are here", text)
            self.assertIn("is empty and ready for create_brain.py", text)

    def test_a_folder_that_is_not_a_brain_is_not_mistaken_for_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tax-return.pdf").write_text("x")
            lines = said(tmp)
            self.assertIn("is not a brain", "\n".join(lines))
            self.assertIn("new, empty folder", lines[-1])

    def test_names_every_export_with_the_exact_importer_line_and_the_lines_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "my brain")  # a space, so the line must quote paths
            fill_exports(brain / "exports")
            before = snapshot(brain)
            lines = said(brain)
            self.assertEqual(snapshot(brain), before, "the check changed something")

            commands = {}
            for i, line in enumerate(lines):
                for name, script in EXPECTED.items():
                    if line.startswith(f"- {name}: looks like"):
                        commands[name] = lines[i + 1].strip()
                        self.assertIn(f"importers/{script}", commands[name].replace("\\", "/"), name)
            self.assertEqual(set(commands), set(EXPECTED), "\n".join(lines))
            self.assertTrue(any(l.startswith("- holiday-photo.jpg: not recognised") for l in lines))
            self.assertFalse(any("README.md" in l for l in lines))
            self.assertTrue(lines[-1].startswith("Next step: Run the import lines above, one at a time. Then "), lines[-1])
            self.assertIn("mine-my-context", lines[-1])

            # WhatsApp needs the person's own name first (B14): the check says to ask, once.
            self.assertTrue(any("their own name as it shows in their WhatsApp chats" in l for l in lines))
            whatsapp.save_names(brain, ["Alex Example"])
            self.assertFalse(any("their own name as it shows" in l for l in said(brain)), "asked twice")

            # Every printed line is a real command: running it imports the export into the brain.
            for name, command in commands.items():
                argv = shlex.split(command)
                self.assertEqual(argv[0], "python3")
                self.assertEqual(argv[-1], str(brain.resolve()))
                r = subprocess.run([sys.executable, *argv[1:]], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{name}: {r.stderr}")
            for rel in ("network/people.jsonl", "network/interactions.jsonl", "memory/conversations/x-posts.yaml",
                        "memory/conversations/whatsapp/priya-demo.md", "memory/calendar/events.yaml",
                        "memory/profile/linkedin-profile.md"):
                self.assertTrue((brain / rel).is_file(), rel)

    def test_empty_exports_says_where_to_put_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            lines = said(brain)
            self.assertIn("- None yet.", lines)
            self.assertIn(str((brain / "exports").resolve()), lines[-1])

    def test_existing_notes_are_named_and_need_no_import(self):
        # Drummond call, 19 Oct 2026: an Obsidian folder or a Notion export is one more source. Nothing imports
        # it; the AI reads it when it gets to know the person.
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            vault = brain / "exports" / "My Vault"
            (vault / "Projects").mkdir(parents=True)
            (vault / "Projects" / "Launch plan.md").write_text("# Launch plan\n", encoding="utf-8")
            (vault / ".obsidian").mkdir()
            zip_of(brain / "exports" / "Export-notion.zip", [vault / "Projects" / "Launch plan.md"])
            before = snapshot(brain)
            lines = said(brain)
            self.assertEqual(snapshot(brain), before, "the check changed something")
            for name in ("My Vault", "Export-notion.zip"):
                line = next(l for l in lines if l.startswith(f"- {name}:"))
                self.assertIn("your existing notes", line)
                self.assertIn("Nothing to import", line)
            self.assertNotIn("Import it with:", "\n".join(lines))
            self.assertIn("Your notes are in.", lines[-1])

    def test_a_folder_holding_only_the_kit_and_saved_progress_is_ready_for_a_brain(self):
        """The terminal line leaves a folder with only kit/ in it, and setup.yaml may be there too: the same
        things create_brain.py accepts. Anything else still makes it "not a brain"."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "b"
            (folder / "kit").mkdir(parents=True)
            (folder / "exports").mkdir()
            (folder / "setup.yaml").write_text("step: 1\n", encoding="utf-8")
            self.assertEqual(check_setup.brain_state(folder), "empty")
            self.assertIn("is empty and ready for create_brain.py", "\n".join(said(folder)))
            (folder / "notes.txt").write_text("mine", encoding="utf-8")
            self.assertEqual(check_setup.brain_state(folder), "not-empty")

    def test_the_kit_check_needs_the_kit_2_files(self):
        for rel in ("connections.yaml", "importers/from_connector.py", "progress.py"):
            self.assertIn(rel, check_setup.NEEDED)
            self.assertTrue((CORE / rel).is_file(), rel)

    def test_a_brain_made_before_the_exports_folder_is_told_to_make_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            shutil.rmtree(brain / "exports")
            lines = said(brain)
            self.assertIn("Make a folder called exports", lines[-1])
            self.assertFalse((brain / "exports").exists())

    def test_exports_put_in_first_are_listed_and_create_brain_keeps_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "b"
            (folder / "exports").mkdir(parents=True)
            shutil.copy(EX / "apple" / "contacts.vcf", folder / "exports")
            lines = said(folder)
            self.assertIn("is empty and ready for create_brain.py", "\n".join(lines))
            self.assertTrue(any(l.startswith("- contacts.vcf: looks like an Apple Contacts export") for l in lines))
            self.assertIn("create_brain.py", lines[-1])
            create_brain(folder)
            self.assertTrue((folder / "brain.yaml").is_file())
            self.assertTrue((folder / "exports" / "contacts.vcf").is_file())

    def test_exit_code_is_zero_whatever_it_finds_and_non_zero_only_for_bad_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "junk.txt").write_text("not a brain")
            for folder in (tmp, str(Path(tmp) / "nope")):
                r = subprocess.run([sys.executable, str(CORE / "check_setup.py"), folder], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("Next step:", r.stdout)
            for argv in ([], [tmp, "extra"], ["--help"]):
                r = subprocess.run([sys.executable, str(CORE / "check_setup.py"), *argv], capture_output=True, text=True)
                self.assertNotEqual(r.returncode, 0, argv)
                self.assertIn("Usage:", r.stderr)


    def test_windows_lines_use_py_and_double_quotes(self):
        # On Windows `python3` is missing or opens the Microsoft Store, and cmd.exe ignores single quotes.
        import check_setup
        line = check_setup.command(r"C:\Users\A B\brain\kit\importers\whatsapp.py", r"C:\Users\A B\brain\exports\chat.txt", ".", windows=True)
        self.assertTrue(line.startswith("py "), line)
        self.assertIn('"C:\\Users\\A B\\brain\\exports\\chat.txt"', line)
        self.assertNotIn("'", line)
        self.assertTrue(check_setup.command("x.py", windows=False).startswith("python3 "))

if __name__ == "__main__":
    unittest.main()
