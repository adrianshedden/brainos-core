import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import nonet

nonet.install()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jobs  # noqa: E402
import check_brain  # noqa: E402
from create_brain import create_brain  # noqa: E402

CORE = Path(__file__).resolve().parents[1]
STARTERS = {
    "whats-on-my-plate": "weekly",
    "who-to-reply-to-first": "daily",
    "who-do-i-know-at": "as-needed",
    "draft-in-my-voice": "as-needed",
    "what-am-i-putting-off": "weekly",
    "mine-my-context": "as-needed",
    "prep-my-next-meeting": "as-needed",
    "who-have-i-gone-quiet-with": "monthly",
    "morning-brief": "daily",
    "weekly-review": "weekly",
    "show-it-visually": "as-needed",
}


class JobTracker(unittest.TestCase):
    """B7: jobs.py, the to-do list over the brain's skills/. Not the paid organiser."""

    def test_seven_starter_skills_and_mine_my_context_with_declared_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            self.assertEqual(jobs.jobs(brain), STARTERS)
            self.assertEqual(check_brain.check(brain), [])  # declared in brain.yaml, no personal data

    def test_never_done_job_is_due_fixed_cadence_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            rows = {name: status for name, _, status in jobs.list_jobs(brain)}
            self.assertEqual(rows["whats-on-my-plate"], "due (never done)")
            self.assertEqual(rows["who-do-i-know-at"], "no fixed cadence")

    def test_mark_done_then_not_due_until_cadence_elapses(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            today = date(2024, 6, 10)
            done_date = jobs.mark_done(brain, "whats-on-my-plate", today=today)
            self.assertEqual(done_date, "2024-06-10")
            rows = {name: status for name, _, status in jobs.list_jobs(brain, today=today + timedelta(days=3))}
            self.assertEqual(rows["whats-on-my-plate"], "not due (last done 2024-06-10)")
            rows = {name: status for name, _, status in jobs.list_jobs(brain, today=today + timedelta(days=7))}
            self.assertEqual(rows["whats-on-my-plate"], "due (last done 2024-06-10)")

    def test_broken_state_file_counts_as_nothing_done_and_is_repaired(self):
        """The brain is the person's own folder: they can edit or break this file, and syncing a
        brain between machines can mangle it. It must never turn `list` into a traceback."""
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            for broken in ('{"whats-on-my-plate": "last tuesday"}', '["whats-on-my-plate"]', 'not json at all'):
                jobs.state_path(brain).write_text(broken, encoding="utf-8")
                rows = {name: status for name, _, status in jobs.list_jobs(brain)}
                self.assertEqual(rows["whats-on-my-plate"], "due (never done)")
            today = date(2024, 6, 10)
            jobs.mark_done(brain, "whats-on-my-plate", today=today)
            rows = {name: status for name, _, status in jobs.list_jobs(brain, today=today)}
            self.assertEqual(rows["whats-on-my-plate"], "not due (last done 2024-06-10)")

    def test_unknown_job_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            with self.assertRaises(SystemExit):
                jobs.mark_done(brain, "does-not-exist")

    def test_cli_list_and_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            r = subprocess.run([sys.executable, str(CORE / "jobs.py"), "list", str(brain)],
                                check=True, capture_output=True, text=True)
            self.assertIn("whats-on-my-plate", r.stdout)
            self.assertIn("due (never done)", r.stdout)
            r = subprocess.run([sys.executable, str(CORE / "jobs.py"), "done", str(brain), "whats-on-my-plate"],
                                check=True, capture_output=True, text=True)
            self.assertIn("Marked whats-on-my-plate done", r.stdout)

    def test_the_brain_has_its_own_copy_and_a_skill_can_be_named_three_ways(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            self.assertEqual((brain / "scripts" / "jobs.py").read_bytes(), (CORE / "jobs.py").read_bytes())
            r = subprocess.run([sys.executable, "scripts/jobs.py", "done", ".", "skills/who-do-i-know-at/SKILL.md"],
                                cwd=brain, check=True, capture_output=True, text=True)
            self.assertIn("Marked", r.stdout)
            for name in ("whats-on-my-plate.md", "skills/whats-on-my-plate/"):
                jobs.mark_done(brain, name, today=date(2024, 6, 10))
            self.assertEqual(sorted(jobs.load_state(brain)), ["whats-on-my-plate", "who-do-i-know-at"])


if __name__ == "__main__":
    unittest.main()
