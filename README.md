# BrainOS core — the free edition

Your own second brain: a folder of plain text files on your own computer, readable by any AI.
Plain Python 3, nothing to install, no account. The kit's scripts never use the internet, except the
backup to a private GitHub repo of your own, if you choose to make one (step 7).

This is the free edition, under the GNU Affero General Public License v3.0 (AGPL-3.0). The paid part is a separate
product and is not in this folder.

Who makes it: BrainOS is the product, Remyn is the brand, and AI Ops is the company behind both.
This kit lives in the `brainos-core` repository on GitHub: github.com/adrianshedden/brainos-core.

A second brain is everything the AI remembers about you and your work and life. Facts, history, and how you like things done. The agent is what acts on it, tools are how it acts.

## Where your data goes

Your brain is stored as plain files on your laptop. When you use a cloud AI provider (Anthropic, OpenAI and others), whatever their agent reads is processed by that provider, like any chat. Run it with a local model in the future and it stays fully private on your machine. That is what we are working towards.

- The importers read your export files and write the brain. They never use the internet.
- Nothing is published. The only copy that goes online is a backup to your own private GitHub, and only if you set one up.
- Your raw export files, in the brain's `exports` folder, are never part of that backup.

## Free and paid

- Free: this kit. Your AI sets up your brain in a chat. It connects the accounts your AI app can reach (such as your calendar and email), and uses export files you download for the rest.
- Paid: Remyn, the guided set-up website, with templates and support, on top of this same kit.

## Set up with your AI (no commands)

Using the Claude app? Install it from claude.com/download, open it, and sign in inside the Claude app window. Signing in on the website does not sign in the app.

Paste this one line into the Claude app, the ChatGPT app (with Codex), Cursor, OpenCode or Orca on your computer:

> Set up my brain from the BrainOS kit at github.com/adrianshedden/brainos-core (read its SETUP.md first and follow it). Ask me before you change anything, work only in my brain folder, and never send my files anywhere.

Your AI follows `SETUP.md`, in nine steps: it finds or makes your brain (a folder called brain in your Documents, unless you choose another place), shows what it can connect (your calendar, email, documents, Notion, Slack and your existing notes, such as an Obsidian folder; WhatsApp chats you export; LinkedIn, if you like, now or later), gives you the exact clicks for each one, fills your brain, suggests the areas it should keep, learns what matters to you, sets up skills and scheduled jobs, and answers a first real question. Progress is saved after every step: stop any time, paste the same line again, and it carries on, in the same app or another.

Prefer a terminal? One line does the download and starts your AI if it finds one:

- Mac: `curl -fsSL https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.sh | sh`
- Windows (PowerShell): `irm https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.ps1 | iex`

This is kit version 2.0 (`VERSION`).

## Quick start (by hand)

Run these from the top of your BrainOS download. On Windows, type `py` wherever this says `python3` (`python3` there is usually missing or opens the Microsoft Store); if `py` is missing too, try `python`.

1. Check you are ready: `python3 check_setup.py ~/my-brain`. It changes nothing and says what to do next.
2. Choose your personal domains: the areas of your life your brain keeps, each in its own folder. Pick from network (the people you know and your conversations with them), work, knowledge, family, health and finance. Your AI will suggest three to five that fit you.
3. Make an empty brain in a new folder: `python3 create_brain.py ~/my-brain --domains network,work`. To add more areas later: `python3 create_brain.py ~/my-brain --add family,health`
4. Put your export files in `~/my-brain/exports/`, then fill the brain from them. `check_setup.py` prints the exact line for each file. Any you have:
   - LinkedIn data archive: `python3 importers/linkedin.py ~/my-brain/exports/Basic_LinkedInDataExport.zip ~/my-brain`
   - WhatsApp chat export: `python3 importers/whatsapp.py ~/my-brain/exports/chat.txt ~/my-brain --me "Your Name"` (your own name as it shows in your chats, given once, so you are never listed as one of your own contacts)
   - Calendar file: `python3 importers/calendar_ics.py ~/my-brain/exports/calendar.ics ~/my-brain`
   - Apple Contacts export: `python3 importers/apple_contacts.py ~/my-brain/exports/contacts.vcf ~/my-brain`
   - X / Twitter archive: `python3 importers/x_export.py ~/my-brain/exports/twitter-archive.zip ~/my-brain`
5. Open `~/my-brain/tools/ai-tools/` and follow the card for whichever AI you use. Then ask it to "use the mine-my-context skill": it reads your imports, tells you what it thinks it knows about you, asks up to five short questions, and writes down only what you confirm.
6. Try the eleven skills in `~/my-brain/skills/`, for example "Use the whats-on-my-plate skill". See which are due: `python3 jobs.py list ~/my-brain`
7. Back it up to your own private GitHub: follow `GITHUB.md`.

Each importer prints what it found and what it skipped, and is safe to re-run.

## What is in here

- `check_setup.py` — checks Python, the kit, the brain folder and your exports, and says the next step. Changes nothing.
- `SETUP.md` — the guided first run your AI follows when you paste the one line: nine steps, with progress saved.
- `progress.py` — saves how far the setup has got, in the brain's `setup.yaml`, so you can stop and carry on later.
- `create_brain.py` — stamps an empty brain from `template/`, with the personal domains you choose; `--add` puts more into a brain you already have (for example `python3 kit/create_brain.py . --add work,family` from inside the brain).
- `start.sh` and `start.ps1` — the terminal line for a Mac and for Windows: download the kit into your brain folder and start your AI.
- `connections.yaml` — every account each AI app can connect, with the exact clicks, in the order the setup offers them.
- `level1.py` — keeps level 1 the same at every AI's front door; each brain gets a copy in `scripts/`.
- `importers/` — LinkedIn, WhatsApp, calendar, Apple Contacts and X export readers, plus `from_connector.py`, which saves who and when from what your AI read through a connection. They only ever read a file you give them.
- `jobs.py` — lists the brain's skills and which are due, and marks one done. Each brain gets its own copy in `scripts/`.
- `publish_github.py` and `GITHUB.md` — back the brain up to a private GitHub repository you own, step by step.
- `WHATSAPP-LIVE.md`, `whatsapp_live.py` and `whatsapp_send_guard.py` — optional, never part of setup: a live link to WhatsApp, for people who want it after setup. Risks and a yes first, reading first, and sending only with a second yes, with each message shown to you word for word before it goes. Sending works in Claude Code only. Switch it off or remove it any time.
- `template/` — the brain itself. `LEVEL1.md` is level 1 (who it is for, how to start, the rules), written once and
  copied word for word to `CLAUDE.md` (Claude), `GEMINI.md` (Gemini) and the top of `AGENTS.md` (Codex, Cursor and
  others); `AGENTS.md` is level 2 (which folder or skill answers which request) and `DOMAINS.md` lists level 3; five core domains, each with its own instructions file: `automations/`,
  `memory/`, `scripts/`, `skills/` (eleven skills: mine-my-context, one per week-one question, morning-brief, weekly-review and show-it-visually), `tools/` (one card per AI tool);
  `exports/`; and `domains/`, the library of personal domains (network, work, knowledge, family, health, finance).
- `sample/` — a filled brain made of invented people, so you can see the shape. Rebuild it with
  `python3 sample/build_sample.py`.
- `tests/` — the checks. Run them all: `bash tests/run_all.sh`

Instructions for a person or an AI driving this: `INSTRUCTIONS.md`. Licence: `LICENSE` (AGPL-3.0).
