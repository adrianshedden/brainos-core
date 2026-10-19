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

- Where the data goes. Before the first import, tell the person once, in plain words: "Your brain's files stay in your folder. When you ask a question, the parts the AI reads go to the AI company to work out the answer, the same as any chat with it. The kit sends nothing anywhere else. The importers never use the internet. Nothing is published unless you back up to your own private GitHub." Then, if they have asked for the import, go ahead. Do not stop to offer other ways of doing it.
- Never publish, post or send files from this folder to a website, a person or another service yourself. Working on them in your own workspace to do what the person asked is fine. The only copy that goes online is the person's own private GitHub backup, when they ask for it.
- Only the person's own data goes in. Do not add other people's private data from anywhere else.
- Connections live in your AI app or on your computer, never in this folder, and passwords never go in it. If the person has turned on a connector in their AI app or on their computer (for example Gmail or Google Calendar), you may read it when a skill says so; `tools/TOOLS.md` lists which are on. Connectors: the first time you use a connector (for example Google Calendar, Gmail or Google Drive), add a line for it to `tools/TOOLS.md` without asking, then tell the person once, in one line, that you have listed it.
- Do not read a person's file unless the task needs it.
- Never invent a fact. If it is not in the files and the person has not said it, ask. Every line you add to a `.jsonl` file carries `source` (where it came from) and `confidence` (high, medium or low).
- Never overwrite what the person wrote without asking, and never delete their files. Drafts are for the person to send: never send anything yourself.
