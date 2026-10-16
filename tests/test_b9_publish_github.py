"""B9: publish the brain to the person's own GitHub (free edition, so bootcamp attendees have it too).
No network: the 'remote' is a local bare git repo reached by filesystem path, never a real github.com URL."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
import nonet  # noqa: E402

nonet.install()
import publish_github  # noqa: E402
from create_brain import create_brain  # noqa: E402

QUIET = lambda _: None  # noqa: E731


def bare_remote(tmp):
    remote = Path(tmp) / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    return remote


def remote_log(remote):
    r = subprocess.run(["git", "--git-dir", str(remote), "log", "--oneline"], capture_output=True, text=True)
    return r.stdout


class PublishGithub(unittest.TestCase):
    def test_dry_run_prints_plan_and_touches_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            r = subprocess.run([sys.executable, str(CORE / "publish_github.py"), str(brain), "git@github.com:me/my-brain.git"],
                                check=True, capture_output=True, text=True)
            self.assertIn("git push", r.stdout)
            self.assertIn("git commit", r.stdout)
            self.assertFalse((brain / ".git").exists())

    def test_dry_run_explains_every_command_in_one_plain_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            said = []
            publish_github.main([str(brain), "https://github.com/me/my-brain.git"], out=said.append)
            lines = "\n".join(said).splitlines()
            commands = [i for i, line in enumerate(lines) if line.startswith("git ")]
            self.assertEqual(len(commands), 5)  # init, stage, commit, remote, push
            for i in commands:
                explained = lines[i - 1]
                self.assertTrue(explained.startswith("# ") and len(explained) > 20, lines[i])
                self.assertIn(explained[2:], publish_github.EXPLAIN.values())
            self.assertTrue(any("Private" in line for line in lines))
            self.assertFalse((brain / ".git").exists())

    def test_apply_pushes_brain_to_remote_and_is_safe_to_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            remote = bare_remote(tmp)
            publish_github.main([str(brain), str(remote), "--apply"], out=QUIET)
            self.assertTrue((brain / ".git").is_dir())
            self.assertIn("Update my brain", remote_log(remote))

            # Re-run with no changes: nothing to commit, remote already set, must not raise.
            publish_github.main([str(brain), str(remote), "--apply"], out=QUIET)

            # Re-run after a real change: a second commit reaches the remote.
            (brain / "memory" / "decisions.jsonl").write_text('{"decision": "Ship BrainOS", "source": "me", "confidence": "high"}\n')
            publish_github.main([str(brain), str(remote), "--apply"], out=QUIET)
            self.assertEqual(len(remote_log(remote).splitlines()), 2)

    def test_publishes_the_branch_the_brain_repo_is_already_on(self):
        """A buyer may have made the folder a repo themselves, on master. Pushing a hardcoded
        main would fail with git's own refspec error."""
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            subprocess.run(["git", "-C", str(brain), "init", "-q", "-b", "master"], check=True)
            remote = bare_remote(tmp)
            publish_github.main([str(brain), str(remote), "--apply"], out=QUIET)
            branches = subprocess.run(["git", "--git-dir", str(remote), "branch", "--format=%(refname:short)"],
                                       capture_output=True, text=True, check=True)
            self.assertEqual(branches.stdout.split(), ["master"])
            pushed = subprocess.run(["git", "--git-dir", str(remote), "log", "--oneline", "master"],
                                     capture_output=True, text=True, check=True)
            self.assertIn("Update my brain", pushed.stdout)

    def test_refuses_a_flag_where_the_repo_url_belongs(self):
        """`publish_github.py <brain> --apply` must not commit the brain and then try to add a
        remote called --apply."""
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            with self.assertRaises(SystemExit):
                publish_github.main([str(brain), "--apply"])
            self.assertFalse((brain / ".git").exists())

    def test_a_refused_push_is_explained_in_plain_words(self):
        """The usual first-time failure: the person ticked 'Add a README' when making the repo, so
        GitHub refuses the push. They get what to do, not just git's own message."""
        with tempfile.TemporaryDirectory() as tmp:
            remote = bare_remote(tmp)
            other = Path(tmp) / "other"
            subprocess.run(["git", "init", "-q", "-b", "main", str(other)], check=True)
            (other / "README.md").write_text("# my-brain\n")
            subprocess.run(["git", "-C", str(other), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(other), "-c", "user.name=T", "-c", "user.email=t@localhost",
                            "commit", "-q", "-m", "Initial commit"], check=True)
            subprocess.run(["git", "-C", str(other), "push", "-q", str(remote), "main"], check=True)

            brain = create_brain(Path(tmp) / "b")
            with self.assertRaises(SystemExit) as stopped:
                publish_github.main([str(brain), str(remote), "--apply"], out=QUIET)
            self.assertIn("push failed", str(stopped.exception))
            self.assertIn("already has files in it", str(stopped.exception))
            self.assertNotIn("Update my brain", remote_log(remote))

    def test_export_files_are_never_backed_up(self):
        """Raw exports hold other people's messages and details. They stay on the computer: only the
        exports folder's README reaches GitHub. Also true for a brain made before .gitignore shipped."""
        for older_brain in (False, True):
            with self.subTest(older_brain=older_brain), tempfile.TemporaryDirectory() as tmp:
                brain = create_brain(Path(tmp) / "b")
                if older_brain:
                    (brain / ".gitignore").unlink()
                (brain / "exports" / "WhatsApp Chat with Sam.txt").write_text("[01/10/2026, 09:00:00] Sam: hi\n")
                (brain / "exports" / "unzipped").mkdir()
                (brain / "exports" / "unzipped" / "Connections.csv").write_text("First Name,Last Name\n")
                said = []
                publish_github.main([str(brain), "https://github.com/me/my-brain.git"], out=said.append)
                self.assertTrue(any("exports folder" in line and "left out" in line for line in said))
                remote = bare_remote(tmp)
                publish_github.main([str(brain), str(remote), "--apply"], out=QUIET)
                files = subprocess.run(["git", "--git-dir", str(remote), "ls-tree", "-r", "--name-only", "main"],
                                       capture_output=True, text=True, check=True).stdout.split("\n")
                self.assertIn("exports/README.md", files)
                self.assertIn("brain.yaml", files)
                self.assertEqual([f for f in files if f.startswith("exports/") and f != "exports/README.md"], [])
                self.assertTrue((brain / "exports" / "WhatsApp Chat with Sam.txt").is_file())

    def test_refuses_a_folder_that_is_not_a_brain(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                publish_github.main([tmp, "git@github.com:me/my-brain.git"])


if __name__ == "__main__":
    unittest.main()
