"""The no-network guard: importers must never open a socket. Runs each importer's real command line
with sockets blocked, and also refuses any network-capable import in their source."""
import ast
import runpy
import socket
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


if __name__ == "__main__":
    unittest.main()
