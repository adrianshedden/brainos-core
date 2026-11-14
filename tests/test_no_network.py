"""The no-network guard: importers must never open a socket. Runs each importer's real command line
with sockets blocked, and also refuses any network-capable import in their source."""
import ast
import runpy
import socket
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import nonet

CORE = Path(__file__).resolve().parents[1]
FORBIDDEN = {"socket", "urllib", "http", "https", "requests", "ftplib", "smtplib", "ssl", "asyncio",
             "httpx", "aiohttp", "telnetlib", "xmlrpc", "webbrowser"}


class NoNetwork(unittest.TestCase):
    def test_guard_actually_blocks(self):
        real = socket.socket
        try:
            nonet.install()
            with self.assertRaises(nonet.NetworkAttempt):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        finally:
            socket.socket = real

    def test_importer_source_has_no_network_imports(self):
        for path in sorted((CORE / "importers").glob("*.py")) + [CORE / "create_brain.py", CORE / "check_setup.py"]:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                for n in names:
                    self.assertNotIn(n.split(".")[0], FORBIDDEN, f"{path.name} imports {n}")

    def test_importers_run_with_sockets_blocked(self):
        real = (socket.socket, socket.create_connection, socket.getaddrinfo, socket.gethostbyname)
        ex = CORE / "sample" / "exports"
        try:
            nonet.install()
            with tempfile.TemporaryDirectory() as tmp:
                brain = Path(tmp) / "brain"
                old_argv = sys.argv
                zpath = Path(tmp) / "li.zip"
                with zipfile.ZipFile(zpath, "w") as zf:
                    for f in (ex / "linkedin").glob("*.csv"):
                        zf.write(f, f.name)
                runs = [
                    ("create_brain.py", [str(brain)]),
                    ("importers/linkedin.py", [str(zpath), str(brain)]),
                    ("importers/whatsapp.py", [str(ex / "whatsapp"), str(brain), "--me", "Alex Example"]),
                    ("importers/calendar_ics.py", [str(ex / "calendar" / "calendar.ics"), str(brain)]),
                    ("importers/apple_contacts.py", [str(ex / "apple" / "contacts.vcf"), str(brain)]),
                    ("importers/x_export.py", [str(ex / "x"), str(brain)]),
                    ("check_setup.py", [str(brain)]),
                ]
                try:
                    for script, args in runs:
                        sys.argv = [script, *args]
                        runpy.run_path(str(CORE / script), run_name="__main__")
                finally:
                    sys.argv = old_argv
                self.assertTrue((brain / "network/people.jsonl").is_file())
                self.assertTrue((brain / "network/interactions.jsonl").is_file())
                self.assertTrue((brain / "memory/conversations/x-posts.yaml").is_file())
        finally:
            socket.socket, socket.create_connection, socket.getaddrinfo, socket.gethostbyname = real


REAL_REMOTE = "https://github.com/example-owner/example-core.git"


def git(*args, cwd=None):
    return subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],
                          cwd=cwd, check=True, capture_output=True, text=True)


class NoNetworkGit(unittest.TestCase):
    """A git push/fetch to a real remote must raise before any process starts (13 Nov 2026: a test
    force-pushed over remyn-core because only Python sockets were blocked)."""

    def setUp(self):
        self.was_installed = nonet.installed()
        nonet.uninstall()
        self.started = []
        self.real_init = subprocess.Popen.__init__
        started, real_init = self.started, self.real_init

        def recording_init(popen, args, *a, **kw):  # sits beneath the guard: only reached if the guard let it through
            started.append(args)
            return real_init(popen, args, *a, **kw)

        subprocess.Popen.__init__ = recording_init
        nonet.install()

    def tearDown(self):
        nonet.uninstall()
        subprocess.Popen.__init__ = self.real_init
        if self.was_installed:
            nonet.install()

    def test_push_to_real_url_raises_before_any_process_starts(self):
        for caller in (subprocess.run, subprocess.check_call, subprocess.check_output,
                       lambda argv, **kw: subprocess.Popen(argv, **kw)):
            for argv in (["git", "push", "-f", "-q", REAL_REMOTE, "main"],
                         ["git", "-C", "/nonexistent", "push", "origin", "git@github.com:example-owner/example-core.git"],
                         ["git", "fetch", "ssh://git@github.com/example-owner/example-core.git"],
                         ["git", "pull", REAL_REMOTE], ["git", "clone", REAL_REMOTE, "x"], ["git", "ls-remote", REAL_REMOTE]):
                with self.assertRaises(nonet.NetworkAttempt, msg=f"{caller} {argv}"):
                    caller(argv, capture_output=True) if caller is subprocess.run else caller(argv)
        with self.assertRaises(nonet.NetworkAttempt):
            subprocess.run(f"cd /tmp && git push {REAL_REMOTE} main", shell=True)
        self.assertEqual(self.started, [])

    def test_push_by_remote_name_is_caught_when_the_name_points_at_a_real_url(self):
        # the shape publish_bootcamp_core.py uses: `git remote add origin <url>` then `git push origin main`
        with tempfile.TemporaryDirectory() as tmp:
            git("init", "-q", "-b", "main", tmp)
            git("remote", "add", "origin", REAL_REMOTE, cwd=tmp)
            self.started.clear()
            for argv in (["git", "push", "-f", "-q", "origin", "main"], ["git", "push"], ["git", "fetch", "--all"]):
                with self.assertRaises(nonet.NetworkAttempt, msg=str(argv)):
                    subprocess.run(argv, cwd=tmp, capture_output=True, text=True)
            self.assertEqual([a for a in self.started if a[1] in ("push", "fetch")], [])

    def test_push_to_a_local_bare_repo_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare, work = Path(tmp) / "remote.git", Path(tmp) / "work"
            git("init", "-q", "--bare", "-b", "main", str(bare))
            git("init", "-q", "-b", "main", str(work))
            (work / "f.txt").write_text("x")
            git("add", "-A", cwd=work)
            git("commit", "-q", "-m", "c", cwd=work)
            git("remote", "add", "origin", str(bare), cwd=work)
            git("push", "-f", "-q", "origin", "main", cwd=work)
            git("fetch", "-q", str(bare), cwd=work)
            self.assertIn("f.txt", git("--git-dir", str(bare), "ls-tree", "--name-only", "main").stdout)
            self.assertTrue(any(a[1:2] == ["push"] or "push" in a for a in self.started))  # it really ran


if __name__ == "__main__":
    unittest.main()
