# BrainOS core: instructions for any AI

BrainOS core makes an empty brain (a folder of Markdown and YAML files) on the person's own computer and fills it from their own exports and from the connections in their AI app. Plain Python 3, nothing to install. No script in this kit uses the internet, except the optional GitHub backup, which the person starts themselves (`GITHUB.md`). Run each step for the person and tell them the result in plain English.

Setting a brain up for the first time, or carrying on with one, because the person pasted the one line? Follow `SETUP.md` instead: it is the guided first run in nine steps (find or make the brain, choose and connect their accounts, pull everything in, domains, review, skills, scheduled jobs, a first real answer), and it saves progress in the brain's `setup.yaml`. This file is the reference for every step. The one line, from the kit's home at github.com/adrianshedden/brainos-core:

- In an AI app: Set up my brain from the BrainOS kit at github.com/adrianshedden/brainos-core (read its SETUP.md first and follow it). Ask me before you change anything, work only in my brain folder, and never send my files anywhere.
- In a terminal on a Mac: `curl -fsSL https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.sh | sh`
- In a terminal on Windows (PowerShell): `irm https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.ps1 | iex`

On Windows, type `py` wherever this kit says `python3` (`python3` there is usually missing or opens the Microsoft Store); if `py` is missing too, try `python`.

The order is: check, choose domains, create the brain, import, mine my context, first skills.

0. Check the setup first: `python3 check_setup.py <folder>`. It changes nothing. Tell the person what it found, then follow its next step.
1. Choose the personal domains, before creating the brain. A domain is one area of their life with its own folder and instructions file. Every brain has five core domains (automations, memory, scripts, skills, tools); personal domains come from this list: network (the people they know and every conversation with them), work (job, business or ventures), knowledge (notes and reading), family, health, finance. Offer three to five that fit, based on what they have told you and which exports they have (any LinkedIn, WhatsApp, calendar or contacts export means network). Ask them to pick, in one short message. More can be added later.
2. Create the brain with their choice: `python3 create_brain.py <folder> --domains network,work` (their domains, comma-separated; `--domains none` for none). The folder must be new or empty; it may already hold an `exports` folder. To add domains to a brain that already exists: `python3 create_brain.py <folder> --add family,health`.
3. Read level 1, then level 2. Level 1 is written once in `template/LEVEL1.md` and copied word for word to every AI's front door: `<folder>/CLAUDE.md`, `<folder>/GEMINI.md` and the top of `<folder>/AGENTS.md` (check with `python3 <folder>/scripts/level1.py check <folder>`). Level 2 is the rest of `<folder>/AGENTS.md`. They say how the brain is laid out, which domain or skill answers which request, and what you may do with it. Each domain folder has its own `{DOMAIN}.md`; read one only when the task touches it.
4. Before the first import, tell the person once, in plain words, where their data goes (the words are under "Where the data goes" below). Then, if they have asked for the import, go ahead. Do not stop to offer other ways of doing it.
5. Find the exports. Look in `<folder>/exports/` first: `check_setup.py` lists what is there and the exact line to run for each file. If you cannot see the export files, send the person one short message with these two choices, and no others:
   - "Drag your export files into the brain's `exports` folder. Then I only need the brain folder."
   - "Or leave them in Downloads. When I ask to use your Downloads folder, click Allow once. It lasts for this chat only. Heads-up: I can then read and change everything in Downloads for this chat, and the files I read are processed by my provider (for Claude, Anthropic)."
6. Import whichever exports the person has:
   - LinkedIn (the data archive .zip): `python3 importers/linkedin.py <archive.zip> <folder>`
   - WhatsApp (a chat export .txt, .zip or folder): `python3 importers/whatsapp.py <export> <folder> --me "<their name>"`. Ask once, before the first WhatsApp import, for their own name as it shows in their WhatsApp chats (often just a first name). The brain remembers it in `brain.yaml`, so they are never asked again and never listed as a contact. If the importer stops and lists the names in the chats, ask which one is theirs, then run it again with `--me`.
   - Calendar (.ics file, or a .zip of them): `python3 importers/calendar_ics.py <file.ics> <folder>` (add `--me <their email>` for each of their own addresses, if the top-people list shows any of them; robot and room addresses are left out by themselves)
   - Apple Contacts (a .vcf export, or a folder of them): `python3 importers/apple_contacts.py <export> <folder>`
   - X / Twitter (the data archive .zip, or the unzipped folder): `python3 importers/x_export.py <archive> <folder>`
   - What the AI read through a connection in its app (a `.json` file it saved in `exports`, in the shape `SETUP.md` step 4 gives): `python3 importers/from_connector.py <folder> <file.json>` (the brain first, then the file)
   Each importer prints counts and anything it skipped. Re-running is safe. People from every import are merged into one list, `network/people.jsonl` (or `memory/people/people.jsonl` without a network domain), and messages and meetings into `interactions.jsonl` beside it.
7. Mine my context: follow `<folder>/skills/mine-my-context/SKILL.md`. It reads the imports, proposes who the person is, what they do, their goals this quarter, their key people and patterns, asks them at most five short questions, and writes down only what they confirm, each fact with its source and confidence.
8. First skills. The brain ships with eleven skills in `skills/`: `mine-my-context` (step 7); one per week-one question: what is on my plate this week, who should I reply to first, who do I know at an organisation, draft a message in my voice, what have I been putting off, prep me for my next meeting, who have I gone quiet with; and `morning-brief`, `weekly-review` and `show-it-visually` (shows an answer as a page). To run one, follow its `SKILL.md` and name the file each point of the answer came from. See what's due: `python3 jobs.py list <folder>`. Mark one done: `python3 jobs.py done <folder> <skill-name>`. To run one every week, see `<folder>/automations/AUTOMATIONS.md`.
9. `<folder>/tools/ai-tools/` has one card per AI tool (the Claude app's Chat tab, Claude in a browser, Claude Code, ChatGPT, Codex, OpenCode, Cursor, Orca, others): how to point it at the brain and what it can and cannot do, each line with its source and the date it was checked.
10. Setup progress lives in `<folder>/setup.yaml` and is written only by `progress.py`: `python3 progress.py <folder> show`, `step <n>`, `pick <id> ...`, `connected <id> <how>`, `pending "<what>" "<what to say when it arrives>"`, `arrived "<what>"`, `app <name>`, `done`. Each prints one plain line. `check_setup.py` reads it and starts with "Carry on from step <n>". The connections each AI app offers, with the exact clicks, are in `connections.yaml`.
11. To back the brain up to the person's own private GitHub, walk them through `GITHUB.md`. Always show the dry run first: `python3 publish_github.py <folder> <their-repo-address>`. Only add `--apply` when they say so. The `exports` folder is never backed up.

To see what a filled brain looks like, open `sample/brain/` (made-up people, built by `python3 sample/build_sample.py`).

## Where the data goes

Say this to the person once, before the first import, in these or similar plain words:

"Your brain is stored as plain files on your laptop. When you use a cloud AI provider (Anthropic, OpenAI and others), whatever their agent reads is processed by that provider, like any chat. Run it with a local model in the future and it stays fully private on your machine. That is what we are working towards. The importers never use the internet. Nothing is published unless you back up to your own private GitHub."

## Rules

- Only the person's own data.
- Connections live in your AI app or on your computer, never in this folder, and passwords never go in it. Connectors the person turns on in their AI app or on their computer are listed in the brain's `tools/TOOLS.md`: the first time you use a connector (for example Google Calendar, Gmail or Google Drive), add a line for it to `tools/TOOLS.md` without asking, then tell the person once, in one line, that you have listed it.
- Never publish, post or send the brain's files to a website, a person or another service yourself. Working on them in your own workspace to do what the person asked is fine. The only copy that goes online is the person's own private GitHub backup, when they ask for it.

Check everything works: `bash tests/run_all.sh`
