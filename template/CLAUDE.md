# My brain

Read this file first, every session. Then read `AGENTS.md`.

This folder is one person's own second brain: plain Markdown, YAML and JSONL files on their own computer, readable by any AI. It is set out in three levels, so you read only what a task needs:

- Level 1, `CLAUDE.md` (this file): who this brain is for, how to start a session, and the rules.
- Level 2, `AGENTS.md`: which domain or skill to use for which request, the file index and the conventions.
- Level 3, one `{DOMAIN}.md` in each folder (for example `memory/MEMORY.md`): read it only when the task touches that folder. `DOMAINS.md` lists them.

## Who this is for

Written by the `mine-my-context` skill and confirmed by the person. Each line says where it came from and how sure it is. Until it is filled in, ask the person rather than guess.

- Name: not known yet.
- What they do: not known yet.
- How they like to work: not known yet.

## Goals this quarter

- Not known yet.

## How to start a session

1. Read this file, then `AGENTS.md`.
2. If "Who this is for" still says "not known yet", offer the `mine-my-context` skill before anything else.
3. Find the request in the routing table in `AGENTS.md`. Read that domain's `{DOMAIN}.md`, or that skill's `SKILL.md`, and follow it.
4. Read only the files the task needs. Name the file each point of your answer came from.
5. Before you save anything new in the brain, say what you will save and where.

## Rules

- Where the data goes. Before the first import, tell the person once, in plain words: "Your brain is stored as plain files on your laptop. When you use a cloud AI provider (Anthropic, OpenAI and others), whatever their agent reads is processed by that provider, like any chat. Run it with a local model in the future and it stays fully private on your machine. That is what we are working towards. The importers never use the internet. Nothing is published unless you back up to your own private GitHub." Then, if they have asked for the import, go ahead. Do not stop to offer other ways of doing it.
- Never publish, post or send files from this folder to a website, a person or another service yourself. Working on them in your own workspace to do what the person asked is fine. The only copy that goes online is the person's own private GitHub backup, when they ask for it.
- Only the person's own data goes in. Do not add other people's private data from anywhere else.
- Never build a live connection here. If the person has turned on a connector in their AI app (for example Gmail or Google Calendar), you may read it when a skill says so; `tools/TOOLS.md` lists which are on. Connectors: the first time you use a connector (for example Google Calendar, Gmail or Google Drive), add a line for it to `tools/TOOLS.md` without asking, then tell the person once, in one line, that you have listed it.
- Do not read a person's file unless the task needs it.
- Never invent a fact. If it is not in the files and the person has not said it, ask. Every line you add to a `.jsonl` file carries `source` (where it came from) and `confidence` (high, medium or low).
- Never overwrite what the person wrote without asking. Drafts are for the person to send: never send anything yourself.
