"""start.sh (Mac and Linux: curl ... | sh) and start.ps1 (Windows: irm ... | iex): the terminal line.

Each run here is sealed off: a made-up home folder, a kit zip built from this kit on disk (never
downloaded), stand-ins for curl, wget and the folder opener that only write down that they were called,
and a dead web proxy, so nothing can reach the internet. start.ps1 runs too when PowerShell is here."""
import os
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
START_SH = CORE / "start.sh"
START_PS1 = CORE / "start.ps1"
LINE = ("Set up my brain with BrainOS from github.com/adrianshedden/brainos-core (read its SETUP.md first "
        "and follow it). Ask me before you change anything, work only in my brain folder, and never share, "
        "upload or post my files.")
AI_APPS = ("claude", "codex", "opencode")
SYSTEM_PATH = "/usr/bin:/bin"
DEAD_PROXY = "http://127.0.0.1:9"
# The only web addresses either script may name: the kit on GitHub, and python.org in the install steps.
ALLOWED_URLS = {"https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.sh",
                "https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.ps1",
                "https://github.com/adrianshedden/brainos-core/archive/refs/heads"}
# Plain words both scripts print for the same step.
SHARED_WORDS = ("BrainOS: getting your brain folder ready. This takes about a minute.",
                "Downloading BrainOS...",
                "Your Documents folder is copied online by",
                "instead, which stays on this computer.",
                "and it is not a brain. To keep those files safe, nothing was changed.",
                "Python is not on this computer yet. BrainOS uses it to read your files. To get it, free:",
                "1. Go to python.org/downloads and click the yellow Download button.",
                "in your brain folder with the set-up line. Answer its questions there.",
                "Next, open your AI app (for example the Claude app), choose the folder",
                "Could not download BrainOS. Check this computer is online")


def kit_zip(dest, top="brainos-core-main", leave_out=()):
    """A zip shaped like GitHub's download of this kit: one top folder holding the kit's files."""
    with zipfile.ZipFile(dest, "w") as zf:
        for p in sorted(CORE.rglob("*")):
            rel = p.relative_to(CORE)
            if p.is_file() and not {".git", "__pycache__"} & set(rel.parts) and p.suffix != ".pyc" \
                    and rel.as_posix() not in leave_out:
                zf.write(p, f"{top}/{rel.as_posix()}")
    return dest


def stand_in(bin_dir, name, body='echo "$0 $*" >> "$CALLS"'):
    path = Path(bin_dir) / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def files_outside_kit(brain):
    return {p.relative_to(brain).as_posix(): p.read_bytes() for p in sorted(Path(brain).rglob("*"))
            if p.is_file() and p.relative_to(brain).parts[0] != "kit"}


class Sandbox(unittest.TestCase):
    """A made-up home folder with Documents, a bin folder of stand-ins, and a local kit zip."""

    @classmethod
    def setUpClass(cls):
        cls.zips = tempfile.TemporaryDirectory()
        cls.zip = kit_zip(Path(cls.zips.name) / "kit.zip")

    @classmethod
    def tearDownClass(cls):
        cls.zips.cleanup()

    def setUp(self):
        if os.name == "nt":
            # The stand-ins are shell scripts on a Unix-style PATH. On Windows the real line is run for real
            # instead, by the kit's GitHub check (.github/workflows/kit.yml).
            self.skipTest("the sandbox needs a Mac or Linux; on Windows, kit.yml runs start.ps1 for real")
        for app in AI_APPS:
            if shutil.which(app, path=SYSTEM_PATH):
                self.skipTest(f"{app} is installed in {SYSTEM_PATH}, so 'no AI app' cannot be tested here")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        (self.home / "Documents").mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "calls.txt"
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        for name in ("curl", "wget", "open", "xdg-open"):
            stand_in(self.bin, name, f'echo "{name} $*" >> "$CALLS"; ' + ("exit 1" if name in ("curl", "wget") else ""))
        os.symlink(sys.executable, self.bin / "python3")

    def env(self, **extra):
        env = {"HOME": str(self.home), "PATH": f"{self.bin}:{SYSTEM_PATH}", "BRAINOS_ZIP": str(self.zip),
               "CALLS": str(self.calls), "TMPDIR": str(self.scratch), "LANG": "C",
               "http_proxy": DEAD_PROXY, "https_proxy": DEAD_PROXY, "HTTP_PROXY": DEAD_PROXY,
               "HTTPS_PROXY": DEAD_PROXY, "ALL_PROXY": DEAD_PROXY}
        env.update({k: str(v) for k, v in extra.items()})
        return env

    def calls_made(self):
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []

    def assert_no_download_tool_used(self):
        self.assertFalse([c for c in self.calls_made() if c.startswith(("curl", "wget"))], self.calls_made())


class StartSh(Sandbox):
    def run_sh(self, shell="/bin/sh", **extra):
        """Runs start.sh the way the terminal line does: the script arrives on the shell's input."""
        return subprocess.run([shell], input=START_SH.read_bytes(), env=self.env(**extra), cwd=self.root,
                              capture_output=True, timeout=120)

    def assert_kit_in(self, brain):
        for rel in ("SETUP.md", "create_brain.py", "level1.py", "template/LEVEL1.md", "start.sh"):
            self.assertTrue((brain / "kit" / rel).is_file(), rel)
        self.assertEqual([p.name for p in brain.iterdir() if p.name.startswith(".kit-")], [])
        self.assertEqual(list(self.scratch.iterdir()), [], "the temporary download folder is deleted")

    def test_makes_documents_brain_places_the_kit_and_prints_the_line_when_no_ai_app_is_installed(self):
        shells = ["/bin/sh"] + (["/bin/dash"] if Path("/bin/dash").exists() else [])
        for shell in shells:
            with self.subTest(shell=shell):
                r = self.run_sh(shell)
                out = r.stdout.decode()
                self.assertEqual(r.returncode, 0, r.stderr.decode())
                brain = self.home / "Documents" / "brain"
                self.assert_kit_in(brain)
                self.assertIn(LINE, out.splitlines(), "the AI-app line, word for word, on a line of its own")
                self.assertIn(f"Your brain folder is {brain}", out)
                self.assertIn("Python is ready.", out)
                self.assertNotIn("copied online", out)
                if sys.platform == "darwin":
                    self.assertIn(f"open {brain}", self.calls_made())
                self.assert_no_download_tool_used()

    def test_running_it_again_refreshes_the_kit_and_never_touches_the_persons_files(self):
        self.assertEqual(self.run_sh().returncode, 0)
        brain = self.home / "Documents" / "brain"
        subprocess.run([sys.executable, str(brain / "kit" / "create_brain.py"), str(brain)], check=True,
                       capture_output=True)
        (brain / "kit" / "left-from-an-old-kit.txt").write_text("old", encoding="utf-8")
        (brain / "memory" / "my-notes.md").write_text("Mine.\n", encoding="utf-8")
        (brain / "setup.yaml").write_text("step: 3\n", encoding="utf-8")
        before = files_outside_kit(brain)
        r = self.run_sh()
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertFalse((brain / "kit" / "left-from-an-old-kit.txt").exists())
        self.assert_kit_in(brain)
        self.assertEqual(files_outside_kit(brain), before)

    def test_icloud_documents_means_the_brain_goes_in_the_home_folder(self):
        (self.home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Documents").mkdir(parents=True)
        r = self.run_sh()
        out = r.stdout.decode()
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn(f"Your Documents folder is copied online by iCloud, so your brain goes in {self.home}/brain "
                      "instead, which stays on this computer.", out.splitlines())
        self.assert_kit_in(self.home / "brain")
        self.assertFalse((self.home / "Documents" / "brain").exists())

    def test_onedrive_documents_means_the_brain_goes_in_the_home_folder(self):
        (self.home / "Documents").rmdir()
        (self.home / "OneDrive" / "Documents").mkdir(parents=True)
        (self.home / "Documents").symlink_to(self.home / "OneDrive" / "Documents")
        r = self.run_sh()
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("copied online by OneDrive", r.stdout.decode())
        self.assert_kit_in(self.home / "brain")

    def test_a_brain_made_earlier_is_found_again(self):
        (self.home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Documents").mkdir(parents=True)
        earlier = self.home / "Documents" / "brain"
        earlier.mkdir()
        (earlier / "brain.yaml").write_text("domains: []\n", encoding="utf-8")
        r = self.run_sh()
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assert_kit_in(earlier)
        self.assertFalse((self.home / "brain").exists())

    def test_brainos_dir_chooses_the_folder(self):
        chosen = self.root / "elsewhere" / "my brain"
        r = self.run_sh(BRAINOS_DIR=chosen)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assert_kit_in(chosen)
        self.assertIn(f"choose the folder {chosen}, and paste this line:", r.stdout.decode())

    def test_refuses_a_folder_holding_someone_elses_files(self):
        theirs = self.home / "Documents" / "brain"
        theirs.mkdir()
        (theirs / "thesis.docx").write_text("mine", encoding="utf-8")
        r = self.run_sh()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("To keep those files safe, nothing was changed.", r.stderr.decode())
        self.assertEqual([p.name for p in theirs.iterdir()], ["thesis.docx"])

    def test_a_download_that_is_not_the_kit_changes_nothing(self):
        self.assertEqual(self.run_sh().returncode, 0)
        brain = self.home / "Documents" / "brain"
        (brain / "kit" / "marker.txt").write_text("the kit from before", encoding="utf-8")
        broken = kit_zip(self.root / "broken.zip", leave_out=("SETUP.md",))
        r = self.run_sh(BRAINOS_ZIP=broken)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not look like BrainOS", r.stderr.decode())
        self.assertEqual((brain / "kit" / "marker.txt").read_text(encoding="utf-8"), "the kit from before")

    def test_no_python_prints_plain_steps_installs_nothing_and_still_gives_the_line(self):
        needed = ("mktemp", "rm", "cp", "mkdir", "mv", "unzip", "uname")
        if not all(shutil.which(t, path=SYSTEM_PATH) for t in needed):
            self.skipTest("this computer lacks one of " + ", ".join(needed))
        bare = self.root / "bare-bin"
        bare.mkdir()
        for tool in needed:
            os.symlink(shutil.which(tool, path=SYSTEM_PATH), bare / tool)
        for name in ("open", "xdg-open"):
            shutil.copy(self.bin / name, bare / name)
        r = self.run_sh(PATH=bare)
        out = r.stdout.decode()
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("Python is not on this computer yet.", out)
        self.assertIn("python.org/downloads", out)
        self.assertIn(LINE, out.splitlines())
        self.assert_kit_in(self.home / "Documents" / "brain")

    def test_starts_the_ai_app_in_the_brain_folder_with_the_line(self):
        record = 'pwd -P > "$CALLS.cwd"; for a in "$@"; do printf "%s\\n" "$a"; done > "$CALLS.args"'
        brain = self.home / "Documents" / "brain"
        for app, expected in (("claude", [LINE]), ("codex", [LINE]), ("opencode", ["--prompt", LINE])):
            with self.subTest(app=app):
                for other in AI_APPS:
                    (self.bin / other).unlink(missing_ok=True)
                stand_in(self.bin, app, record)
                r = self.run_sh(BRAINOS_TTY=os.devnull)
                self.assertEqual(r.returncode, 0, r.stderr.decode())
                self.assertIn("in your brain folder with the set-up line", r.stdout.decode())
                self.assertEqual(Path(f"{self.calls}.args").read_text(encoding="utf-8").splitlines(), expected)
                self.assertEqual(Path(f"{self.calls}.cwd").read_text(encoding="utf-8").strip(), str(brain.resolve()))
                self.assertEqual(list(self.scratch.iterdir()), [])

    def test_an_ai_app_with_no_keyboard_to_read_gets_the_line_printed_instead(self):
        stand_in(self.bin, "claude", 'echo "claude $*" >> "$CALLS"')
        r = self.run_sh(BRAINOS_TTY=self.root / "no-such-keyboard")
        out = r.stdout.decode()
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("Claude Code is on this computer.", out)
        self.assertIn(LINE, out.splitlines())
        self.assertFalse([c for c in self.calls_made() if c.startswith("claude")])


class StaticChecks(unittest.TestCase):
    def test_both_scripts_carry_the_line_word_for_word(self):
        for script in (START_SH, START_PS1):
            self.assertIn(LINE, script.read_text(encoding="utf-8"), script.name)

    def test_both_scripts_take_the_same_steps_in_the_same_plain_words(self):
        sh, ps1 = START_SH.read_text(encoding="utf-8"), START_PS1.read_text(encoding="utf-8")
        for words in SHARED_WORDS:
            self.assertIn(words, sh, f"start.sh: {words}")
            self.assertIn(words, ps1, f"start.ps1: {words}")
        for setting in ("BRAINOS_REF", "BRAINOS_ZIP", "BRAINOS_DIR"):
            self.assertIn(setting, sh)
            self.assertIn(setting, ps1)
        for app in AI_APPS:
            self.assertIn(app, sh)
            self.assertIn(app, ps1)
        self.assertIn("opencode --prompt", sh)
        self.assertIn("opencode --prompt", ps1)
        self.assertIn("iCloud", sh)
        self.assertIn("OneDrive", sh)
        self.assertIn("OneDrive", ps1)
        # Windows: py first (python.org's own launcher), then python; strict mode; unzip with no extra tools.
        self.assertIn("@('py', 'python')", ps1)
        self.assertIn("Set-StrictMode -Version Latest", ps1)
        self.assertIn("$ErrorActionPreference = 'Stop'", ps1)
        self.assertIn("Expand-Archive", ps1)
        self.assertIn("set -eu", sh)

    def test_no_admin_no_tracking_no_other_websites(self):
        for script in (START_SH, START_PS1):
            text = script.read_text(encoding="utf-8")
            code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
            for banned in ("sudo", "RunAs", "Set-ExecutionPolicy", "analytics", "telemetry", "doas "):
                self.assertNotIn(banned, code, f"{script.name}: {banned}")
            urls = set(re.findall(r"https?://[^\s'\"`)]+", text))
            self.assertTrue(urls <= ALLOWED_URLS, f"{script.name}: {urls - ALLOWED_URLS}")

    def test_both_scripts_are_plain_ascii(self):
        """Windows PowerShell 5.1 may read a downloaded script in the wrong character set: plain letters only."""
        for script in (START_SH, START_PS1):
            self.assertTrue(script.read_bytes().isascii(), script.name)

    def test_start_ps1_never_closes_the_persons_window(self):
        """Run through irm | iex, an `exit` would close the PowerShell window itself."""
        code = [line for line in START_PS1.read_text(encoding="utf-8").splitlines()
                if not line.lstrip().startswith("#")]
        self.assertFalse([line for line in code if re.search(r"\bexit\b", line, re.I)])

    def test_start_sh_is_posix_and_passes_shellcheck(self):
        if Path("/bin/dash").exists():
            r = subprocess.run(["/bin/dash", "-n", str(START_SH)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        if not shutil.which("shellcheck"):
            self.skipTest("shellcheck is not installed")
        r = subprocess.run(["shellcheck", "-s", "sh", str(START_SH)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell (pwsh) is not installed")
class StartPs1(Sandbox):
    def run_ps1(self, **extra):
        """Runs start.ps1 the way the Windows line does (the script text piped into Invoke-Expression), then
        prints a marker to prove the window would still be open."""
        script = self.root / "start.ps1"
        shutil.copy(START_PS1, script)
        command = f"Get-Content -Raw -LiteralPath '{script}' | Invoke-Expression; 'window still open'"
        env = self.env(**{"BRAINOS_DOCUMENTS": self.home / "Documents", **extra})
        return subprocess.run([shutil.which("pwsh"), "-NoProfile", "-NonInteractive", "-Command", command],
                              env=env, cwd=self.root, capture_output=True, text=True, timeout=180)

    def setUp(self):
        super().setUp()
        stand_in(self.bin, "py", f'exec "{sys.executable}" "$@"')

    def test_makes_documents_brain_places_the_kit_and_prints_the_line(self):
        r = self.run_ps1()
        self.assertEqual(r.returncode, 0, r.stderr)
        brain = self.home / "Documents" / "brain"
        self.assertTrue((brain / "kit" / "SETUP.md").is_file())
        self.assertTrue((brain / "kit" / "create_brain.py").is_file())
        self.assertEqual([p.name for p in brain.iterdir()], ["kit"])
        self.assertIn(LINE, r.stdout.splitlines())
        self.assertIn("Python is ready.", r.stdout)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "window still open")
        self.assert_no_download_tool_used()

    def test_running_it_again_refreshes_the_kit_and_keeps_the_persons_files(self):
        self.assertEqual(self.run_ps1().returncode, 0)
        brain = self.home / "Documents" / "brain"
        (brain / "kit" / "left-from-an-old-kit.txt").write_text("old", encoding="utf-8")
        (brain / "brain.yaml").write_text("domains: []\n", encoding="utf-8")
        (brain / "notes.md").write_text("Mine.\n", encoding="utf-8")
        before = files_outside_kit(brain)
        r = self.run_ps1()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((brain / "kit" / "left-from-an-old-kit.txt").exists())
        self.assertTrue((brain / "kit" / "SETUP.md").is_file())
        self.assertEqual(files_outside_kit(brain), before)

    def test_onedrive_documents_means_the_brain_goes_in_the_home_folder(self):
        docs = self.home / "OneDrive" / "Documents"
        docs.mkdir(parents=True)
        r = self.run_ps1(BRAINOS_DOCUMENTS=docs)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("copied online by OneDrive", r.stdout)
        self.assertTrue((self.home / "brain" / "kit" / "SETUP.md").is_file())
        self.assertFalse((docs / "brain").exists())

    def test_refuses_a_folder_holding_someone_elses_files(self):
        theirs = self.home / "Documents" / "brain"
        theirs.mkdir()
        (theirs / "thesis.docx").write_text("mine", encoding="utf-8")
        r = self.run_ps1()
        self.assertIn("To keep those files safe, nothing was changed.", r.stdout)
        self.assertEqual([p.name for p in theirs.iterdir()], ["thesis.docx"])
        self.assertEqual(r.stdout.strip().splitlines()[-1], "window still open")

    def test_no_python_prints_plain_steps_and_still_gives_the_line(self):
        (self.bin / "py").unlink()
        os.unlink(self.bin / "python3")
        if shutil.which("python", path=SYSTEM_PATH) or shutil.which("py", path=SYSTEM_PATH):
            self.skipTest("a python is installed in " + SYSTEM_PATH)
        r = self.run_ps1()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Python is not on this computer yet.", r.stdout)
        self.assertIn('tick "Add python.exe to PATH"', r.stdout)
        self.assertIn(LINE, r.stdout.splitlines())

    def test_starts_the_ai_app_in_the_brain_folder_with_the_line(self):
        stand_in(self.bin, "claude", 'pwd -P > "$CALLS.cwd"; for a in "$@"; do printf "%s\\n" "$a"; done > "$CALLS.args"')
        r = self.run_ps1()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Starting Claude Code in your brain folder", r.stdout)
        self.assertEqual(Path(f"{self.calls}.args").read_text(encoding="utf-8").splitlines(), [LINE])
        self.assertEqual(Path(f"{self.calls}.cwd").read_text(encoding="utf-8").strip(),
                         str((self.home / "Documents" / "brain").resolve()))


if __name__ == "__main__":
    unittest.main()
