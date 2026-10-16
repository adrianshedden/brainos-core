#!/usr/bin/env python3
"""Back a brain folder up to your own GitHub, as a private repo you own. Step by step: GITHUB.md.

  python3 publish_github.py <brain> <repo-address>            show each command and what it does; runs nothing
  python3 publish_github.py <brain> <repo-address> --apply    do it for real

<repo-address> is an empty, private repo you already made under your own GitHub account, for example
https://github.com/your-name/my-brain.git. BrainOS never makes a GitHub account or signs in for you:
it runs ordinary git commands inside your brain folder and sends the brain to the repo you named, and
nowhere else.

Safe to re-run: later runs save only what changed and send it again. If you have no git name set up,
a stand-in one ("BrainOS", not your name) is set inside the brain folder only, so the first save does
not fail on a fresh computer. If the brain folder is already a git repo, its own branch is sent.

The brain's exports/ folder (the raw export files) is never backed up. The brain's .gitignore says so;
a brain made before that file existed gets it added on the first --apply.
"""
import subprocess
import sys
from pathlib import Path

# One plain-English line per command, shown above it in the dry run.
EXPLAIN = {
    "init": "Turn this folder into a git repository, so its history can be saved (first time only).",
    "stage": "Gather every file in the brain for the next save.",
    "commit": "Save a snapshot of the brain on this computer, labelled 'Update my brain'.",
    "remote": "Remember your GitHub repo's address, under the name origin.",
    "push": "Send the snapshot to your GitHub repo. Git may ask you to sign in: see GITHUB.md, step 4.",
}

# Keeps the raw export files out of every save. Its README stays, so the folder's purpose is backed up too.
IGNORE_EXPORTS = ("exports/*", "!exports/README.md")
IGNORE_NOTE = "# Raw export files stay on this computer: they are never part of the GitHub backup."

# What a refused push usually means, in plain words. Matched against git's own message.
PUSH_HINTS = (
    (("rejected", "fetch first", "non-fast-forward"),
     "Your GitHub repo already has files in it, probably a README ticked when it was made. Make a new "
     "repo with nothing ticked and use that address instead."),
    (("authentication failed", "could not read username", "permission denied", "403"),
     "GitHub did not accept the sign-in. Use your GitHub username, and paste a token (not your password) "
     "when asked for a password: see GITHUB.md, step 4."),
    (("repository not found", "does not appear to be a git repository"),
     "There is no repo at that address you can reach. Copy the address again from the repo's page on GitHub."),
)


def require_brain(brain):
    brain = Path(brain)
    if not (brain / "brain.yaml").is_file():
        raise SystemExit(f"{brain} is not a brain folder (no brain.yaml). Create one with create_brain.py first.")
    return brain


def leave_out_exports(brain):
    """Make sure the brain's .gitignore keeps exports/ out of the backup. Adds only the missing lines."""
    path = Path(brain) / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    have = {line.strip() for line in text.splitlines()}
    missing = [line for line in IGNORE_EXPORTS if line not in have]
    if missing:
        lead = "" if not text or text.endswith("\n") else "\n"
        path.write_text(text + lead + "\n".join(([IGNORE_NOTE] if not text else []) + missing) + "\n", encoding="utf-8")


def branch_of(brain, run=subprocess.run):
    """The brain repo's current branch. A folder they already made a repo in may be on master."""
    r = run(["git", "-C", str(brain), "symbolic-ref", "--short", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or "main"


def plan(brain, remote):
    """List of (label, argv) git commands to run inside <brain>, in order."""
    cmds = []
    if (Path(brain) / ".git").is_dir():
        branch = branch_of(brain)
    else:
        branch = "main"
        cmds.append(("init", ["git", "init", "-q", "-b", branch]))
    cmds.append(("stage", ["git", "add", "-A"]))
    cmds.append(("commit", ["git", "commit", "-q", "-m", "Update my brain"]))
    cmds.append(("remote", ["git", "remote", "add", "origin", remote]))
    cmds.append(("push", ["git", "push", "-q", "-u", "origin", branch]))
    return cmds


def push_hint(message):
    low = message.lower()
    for needles, hint in PUSH_HINTS:
        if any(n in low for n in needles):
            return hint
    return ""


def run_all(brain, cmds, run=subprocess.run):
    for label, argv in cmds:
        if label == "commit":
            have_identity = run(["git", "config", "user.name"], cwd=str(brain), capture_output=True, text=True)
            if not have_identity.stdout.strip():
                run(["git", "config", "user.name", "BrainOS"], cwd=str(brain), check=True, capture_output=True, text=True)
                run(["git", "config", "user.email", "brain-os@localhost"], cwd=str(brain), check=True, capture_output=True, text=True)
        r = run(argv, cwd=str(brain), capture_output=True, text=True)
        if r.returncode != 0:
            if label == "commit" and "nothing to commit" in (r.stdout + r.stderr):
                continue
            if label == "remote" and "already exists" in r.stderr:
                r2 = run(["git", "remote", "set-url", "origin", argv[-1]], cwd=str(brain), capture_output=True, text=True)
                if r2.returncode != 0:
                    raise SystemExit(f"remote failed: {r2.stderr.strip()}")
                continue
            said = (r.stderr or r.stdout).strip()
            hint = push_hint(said) if label == "push" else ""
            raise SystemExit(f"{label} failed: {said}" + (f"\n\n{hint}" if hint else ""))


USAGE = "Usage: python3 publish_github.py <brain> <repo-address> [--apply]"


def main(argv, out=print):
    if len(argv) < 2 or argv[1].startswith("-"):
        # Without this, `publish_github.py <brain> --apply` would commit the brain for real and
        # then try to add a remote called --apply.
        raise SystemExit(USAGE + "\nName the repo you made, for example https://github.com/your-name/my-brain.git")
    brain = require_brain(argv[0])
    remote = argv[1]
    cmds = plan(brain, remote)
    if "--apply" not in argv:
        out("Dry run: nothing has been done. Each step below is what --apply would run, with what it does.")
        out(f"Check first: {remote} is your own repo, set to Private, and empty.")
        out("Your exports folder (the raw export files) is left out of the backup.\n")
        for label, a in cmds:
            out(f"# {EXPLAIN[label]}\n{' '.join(a)}")
        out("\nTo do it for real, run the same command again with --apply on the end.")
        return
    leave_out_exports(brain)
    run_all(brain, cmds)
    out(f"Done. Your brain is backed up to {remote}. Open that page on GitHub to see it.")


if __name__ == "__main__":
    main(sys.argv[1:])
