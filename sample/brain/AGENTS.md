# How this brain works (level 2)

Read `CLAUDE.md` first. This file says which domain or skill answers which request, where every file is, and the conventions for adding to it. Read a domain's `{DOMAIN}.md` only when the task touches it.

## Routing table

| When the person asks… | Do this |
|---|---|
| Anything about one domain | Read that folder's `{DOMAIN}.md` first, then work |
| Get to know me, set up my context, mine my context, "who am I to you?" | Follow `skills/mine-my-context/SKILL.md` |
| What is on my plate this week? | Follow `skills/whats-on-my-plate/SKILL.md` |
| Who should I reply to first? | Follow `skills/who-to-reply-to-first/SKILL.md` |
| Who do I know at an organisation? | Follow `skills/who-do-i-know-at/SKILL.md` |
| Draft a message in my voice | Follow `skills/draft-in-my-voice/SKILL.md` |
| What have I been putting off? | Follow `skills/what-am-i-putting-off/SKILL.md` |
| Prep me for my next meeting, get me ready for a meeting or call | Follow `skills/prep-my-next-meeting/SKILL.md` |
| Who have I gone quiet with? Who should I reconnect with? | Follow `skills/who-have-i-gone-quiet-with/SKILL.md` |
| Import an export, add my LinkedIn, WhatsApp, calendar, contacts or X | See "Importing" below |
| Note a decision, or something that happened | Add one line to `memory/decisions.jsonl` or `memory/events.jsonl` (see `memory/MEMORY.md`) |
| Run something every week, a scheduled job | Read `automations/AUTOMATIONS.md` |
| Which AI tool or connector, how to point it at this folder | Read `tools/TOOLS.md` |
| You used a connector (calendar, Gmail, Drive…) that `tools/TOOLS.md` does not list | Record it: the first time you use a connector (for example Google Calendar, Gmail or Google Drive), add a line for it to `tools/TOOLS.md` without asking, then tell the person once, in one line, that you have listed it |
| What is due? | `python3 scripts/jobs.py list .` (see `scripts/SCRIPTS.md`) |
| Make a new skill | Read `skills/SKILLS.md` |
| Someone I know, a contact, when we last spoke, an introduction | Read `network/NETWORK.md` first |
| My work, a project or venture, its status or next step | Read `work/WORK.md` first |

## File index

```
CLAUDE.md          level 1: who this is for, how to start, the rules
AGENTS.md          level 2: this file
DOMAINS.md         the domains this brain has
README.md          what the folder is, for the person
brain.yaml         the files a brain must have (checked by the kit's tests)
exports/           raw export files; read only to import them; never backed up
automations/       AUTOMATIONS.md: scheduled jobs
memory/            MEMORY.md, decisions.jsonl, events.jsonl, calendar/, conversations/, profile/
scripts/           SCRIPTS.md, jobs.py
skills/            SKILLS.md, one folder per skill with its SKILL.md
tools/             TOOLS.md, ai-tools/ (one card per AI tool)
network/           NETWORK.md, people.jsonl, interactions.jsonl
work/              WORK.md, projects.yaml
```

## Conventions

- `.jsonl`: one JSON object per line. Every line has `source` (where it came from: an importer, a file, or "you said so on <date>") and `confidence` (high, medium or low). Add new lines at the end; do not rewrite lines someone else wrote. To retire a line, add `"status": "archived"` rather than deleting it.
- Importers own their own lines. Re-running an importer replaces only the lines and files it wrote before; lines added by hand or by a skill are kept.
- `.yaml`: lists written by the importers. `.md`: instructions and readable text.
- Dates are written YYYY-MM-DD.
- Each person appears once in `network/people.jsonl`, merged across every import, with a stable `id` (for example `person_priya_demo`). Refer to people by that id elsewhere.
- Name the file each point of an answer came from.

## Importing

Importers live in the `importers` folder of the BrainOS download. Each takes an export file and this brain folder. Run them with Python 3 (nothing to install). Look for the export files in this brain's `exports/` folder first: `python3 check_setup.py <this-brain-folder>` lists them, with the exact line to run for each.

If you cannot see the export files, send the person one short message with two choices, and no others: drag the files into this brain's `exports` folder (then you need only this folder); or leave them in Downloads, and they click "Allow once" when you ask to use Downloads (it lasts this chat only; heads-up: you can then read and change everything in Downloads for this chat, and the files you read are processed by your provider).

- LinkedIn: `python3 importers/linkedin.py <linkedin-archive.zip> <this-brain-folder>`
- WhatsApp: `python3 importers/whatsapp.py <chat-export.txt or .zip or folder> <this-brain-folder> --me "<their name>"`. Ask once, before the first WhatsApp import, for their own name as it shows in their WhatsApp chats (often just a first name). The brain remembers it in `brain.yaml`, so they are never asked again and never listed as a contact. If the importer stops and lists the names in the chats, ask which one is theirs, then run it again with `--me`.
- Calendar: `python3 importers/calendar_ics.py <calendar.ics or .zip> <this-brain-folder>` (add `--me <their email>` once for each of the person's own addresses)
- Apple Contacts (Mac): `python3 importers/apple_contacts.py <contacts.vcf> <this-brain-folder>`
- X / Twitter archive: `python3 importers/x_export.py <archive.zip or folder> <this-brain-folder>`

Where they write: people (from LinkedIn, WhatsApp, calendar and contacts) to `network/people.jsonl`; messages and meetings to `network/interactions.jsonl`; meetings also to `memory/calendar/events.yaml`; readable chats and your own posts to `memory/conversations/`; your LinkedIn and X profiles to `memory/profile/`.

Each prints what it found and what it skipped. A missing or odd file is reported and skipped, never fatal. Tell the person the counts in plain English. After the first imports, offer the `mine-my-context` skill.
