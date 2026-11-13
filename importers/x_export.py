#!/usr/bin/env python3
"""Import an X (Twitter) data archive: python3 importers/x_export.py <archive.zip or folder> <brain>

On X: Settings and privacy, Your account, Download an archive of your data. X emails a link when it
is ready (it can take a day). Drop the .zip here, or the folder you unzipped it into.

What is read: your own posts — your writing, which is what the "draft in my voice" job needs — and
your profile. Large accounts get their posts split across data/tweets.js, data/tweets-part1.js and
so on; every part is read.

What is NOT read, and why: reposts of other people's posts (their words, not yours), and the people
you follow, your followers and your direct messages. X puts only numeric account ids in those files
with no name or handle beside them, so there is nothing a person could recognise to put in a brain.

No network: the archive is read on this machine and written into the brain folder only."""
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import require_brain, write_text, write_yaml  # noqa: E402

# Every data file in the archive is JavaScript wrapping one JSON list: window.YTD.tweets.part0 = [...]
ASSIGNMENT = re.compile(r"^\s*window\.YTD\.[A-Za-z0-9_]+\.part\d+\s*=\s*", re.DOTALL)
POSTS = re.compile(r"^tweets?(-part\d+)?\.js$", re.IGNORECASE)
ACCOUNT = re.compile(r"^account\.js$", re.IGNORECASE)
PROFILE = re.compile(r"^profile\.js$", re.IGNORECASE)
ROLES = (("posts", POSTS), ("account", ACCOUNT), ("profile", PROFILE))

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
# "Fri Mar 15 09:41:22 +0000 2024", the format X writes in tweets.js.
X_DATE = re.compile(r"^\w{3}\s+(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):\d{2}\s+[+-]\d{4}\s+(\d{4})$")
# "2015-03-02T10:00:00.000Z", the format it writes in account.js.
ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})")


def when(value):
    """('YYYY-MM-DD', 'HH:MM'), or (None, None) when the date cannot be read."""
    value = str(value or "").strip()
    m = X_DATE.match(value)
    if m and m.group(1).title() in MONTHS:
        return f"{m.group(5)}-{MONTHS[m.group(1).title()]:02d}-{int(m.group(2)):02d}", f"{m.group(3)}:{m.group(4)}"
    m = ISO_DATE.match(value)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", f"{m.group(4)}:{m.group(5)}"
    return None, None


def _unwrap(row):
    """Each record is wrapped in a one-key object: {"tweet": {...}} is one post."""
    if isinstance(row, dict) and len(row) == 1:
        inner = next(iter(row.values()))
        if isinstance(inner, dict):
            return inner
    return row if isinstance(row, dict) else {}


def parse_js(text):
    """The records inside one data/*.js file. Raises ValueError if it is not one of X's."""
    m = ASSIGNMENT.match(text.lstrip("﻿"))
    if not m:
        raise ValueError("not a file from an X archive (no window.YTD line)")
    try:
        data = json.loads(text[m.end():])
    except json.JSONDecodeError as e:
        raise ValueError(f"the file is damaged ({e.msg})") from None
    if not isinstance(data, list):
        raise ValueError("the file does not hold a list of records")
    return [_unwrap(row) for row in data]


def _count(value):
    return int(value) if str(value).isdigit() else 0


def _read_members(export):
    """{role: [(filename, text), ...]} for a .zip archive or an unzipped folder."""
    export = Path(export)
    found = []
    if export.is_dir():
        for p in sorted(export.rglob("*.js")):
            found.append((p.name, p.read_bytes()))
    else:
        with zipfile.ZipFile(export) as zf:
            for info in sorted(zf.infolist(), key=lambda i: i.filename):
                if not info.is_dir() and info.filename.lower().endswith(".js"):
                    found.append((info.filename.replace("\\", "/").split("/")[-1], zf.read(info)))
    out = {role: [] for role, _ in ROLES}
    for name, raw in found:
        for role, pattern in ROLES:
            if pattern.match(name):
                out[role].append((name, raw.decode("utf-8-sig", errors="replace")))
                break
    return out


def _posts(members, handle, skipped):
    posts, reposts = [], 0
    for filename, text in members["posts"]:
        try:
            records = parse_js(text)
        except ValueError as e:
            skipped.append({"file": filename, "reason": str(e)})
            continue
        for rec in records:
            text_ = rec.get("full_text") or rec.get("text") or ""
            if text_.startswith("RT @"):  # someone else's words
                reposts += 1
                continue
            date, time = when(rec.get("created_at"))
            ident = str(rec.get("id_str") or rec.get("id") or "")
            posts.append({
                "date": date, "time": time, "text": text_,
                "replying_to": rec.get("in_reply_to_screen_name") or "",
                "likes": _count(rec.get("favorite_count")), "reposts": _count(rec.get("retweet_count")),
                "link": f"https://x.com/{handle}/status/{ident}" if handle and ident else "",
                "source": "x",
            })
    posts.sort(key=lambda p: (p["date"] or "", p["time"] or "", p["text"]))
    return posts, reposts


def _profile(members, skipped):
    """(account, profile) dicts; either may be empty when the archive does not carry it."""
    out = {}
    for role in ("account", "profile"):
        out[role] = {}
        for filename, text in members[role]:
            try:
                records = parse_js(text)
            except ValueError as e:
                skipped.append({"file": filename, "reason": str(e)})
                continue
            if records:
                out[role] = records[0]
    return out["account"], out["profile"]


def run(export, brain):
    brain = require_brain(brain)
    skipped = []
    members = _read_members(export)
    if not any(members[role] for role, _ in ROLES):
        raise ValueError("That does not look like an X archive: it has no data/tweets.js in it.")
    account, profile = _profile(members, skipped)
    handle = str(account.get("username") or "").strip().lstrip("@")
    posts, reposts = _posts(members, handle, skipped)

    write_yaml(brain, "memory/conversations/x-posts.yaml", posts,
               "Your own posts on X, oldest first. Reposts of other people are not here: their words "
               "are theirs. Written by importers/x_export.py; re-running replaces this file.")

    display = str(account.get("accountDisplayName") or "").strip()
    description = profile.get("description") if isinstance(profile.get("description"), dict) else {}
    joined, _ = when(account.get("createdAt"))
    title = " ".join(p for p in [display, f"(@{handle})" if handle else ""] if p) or "My X profile"
    lines = [f"# {title}", ""]
    for label, value in (("Bio", description.get("bio")), ("Location", description.get("location")),
                         ("Website", description.get("website")), ("Joined", joined)):
        if str(value or "").strip():
            lines.append(f"- {label}: {str(value).strip()}")
    lines += [f"- Posts in this archive: {len(posts)}", "",
              "Written by importers/x_export.py from your own X archive; re-running replaces this file."]
    write_text(brain, "memory/profile/x-profile.md", "\n".join(lines) + "\n")

    return {"posts": len(posts), "reposts": reposts, "handle": handle,
            "undated": sum(1 for p in posts if not p["date"]), "skipped": skipped}


def main(argv):
    if len(argv) != 3:
        raise SystemExit("Usage: python3 importers/x_export.py <archive.zip or folder> <brain-folder>")
    try:
        r = run(argv[1], argv[2])
    except (OSError, zipfile.BadZipFile) as e:
        raise SystemExit(f"Could not read the X archive: {e}")
    except ValueError as e:
        raise SystemExit(str(e))
    who = f" for @{r['handle']}" if r["handle"] else ""
    print(f"X: {r['posts']} of your own posts{who}, {r['undated']} without a readable date. "
          f"{r['reposts']} reposts of other people skipped.")
    for s in r["skipped"]:
        print(f"Skipped {s['file']}: {s['reason']}.")


if __name__ == "__main__":
    main(sys.argv)
