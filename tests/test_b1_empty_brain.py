import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
import check_brain  # noqa: E402

CORE = Path(__file__).resolve().parents[1]


class EmptyBrain(unittest.TestCase):
    def test_create_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "my-brain"
            subprocess.run([sys.executable, str(CORE / "create_brain.py"), str(brain)], check=True, capture_output=True)
            self.assertEqual(check_brain.check(brain), [])

    def test_refuses_non_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.txt").write_text("keep me")
            r = subprocess.run([sys.executable, str(CORE / "create_brain.py"), tmp], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["x.txt"])

    def test_exports_folder_ships_with_a_readme_and_is_kept_out_of_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "b"
            subprocess.run([sys.executable, str(CORE / "create_brain.py"), str(brain)], check=True, capture_output=True)
            readme = (brain / "exports" / "README.md").read_text(encoding="utf-8")
            for kind in ("LinkedIn", "WhatsApp", ".ics", ".vcf", "X archive", "Downloads", "never included in the GitHub backup"):
                self.assertIn(kind, readme)
            self.assertIn("exports/*", (brain / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_a_folder_holding_only_exports_becomes_a_brain_and_keeps_them(self):
        """The person may drop their exports in first. create_brain must not refuse, nor touch them."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "exports").mkdir()
            (Path(tmp) / "exports" / "contacts.vcf").write_text("BEGIN:VCARD")
            subprocess.run([sys.executable, str(CORE / "create_brain.py"), tmp], check=True, capture_output=True)
            self.assertEqual(check_brain.check(tmp), [])
            self.assertEqual((Path(tmp) / "exports" / "contacts.vcf").read_text(), "BEGIN:VCARD")

    def test_checker_catches_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "b"
            subprocess.run([sys.executable, str(CORE / "create_brain.py"), str(brain)], check=True, capture_output=True)
            (brain / "skills" / "SKILLS.md").unlink()
            (brain / "CLAUDE.md").write_text("Reach me at someone@hotmail.co.uk")
            (brain / "tools" / "TOOLS.md").write_text("{{PEOPLE}} left unfilled")
            found = "\n".join(check_brain.check(brain))
            self.assertIn("declared file missing: skills/SKILLS.md", found)
            self.assertIn("hotmail", found)
            self.assertIn("CLAUDE.md is too short", found)
            self.assertIn("unfilled placeholder in tools/TOOLS.md", found)


if __name__ == "__main__":
    unittest.main()
