# How this brain works (level 2)

Read level 1 first: it is the block above (the same words as `CLAUDE.md` and `GEMINI.md`). This manual says which domain or skill answers which request, where every file is, and the conventions for adding to it. Read a domain's `{DOMAIN}.md` only when the task touches it.

## Routing table

| When the person asks… | Do this |
|---|---|
| Anything about one domain | Read that folder's `{DOMAIN}.md` first, then work |
| Get to know me, set up my context, mine my context, "who am I to you?" | Follow `skills/mine-my-context/SKILL.md` |
| What is on my plate for the next seven days? | Follow `skills/whats-on-my-plate/SKILL.md` |
| Who should I reply to first? | Follow `skills/who-to-reply-to-first/SKILL.md` |
| Who do I know at an organisation? | Follow `skills/who-do-i-know-at/SKILL.md` |
| Draft a message in my voice | Follow `skills/draft-in-my-voice/SKILL.md` |
| What have I been putting off? | Follow `skills/what-am-i-putting-off/SKILL.md` |
| Prep me for my next meeting, get me ready for a meeting or call | Follow `skills/prep-my-next-meeting/SKILL.md` |
| Who have I gone quiet with? Who should I reconnect with? | Follow `skills/who-have-i-gone-quiet-with/SKILL.md` |
| Morning brief, brief me, what's on today, start my day | Follow `skills/morning-brief/SKILL.md` |
| Weekly review, review my week, plan next week | Follow `skills/weekly-review/SKILL.md` |
| Show it visually, make it a page, show me that as a page | Follow `skills/show-it-visually/SKILL.md` |
| Set up my BrainOS, finish my setup, connect something new: connect my Outlook, connect my Gmail, connect my calendar | Follow `kit/SETUP.md` (the setup guide in BrainOS): "Coming back later", then step 3 for that one source, down the connection ladder |
| Connect my WhatsApp live, connect my WhatsApp using WHATSAPP-LIVE.md | Follow `kit/WHATSAPP-LIVE.md`: risks and a yes first |
| Import an export, add my LinkedIn, WhatsApp, calendar, contacts or X | See "Importing" below |
| Note a decision, or something that happened | Add one line to `memory/decisions.jsonl` or `memory/events.jsonl` (see `memory/MEMORY.md`) |
| Run something every week, a scheduled job | Read `automations/AUTOMATIONS.md` |
| Which AI tool or connector, how to point it at this folder | Read `tools/TOOLS.md` |
| You used a connector (calendar, Gmail, Drive…) that `tools/TOOLS.md` does not list | Record it: the first time you use a connector (for example Google Calendar, Gmail or Google Drive), add a line for it to `tools/TOOLS.md` without asking, then tell the person once, in one line, that you have listed it |
| What is due? | `python3 scripts/jobs.py list .` (see `scripts/SCRIPTS.md`) |
| Make a new skill | Read `skills/SKILLS.md` |
{{PERSONAL_ROUTES}}

## File index

```
CLAUDE.md          level 1 for Claude: who this is for, how to start, the rules (edit level 1 here)
GEMINI.md          level 1 for Gemini: the same words, copied by scripts/level1.py
AGENTS.md          level 1 block (the same words), then level 2: this manual
DOMAINS.md         the domains this brain has
README.md          what the folder is, for the person
brain.yaml         the files a brain must have (checked by BrainOS's tests)
setup.yaml         how far the setup has got; written only by kit/progress.py (made during setup)
exports/           raw export files; read only to import them; never backed up
kit/               BrainOS (setup guide, importers); never edit it; never backed up
automations/       AUTOMATIONS.md: scheduled jobs
memory/            MEMORY.md, decisions.jsonl, events.jsonl, calendar/, conversations/, profile/
scripts/           SCRIPTS.md, jobs.py, level1.py
skills/            SKILLS.md, one folder per skill with its SKILL.md
tools/             TOOLS.md, ai-tools/ (one card per AI tool)
views/             pages made by show-it-visually, views/<YYYY-MM-DD>-<name>.html (made the first time one is saved)
{{PERSONAL_INDEX}}
```

## Conventions

- `.jsonl`: one JSON object per line. Every line has `source` (where it came from: an importer, a file, or "you said so on <date>") and `confidence` (high, medium or low). Add new lines at the end; do not rewrite lines someone else wrote. To retire a line, add `"status": "archived"` rather than deleting it.
- Importers own their own lines. Re-running an importer replaces only the lines and files it wrote before; lines added by hand or by a skill are kept.
- `.yaml`: lists written by the importers. `.md`: instructions and readable text.
- Dates are written YYYY-MM-DD.
- Each person appears once in `{{PEOPLE}}people.jsonl`, merged across every import, with a stable `id` (for example `person_priya_demo`). Refer to people by that id elsewhere.
- Name the file each point of an answer came from.

## Importing

Importers live in BrainOS, in this brain's `kit/importers/` folder. If there is no `kit/` folder, ask the person to paste the one line again: it names BrainOS, and its `SETUP.md` puts BrainOS back in `kit/` without touching the brain. Each importer takes an export file and this brain folder. Run them from this folder with Python 3 (nothing to install). Look for the export files in this brain's `exports/` folder first: `python3 kit/check_setup.py .` lists them, with the exact line to run for each.

If you cannot see the export files, send the person one short message with two choices, and no others: drag the files into this brain's `exports` folder (then you need only this folder); or leave them in Downloads, and they click "Allow once" when you ask to use Downloads (it lasts this chat only; heads-up: you can then read and change everything in Downloads for this chat, and the files you read are processed by your provider).

- LinkedIn: `python3 kit/importers/linkedin.py <linkedin-archive.zip> .`
- WhatsApp: `python3 kit/importers/whatsapp.py <chat-export.txt or .zip or folder> . --me "<their name>"`. Ask once, before the first WhatsApp import, for their own name as it shows in their WhatsApp chats (often just a first name). The brain remembers it in `brain.yaml`, so they are never asked again and never listed as a contact. If the importer stops and lists the names in the chats, ask which one is theirs, then run it again with `--me`.
- Calendar: `python3 kit/importers/calendar_ics.py <calendar.ics or .zip> .` (add `--me <their email>` once for each of the person's own addresses)
- Apple Contacts (Mac): `python3 kit/importers/apple_contacts.py <contacts.vcf> .`
- X / Twitter archive: `python3 kit/importers/x_export.py <archive.zip or folder> .`
- What you read through a connection in the AI app (calendar, email, WhatsApp and the like): save who and when as a `.json` file in `exports/`, in the shape `kit/SETUP.md` step 4 gives, then `python3 kit/importers/from_connector.py . exports/<file>.json` (this brain first, then the file). Never copy whole messages.

Where they write: people (from LinkedIn, WhatsApp, calendar and contacts) to `{{PEOPLE}}people.jsonl`; messages and meetings to `{{PEOPLE}}interactions.jsonl`; meetings also to `memory/calendar/events.yaml`; readable chats and your own posts to `memory/conversations/`; your LinkedIn and X profiles to `memory/profile/`.

Each prints what it found and what it skipped. A missing or odd file is reported and skipped, never fatal. Tell the person the counts in plain English. After the first imports, offer the `mine-my-context` skill.
