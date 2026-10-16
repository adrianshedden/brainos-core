# BrainOS core — the free edition

Your own second brain: a folder of plain Markdown and YAML on your own computer, readable by any AI.
Plain Python 3, nothing to install, no account. The kit's scripts never use the internet, except the
backup to a private GitHub repo of your own, if you choose to make one (step 7).

This is the free edition used by the Oxford bootcamp, under the GNU Affero General Public License v3.0 (AGPL-3.0). The paid edition (the live
connections library) is a separate product and is not in this folder.

Who makes it: BrainOS is the product, Remyn is the brand, and AI Ops is the company behind both.
That is why this kit lives in the `remyn-core` repository on GitHub.

A second brain is everything the AI remembers about you and your work and life. Facts, history, and how you like things done. The agent is what acts on it, tools are how it acts.

## Where your data goes

Your brain is stored as plain files on your laptop. When you use a cloud AI provider (Anthropic, OpenAI and others), whatever their agent reads is processed by that provider, like any chat. Run it with a local model in the future and it stays fully private on your machine. That is what we are working towards.

- The importers read your export files and write the brain. They never use the internet.
- Nothing is published. The only copy that goes online is a backup to your own private GitHub, and only if you set one up.
- Your raw export files, in the brain's `exports` folder, are never part of that backup.

## Free and paid

- Free: this kit. Your AI sets up your brain in a chat, from export files you download yourself.
- Paid: BrainOS Pro. One Mac app sets everything up for you, with no Terminal. It also connects your live accounts, such as Gmail, Outlook, Google Calendar, Notion and Slack, and reads them into your brain.

## Quick start

Run these from the top of your BrainOS download:

1. Check you are ready: `python3 check_setup.py ~/my-brain`. It changes nothing and says what to do next.
2. Choose your personal domains: the areas of your life your brain keeps, each in its own folder. Pick from network (the people you know and your conversations with them), work, knowledge, family, health and finance. Your AI will suggest three to five that fit you.
3. Make an empty brain in a new folder: `python3 create_brain.py ~/my-brain --domains network,work`
4. Put your export files in `~/my-brain/exports/`, then fill the brain from them. `check_setup.py` prints the exact line for each file. Any you have:
   - LinkedIn data archive: `python3 importers/linkedin.py ~/my-brain/exports/Basic_LinkedInDataExport.zip ~/my-brain`
   - WhatsApp chat export: `python3 importers/whatsapp.py ~/my-brain/exports/chat.txt ~/my-brain --me "Your Name"` (your own name as it shows in your chats, given once, so you are never listed as one of your own contacts)
   - Calendar file: `python3 importers/calendar_ics.py ~/my-brain/exports/calendar.ics ~/my-brain`
   - Apple Contacts export: `python3 importers/apple_contacts.py ~/my-brain/exports/contacts.vcf ~/my-brain`
   - X / Twitter archive: `python3 importers/x_export.py ~/my-brain/exports/twitter-archive.zip ~/my-brain`
5. Open `~/my-brain/tools/ai-tools/` and follow the card for whichever AI you use. Then ask it to "use the mine-my-context skill": it reads your imports, tells you what it thinks it knows about you, asks up to five short questions, and writes down only what you confirm.
6. Try the eight skills in `~/my-brain/skills/`, for example "Use the whats-on-my-plate skill". See which are due: `python3 jobs.py list ~/my-brain`
7. Back it up to your own private GitHub: follow `GITHUB.md`.

Each importer prints what it found and what it skipped, and is safe to re-run.

## What is in here

- `check_setup.py` — checks Python, the kit, the brain folder and your exports, and says the next step. Changes nothing.
- `create_brain.py` — stamps an empty brain from `template/`, with the personal domains you choose.
- `importers/` — LinkedIn, WhatsApp, calendar, Apple Contacts and X export readers. They only ever read a file you give them.
- `jobs.py` — lists the brain's skills and which are due, and marks one done. Each brain gets its own copy in `scripts/`.
- `publish_github.py` and `GITHUB.md` — back the brain up to a private GitHub repository you own, step by step.
- `template/` — the brain itself. `CLAUDE.md` (read first: who it is for, the rules), `AGENTS.md` (which folder or skill
  answers which request) and `DOMAINS.md`; five core domains, each with its own instructions file: `automations/`,
  `memory/`, `scripts/`, `skills/` (eight skills: mine-my-context and one per week-one question), `tools/` (one card per AI tool);
  `exports/`; and `domains/`, the library of personal domains (network, work, knowledge, family, health, finance).
- `sample/` — a filled brain made of invented people, so you can see the shape. Rebuild it with
  `python3 sample/build_sample.py`.
- `tests/` — the checks. Run them all: `bash tests/run_all.sh`

Instructions for a person or an AI driving this: `INSTRUCTIONS.md`. Licence: `LICENSE` (AGPL-3.0).
