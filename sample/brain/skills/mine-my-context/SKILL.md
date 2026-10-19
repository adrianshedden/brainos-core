---
name: mine-my-context
description: Get to know me from my own imported files. Read memory and my people, propose who I am, what I do, my goals this quarter, my key people and patterns, ask me to confirm in at most five short questions, then write down only what I confirmed. Use after the first imports, or when I say "get to know me" or "mine my context".
---
# Mine my context

Question: Who am I, as far as my own files show?
Cadence: as-needed
Read: memory/, network/, CLAUDE.md, DOMAINS.md

Three stages, in this order. Do not skip ahead: nothing is written until the person has confirmed it.

## 1. Gather (read, write nothing)

- Read what the imports produced: `memory/profile/` (what LinkedIn and X say about me), `network/people.jsonl` and `network/interactions.jsonl`, `memory/calendar/events.yaml`, and a sample of `memory/conversations/` (the most recent chats first, my own messages above all).
- For large files, count and sample rather than reading every line. Note which files you read and how many lines each had.
- If a file is missing, say which export would fill it. Do not stop.

## 2. Make sense of it (still write nothing)

Work out, each with the file(s) it rests on and how sure you are (high: stated outright in my own profile or by me; medium: clear from several messages or meetings; low: one hint):

- Who I am: name, and how I come across in my own messages.
- What I do: role, organisation, the work that fills my calendar.
- Goals this quarter: only what my files show I am working towards. If nothing shows it, say so and ask.
- Key people: the five to ten people I meet or message most (count lines per person in `interactions.jsonl`), each by their `id`, with how we are connected.
- Patterns: when I meet, who waits on me, what keeps coming up.
- Extra personal domains worth adding (see `DOMAINS.md` for what exists): only if the files show a clear area of life with no home yet, for example `work` when most meetings are about a venture, or `family` when a family group chat is busy.

## 3. Confirm, then write

- Show the person a short summary, in plain English, with the source and confidence after each point.
- Ask at most five short questions, the ones that matter most: anything low confidence, the goals, and any domain you recommend. Accept "skip".
- Then write only what they confirmed or corrected:
  - `CLAUDE.md`: fill "Who this is for" and "Goals this quarter". After each line, in brackets: the source file(s), the confidence, and "confirmed by you on YYYY-MM-DD". Then run `python3 scripts/level1.py sync .` so `GEMINI.md` and the top of `AGENTS.md` say the same.
  - Each relevant `{DOMAIN}.md`: replace the placeholder under "What's here" with one to three lines, each with its source and confidence (for example `memory/MEMORY.md` and `network/NETWORK.md`).
  - `memory/decisions.jsonl`: one line for each choice the person made here (goals, a domain added or declined), shaped as `memory/MEMORY.md` says, with `"source": "mine-my-context, confirmed by you"` and a `confidence`.
  - A domain they agree to add: follow "Adding a domain" in `DOMAINS.md`.
- Tell them what you wrote and where, in one short list.

Show your sources: every point in the summary, and every line written, names the file(s) it came from and a confidence.
Never: invent a fact, fill a gap with a guess, write anything the person has not confirmed, or add other people's private details beyond what is already in the brain. If the files do not say it, ask or leave it out.
