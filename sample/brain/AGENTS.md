<!-- BrainOS level 1: start. The same words as CLAUDE.md and GEMINI.md. To change them, edit CLAUDE.md, then run: python3 scripts/level1.py sync . -->

# My brain (level 1)

Read this first, every session. The same words are at every AI's front door: `CLAUDE.md` (Claude reads it), `GEMINI.md` (Gemini reads it) and the top of `AGENTS.md` (Codex in the ChatGPT app, Cursor and most other AI apps read it). Whichever you opened, you have read level 1. Then read the level 2 manual in `AGENTS.md`.

This folder is one person's own second brain: plain Markdown, YAML and JSONL files on their own computer, readable by any AI. It is set out in three levels, so you read only what a task needs:

- Level 1 (this text): what this brain is, who it is for, how to start a session, and the rules.
- Level 2, `AGENTS.md` (below the level 1 block): which domain or skill to use for which request, the file index and the conventions.
- Level 3, one `{DOMAIN}.md` in each folder (for example `memory/MEMORY.md`): read it only when the task touches that folder. `DOMAINS.md` lists them.

## Who this is for

Written by the `mine-my-context` skill and confirmed by the person. Each line says where it came from and how sure it is. Until it is filled in, ask the person rather than guess.

- Name: not known yet.
- What they do: not known yet.
- How they like to work: not known yet.

## Goals this quarter

- Not known yet.

## How to start a session

1. Read this text, then the level 2 manual in `AGENTS.md`.
2. If "Who this is for" still says "not known yet", offer the `mine-my-context` skill before anything else.
3. Find the request in the routing table in `AGENTS.md`. Read that domain's `{DOMAIN}.md`, or that skill's `SKILL.md`, and follow it.
4. Read only the files the task needs. Name the file each point of your answer came from.
5. Before you save anything new in the brain, say what you will save and where.
6. Level 1 has three copies that must stay word for word the same. To change level 1, edit `CLAUDE.md` only, then run `python3 scripts/level1.py sync .` from this folder. It copies the words to `GEMINI.md` and the top of `AGENTS.md`. `python3 scripts/level1.py check .` says whether they still match.

## Rules

- Where the data goes. Before the first import, tell the person once, in plain words: "Your brain is stored as plain files on your laptop. When you use a cloud AI provider (Anthropic, OpenAI and others), whatever their agent reads is processed by that provider, like any chat. Run it with a local model in the future and it stays fully private on your machine. That is what we are working towards. The importers never use the internet. Nothing is published unless you back up to your own private GitHub." Then, if they have asked for the import, go ahead. Do not stop to offer other ways of doing it.
- Never publish, post or send files from this folder to a website, a person or another service yourself. Working on them in your own workspace to do what the person asked is fine. The only copy that goes online is the person's own private GitHub backup, when they ask for it.
- Only the person's own data goes in. Do not add other people's private data from anywhere else.
- Never build a live connection here. If the person has turned on a connector in their AI app (for example Gmail or Google Calendar), you may read it when a skill says so; `tools/TOOLS.md` lists which are on. Connectors: the first time you use a connector (for example Google Calendar, Gmail or Google Drive), add a line for it to `tools/TOOLS.md` without asking, then tell the person once, in one line, that you have listed it.
- Do not read a person's file unless the task needs it.
- Never invent a fact. If it is not in the files and the person has not said it, ask. Every line you add to a `.jsonl` file carries `source` (where it came from) and `confidence` (high, medium or low).
- Never overwrite what the person wrote without asking, and never delete their files. Drafts are for the person to send: never send anything yourself.

<!-- BrainOS level 1: end. Level 2 starts below. -->

# How this brain works (level 2)

Read level 1 first: it is the block above (the same words as `CLAUDE.md` and `GEMINI.md`). This manual says which domain or skill answers which request, where every file is, and the conventions for adding to it. Read a domain's `{DOMAIN}.md` only when the task touches it.

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
| Set up my BrainOS, finish my setup, connect something new | Follow `kit/SETUP.md` (the setup guide in the BrainOS kit) |
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
CLAUDE.md          level 1 for Claude: who this is for, how to start, the rules (edit level 1 here)
GEMINI.md          level 1 for Gemini: the same words, copied by scripts/level1.py
AGENTS.md          level 1 block (the same words), then level 2: this manual
DOMAINS.md         the domains this brain has
README.md          what the folder is, for the person
brain.yaml         the files a brain must have (checked by the kit's tests)
exports/           raw export files; read only to import them; never backed up
kit/               the BrainOS kit (setup guide, importers); never edit it; never backed up
automations/       AUTOMATIONS.md: scheduled jobs
memory/            MEMORY.md, decisions.jsonl, events.jsonl, calendar/, conversations/, profile/
scripts/           SCRIPTS.md, jobs.py, level1.py
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

Importers live in the BrainOS kit, in this brain's `kit/importers/` folder. If there is no `kit/` folder, ask the person to paste their Remyn setup instruction again: it names the kit, and its `SETUP.md` puts the kit back in `kit/` without touching the brain. Each importer takes an export file and this brain folder. Run them from this folder with Python 3 (nothing to install). Look for the export files in this brain's `exports/` folder first: `python3 kit/check_setup.py .` lists them, with the exact line to run for each.

If you cannot see the export files, send the person one short message with two choices, and no others: drag the files into this brain's `exports` folder (then you need only this folder); or leave them in Downloads, and they click "Allow once" when you ask to use Downloads (it lasts this chat only; heads-up: you can then read and change everything in Downloads for this chat, and the files you read are processed by your provider).

- LinkedIn: `python3 kit/importers/linkedin.py <linkedin-archive.zip> .`
- WhatsApp: `python3 kit/importers/whatsapp.py <chat-export.txt or .zip or folder> . --me "<their name>"`. Ask once, before the first WhatsApp import, for their own name as it shows in their WhatsApp chats (often just a first name). The brain remembers it in `brain.yaml`, so they are never asked again and never listed as a contact. If the importer stops and lists the names in the chats, ask which one is theirs, then run it again with `--me`.
- Calendar: `python3 kit/importers/calendar_ics.py <calendar.ics or .zip> .` (add `--me <their email>` once for each of the person's own addresses)
- Apple Contacts (Mac): `python3 kit/importers/apple_contacts.py <contacts.vcf> .`
- X / Twitter archive: `python3 kit/importers/x_export.py <archive.zip or folder> .`

Where they write: people (from LinkedIn, WhatsApp, calendar and contacts) to `network/people.jsonl`; messages and meetings to `network/interactions.jsonl`; meetings also to `memory/calendar/events.yaml`; readable chats and your own posts to `memory/conversations/`; your LinkedIn and X profiles to `memory/profile/`.

Each prints what it found and what it skipped. A missing or odd file is reported and skipped, never fatal. Tell the person the counts in plain English. After the first imports, offer the `mine-my-context` skill.
