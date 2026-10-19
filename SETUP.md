# BrainOS setup, kit version 2.0

For the AI. The person pasted this line into you:

> Set up my brain from the BrainOS kit at github.com/adrianshedden/brainos-core (read its SETUP.md first and follow it). Ask me before you change anything, work only in my brain folder, and never send my files anywhere.

Or they ran the terminal line, which downloaded the kit, made the brain folder and started you with that same line. Follow the nine steps below in order. You do the work; the person only clicks where a step says so. Progress is saved after every step (`setup.yaml`, written by `kit/progress.py`), so they can stop at any point and paste the same line again, in this app or another, and you carry on where they left off.

## How to work, the whole way through

The person is not technical. Speak to them that way, every message:

- Plain British English. Short messages. One question at a time, unless a step says to ask two together.
- No jargon. If a technical word cannot be avoided, explain it once, in five words or fewer, in brackets. Never show long command output: say in one line what happened and what it means.
- Before a command, say in one line what it does. Their app may ask them to approve it: tell them that is normal ("You may see a box asking to allow this. Click Allow.").
- One step at a time. Give exact button names, in bold, from `connections.yaml`. Wait for "done" or "skip" before you go on.

What you may and may not do:

- Ask before you change anything. Change files only inside the brain folder (and your own scratch space, if your app has one). Never delete anything, and never overwrite what the person wrote. The one exception is the brain's `kit` folder, which is the kit's own copy (step 1).
- Never send, upload or post the person's files anywhere. The kit's scripts never use the internet. Never send a message, email or post for them during setup.
- Connections live in the AI app or on the computer, never in the brain folder. That is the one exception to "work only in my brain folder": with the person's yes, you may add a connection in the AI app's own settings (for example in Cursor, OpenCode, Codex or Claude Code, when a route in `connections.yaml` says to), and change nothing else outside the brain folder. Never put a connection's settings inside the brain folder. Passwords, keys and sign-in codes never go in the brain: never write one in a file, and never ask the person to type one into this chat. If a step needs one, they type it into the app's own screen.
- Read-only wherever it is offered. If anything asks to allow sending (for example on WhatsApp), the person refuses: the brain only reads.
- Command-line tools are for technical people only. Never offer a route marked `technical_only: true`, or a command-line tool, unless the person has said they are technical (for example "I'm a developer"). Never push one.
- Never block the setup on something slow. If something is on its way (for example the LinkedIn archive), save it as pending (below) and carry on.
- If something fails, never leave the person stuck and never ask them to fix it. Say in one plain line what it means, try the next route, and fall back to an export file. Exports always work.

Commands:

- Run every command from inside the brain folder (move into it first). Every command below is written that way, for example `python3 kit/progress.py . step 2`.
- On Windows, run every `python3` command in this kit as `py` instead (for example `py kit/create_brain.py . --domains network`): `python3` there is usually missing or opens the Microsoft Store. If `py` is missing too, try `python`.
- Save progress only with `kit/progress.py`. It prints one plain line each time; you need not show it. Its commands: `show`, `step <n>` (the next step to do), `pick <id> ...`, `connected <id> <how>` (how: builtin, custom, local, cli or export), `pending "<what>" "<what to say when it arrives>"`, `arrived "<what>"`, `app <name>` and `done`.

## 1. Find or make the brain (one-line)

**What you do**

1. Work out which app you are in. Its name for `progress.py` is one of: `claude` (the Claude app on a computer), `chatgpt` (the ChatGPT app with Codex, or the Codex app), `cursor`, `opencode`, `orca`, `terminal` (Claude Code, Codex or another AI working in a terminal window) or `other`. If you cannot tell, ask: "Which app are you using me in: Claude, ChatGPT, Cursor, or something else?"
2. Check you can work here. You need to open and change a folder on the person's computer and run Python 3 (`python3 --version`; on Windows `py --version`).
   - If you cannot reach folders on their computer (for example the ChatGPT or Claude website, or any phone app), stop and say, in one or two lines: "I can't work on folders on your computer from here. Open the Claude app, the ChatGPT app (with Codex), Cursor or OpenCode on your computer, and paste the same line there."
   - If Python 3 is missing, say so in one line and offer to walk them through installing it from python.org. Do not install anything without their yes. On Windows, the python.org installer's defaults are fine; afterwards the person may need to close and reopen your app before `py` works.
3. Look for a brain they already have, the same way the terminal line does: a folder with a `brain.yaml` in it, or one holding a `kit` folder (the terminal line makes that). Look first wherever the person said, then at `Documents/brain`, then at `brain` in their home folder. If you cannot see their folders yet, ask them to let you first (point 5.1).
   - **You were started inside a folder that holds only `kit`**, or you found one that holds only `kit` (and perhaps `exports` or `setup.yaml`): the terminal line made it, so that is the brain folder. Use the kit that is there (point 6 only checks it is the newest), skip point 4 and build the brain there (point 5, from 5.3).
   - **Found, with a `setup.yaml`:** they are carrying on. Refresh the kit (point 6), save the app again (`python3 kit/progress.py . app <name>`: they may have switched apps), then run `python3 kit/check_setup.py .`. Its first line says where to carry on, for example "Carry on from step 3: connect them", and the lines after it say what is still on its way. Tell the person in one line, for example: "Welcome back. Last time we got to step 3, connecting your accounts. Shall I carry on from there?" Then go to that step. If it says setup is finished, see "Coming back later" at the end.
   - **Found, with no `setup.yaml`:** a brain made by an older kit. Do not build it again. Refresh the kit (point 6), record the app (point 7), then go to step 2.
   - **A folder of that name holds other files and no `brain.yaml`:** it is not a brain. Do not touch it: ask for another name.
   - **Nothing found:** make a new brain (point 4).
4. Choose the place the same way the terminal line does. The brain goes in `Documents/brain`, unless Documents is copied to the cloud: then it goes in `brain` in their home folder, where it stays on this computer. To check: on a Mac, Documents is in iCloud when `~/Library/Mobile Documents/com~apple~CloudDocs/Documents` exists, and it is copied online when its real location is inside iCloud, OneDrive, Dropbox, Google Drive or `~/Library/CloudStorage`; on Windows, Documents is in OneDrive when its real location is inside a OneDrive folder. If it is copied, say so in one line: "Heads-up: your Documents folder is copied to iCloud, so your brain would be too. I'll make it in your home folder instead, where it stays on this computer." (Say OneDrive, or whichever it is.) Then ask, in one message, with that place first: "I'll make a folder called brain in your Documents. Is that all right? If not, say where: Desktop, Documents, or somewhere else. I'll create it once you say." (Name the home folder instead of Documents when Documents is copied.)
5. With their yes, make the brain:
   1. If you cannot reach that place, tell them how to let you. In the Claude app: start a new chat, click **Project or folder** under the message box, choose the place (for example Documents), then click **Always allow**. In Codex, Cursor or OpenCode: open that place as the folder to work in. For the home folder, if the app cannot open it, ask them to make the folder themselves (Mac: in Finder, **Go**, **Home**, then **File**, **New Folder**, named brain; Windows: in File Explorer, open the folder with their name, **New folder**, named brain) and choose that.
   2. Make the empty `brain` folder and get the kit into a folder called `kit` inside it (point 6).
   3. Build the brain: `python3 kit/create_brain.py . --domains network`. Step 5 adds more areas later.
   4. Check the three front doors match: `python3 scripts/level1.py check .` It should say level 1 is the same in `CLAUDE.md`, `GEMINI.md` and the top of `AGENTS.md`.
   5. Read level 1 (your front door) and the level 2 manual in `AGENTS.md`. From now on, follow them as well as this guide.
6. The kit lives in the brain's `kit` folder. It is the kit's own copy, never the person's files.
   - **No `kit` folder:** download the newest kit into `kit`. Either `git clone --depth 1 https://github.com/adrianshedden/brainos-core kit`, or download https://github.com/adrianshedden/brainos-core/archive/refs/heads/main.zip and unpack what is inside its top folder into `kit`.
   - **A `kit` folder is there:** use it; never download a second copy. Compare `kit/VERSION` with https://raw.githubusercontent.com/adrianshedden/brainos-core/main/VERSION. If the online one is newer, ask: "There's a newer version of the kit. Shall I update it? Only the kit folder changes: your own files stay exactly as they are." With a yes, download it into a new folder `kit-new` in the brain, check it has `SETUP.md` and `progress.py`, then replace `kit` with it. Never touch anything outside `kit`.
   - **You cannot download:** ask the person to do it, one step at a time: open https://github.com/adrianshedden/brainos-core, click the green **Code** button, then **Download ZIP**; open the zip; rename the folder inside it to `kit`; drag it into the brain folder (if there is an old `kit`, drag that out to the Desktop first).
7. Save progress: `python3 kit/progress.py . app <name>` (the name from point 1), then `python3 kit/progress.py . step 2`.

**What you say**

Two lines: where the brain is, and that it is a plain folder of text files they can open any time. Then one line on what happens next: "Next, I'll show you what I can connect, like your calendar and email. You can stop at any point and pick up later."

**If something fails:** a download that fails is not a problem: use the "You cannot download" route. If `create_brain.py` says the folder is not empty, ask for another name. If `level1.py check` reports a difference, run `python3 scripts/level1.py sync .`.

## 2. Choose what to connect (choose)

**What you do**

1. Read `kit/connections.yaml`. Each source (for example `google-calendar`, `gmail`, `whatsapp`) has routes, each for one app (`app`) and of one type (`type`), already in the right order: the app's own connector (`builtin`), then a custom connector (`custom`), then a connector on the computer (`local`), then a command-line tool (`cli`), then an export file (`export`).
2. For each source, keep only the routes that work here: `app` is the name you saved in step 1, or `any`. Drop `technical_only: true` routes unless the person has said they are technical. Leave out any source with no route left.
3. Make a short list from what is left, most useful first: calendar, email, LinkedIn, WhatsApp, documents, then the rest. Put the same kind together so the list stays short ("Calendar: Google or Outlook"). After each, one line on why it fills the brain, and say plainly when the only route is a file they download ("a file you download from LinkedIn; it takes up to a day").

**What you ask**

Send the list and ask them to pick any (numbers are fine), or "none for now". For a source with two names (Google or Outlook), ask which one they use.

**Save progress:** `python3 kit/progress.py . pick <id> <id> ...` with the ids from `connections.yaml`, then `python3 kit/progress.py . step 3`. ("None for now" goes straight to `step 4`.)

**If something fails:** if `kit/connections.yaml` is missing or you cannot read it, use this list instead, and the steps in "Export steps" at the end:

1. **Email (Gmail or Outlook)**: who you write to, and who is waiting on you.
2. **Calendar (Google, Outlook or Apple)**: who you meet and how often, which shows your real priorities.
3. **LinkedIn**: everyone you know at work, and your career story. LinkedIn takes up to a day to send it, so start it first.
4. **WhatsApp**: where a lot of real work talk happens, and how you sound when you write.
5. **Google Drive**: what you are working on, in your own documents.
6. **Something else**: for example your contacts, X (Twitter) or Notion. Name it and I'll say how.

## 3. Connect them (connect)

Give steps only for what they picked. Never list steps for the others.

**What you do**

1. Start the slow ones first, so they arrive while you do the rest: LinkedIn, WhatsApp, then the rest. Anything that comes as an export file goes in the brain's `exports` folder.
2. For each pick, take its first route that works here (step 2) and give its `clicks`, one step at a time, with the button names in bold. Pick read-only wherever it is offered. If the route's `checked_on` is empty, add: "These steps haven't been checked yet. If a button looks different, tell me what you see." Pass on anything in its `notes` that matters (for example that a work account may need the IT team to allow it). If the route has you add the connection in the AI app's own settings (Cursor, OpenCode, Codex or Claude Code), say in one line what you will add and where, and add it only after their yes. Wait for "done" or "skip".
3. Do all the clicking first, then check them all. If a route says to restart the app or open a new chat, keep that for last, after all the other clicking. For each connected source, run its `proof_read`: one harmless read, such as listing tomorrow's events. Tell them in one line what you saw ("I can see your calendar: 4 events tomorrow.").
4. When a proof read works:
   - Save it: `python3 kit/progress.py . connected <id> <how>` (how is the route's `type`).
   - The first time you use a connector, add a line for it to `tools/TOOLS.md` without asking, then tell the person once, in one line, that you have listed it.
5. When the source is an export file: give the steps; when the file is in `exports`, save `connected <id> export`. If it will take a while, save it as pending and carry on, for example: `python3 kit/progress.py . pending "LinkedIn archive" "add my LinkedIn"`, and say: "That's started. We'll carry on, and you can add it when it arrives."

**What you ask:** only the clicks, one at a time, and "done" or "skip".

**Save progress:** when every pick is connected, pending or skipped: `python3 kit/progress.py . step 4`.

**If something fails**

- **A new connection does not show up yet.** Many apps only show a new connection in a new chat, or after a restart (for example after installing an extension). Progress is already saved, so say: "Your connections only show up in a new chat. Open a new chat, choose your brain folder again if it asks, and paste the same line. I'll carry on from here." On the way back, `check_setup.py` says which are still to connect.
- **A sign-in or proof read fails.** Say what it means in one plain line and offer one more try. If it fails again, go to that source's next route. The last route is always the export file.
- **It needs someone else's yes** (a work account's IT team, or the owner of a Claude Team plan). Say so in one line, use the export route for now, and save it as pending, for example `pending "Outlook calendar (waiting for your IT team)" "connect my Outlook"`.

## 4. Pull everything in (pull-in)

**What you do**

1. Before you bring anything in, send the person this, in a message of its own (it is required, once per setup): "Your brain is stored as plain files on your laptop. When you use a cloud AI provider (Anthropic, OpenAI and others), whatever their agent reads is processed by that provider, like any chat. Run it with a local model in the future and it stays fully private on your machine. That is what we are working towards. The importers never use the internet. Nothing is published unless you back up to your own private GitHub." Then go ahead.
2. Export files: run `python3 kit/check_setup.py .`. It lists the files in `exports` and the exact line to run for each. Run them. Before the first WhatsApp import, ask once for their own name as it shows in their chats. For each source that came in, save `python3 kit/progress.py . connected <id> export`, and if it was pending, `python3 kit/progress.py . arrived "<what>"`.
3. Live connections: read each one over a sensible window. Read only what the brain needs:
   - Calendar: the last 90 days and the next 14. For each event: when, who was there, and its title.
   - Email: who and when only, for the last 90 days, sent mail first. Never the message text, and never whole mailboxes.
   - Messages (WhatsApp, Slack and similar): who and when, one entry for each day you talked, for the last 90 days. Never copy what was written.
   - Documents (Google Drive, OneDrive, Notion): the names and dates of recent files only, to use in step 6. Save nothing from them.
4. Save what you read from each live connection as one file in `exports`, named `from-<source id>-<YYYY-MM-DD>.json`, in this shape: `{"people": [{"name": ..., "email": ..., "phone": ..., "source": ...}], "interactions": [{"when": ..., "with": ..., "channel": ..., "summary": ..., "source": ...}]}`. `email`, `phone` and `summary` are optional. `when` is a date (YYYY-MM-DD); `with` is the other person's name or email (one entry per person: a meeting with three people is three entries); `channel` is, for example, calendar, email or whatsapp; `source` is the source id from `connections.yaml` (never the name of an app or tool in between) and today's date, for example "google-calendar, 2026-10-21". Then bring it in: `python3 kit/importers/from_connector.py . exports/from-<source id>-<YYYY-MM-DD>.json`.
5. Tell the person what came in, in plain numbers: people, messages, meetings, and anything skipped.

**What you ask:** nothing, except their WhatsApp name once. They watch it fill.

**Save progress:** `python3 kit/progress.py . step 5`.

**If something fails:** if an importer stops, say what it means in one line and carry on with the others. If `kit/importers/from_connector.py` is missing, refresh the kit (step 1, point 6) and run it again. Never write lines in the people list or the interactions log by hand: only the importers write them. If the kit cannot be refreshed now, leave the file in `exports`, save it as pending (`python3 kit/progress.py . pending "What I read from your accounts" "bring in what you read"`) and carry on; it comes in the next time the kit is refreshed.

## 5. Choose the domains (domains)

A domain is one area of their life with its own folder. The brain already has network (the people they know).

**What you do:** from what came in, suggest two to four more from: work (job, business or ventures), knowledge (notes and reading), family, health and finance. One line each on why it fits, for example "work: most of your meetings are about your business".

**What you ask:** "Shall I add these? Say yes, or change them."

With their yes, add the ones from that list in one go, comma-separated, for example: `python3 kit/create_brain.py . --add work,family`. Then `python3 scripts/level1.py check .`. For an area that is not on that list, follow "Adding a domain" in `DOMAINS.md` (it shows `--add` too), one area at a time, with their yes.

**Save progress:** `python3 kit/progress.py . step 6`.

**If something fails:** if `--add` is not known, refresh the kit (step 1, point 6) and try again. If that is not possible, follow "Adding a domain" in `DOMAINS.md` by hand, one domain at a time, with their yes.

## 6. Review what it learned (review)

**What you do:** follow `skills/mine-my-context/SKILL.md`. It tells the person what you now know about them and their work, asks at most five short questions, and writes only what they confirm. It ends by running `python3 scripts/level1.py sync .`

**What you ask:** at most five short questions, as the skill says. Accept "skip". If it suggests more domains and they agree, add them the same way as in step 5.

**Save progress:** `python3 kit/progress.py . step 7`.

**If something fails:** if very little came in, say so plainly, ask the questions anyway, and suggest one more connection or export for later.

## 7. Skills (skills)

**What you do**

1. Say what a skill is, in one line: "A skill is a written recipe for a job you repeat, like a morning brief."
2. Show the skills in `skills/` (see `skills/SKILLS.md`), one plain line each.
3. Offer three that are made for every day: `morning-brief` (each morning: today's meetings and who is waiting on you), `weekly-review` (a look back at the week and ahead to the next) and `show-it-visually` (turns an answer into a polished page). If one of them is not in the brain's `skills/` folder but is in `kit/template/skills/`, offer to copy it in; with their yes, copy its folder and add it to the routing table in `AGENTS.md` and to `skills/SKILLS.md`.
4. From what you saw in steps 4 and 6, suggest at most two new skills for jobs they repeat. With their yes, write each as "Making a new skill" in `skills/SKILLS.md` says.

**What you ask:** which to keep, and whether they want the new ones. To drop a skill, with their yes, take its line out of the routing table in `AGENTS.md` and out of `skills/SKILLS.md`. Leave its folder: it does no harm.

**Save progress:** `python3 kit/progress.py . step 8`.

**If something fails:** none of this is needed for the brain to work. If anything goes wrong, keep the skills it came with and move on.

## 8. Scheduled jobs (schedule)

**What you do**

1. Suggest two jobs worth running on their own: the morning brief (weekdays at 8am) and the weekly review (Fridays at 4pm).
2. Where each runs: by default, in the app's own scheduler. Look up `schedulers` in `kit/connections.yaml` for the app you saved in step 1, say in one line how it works (from its `how`, for example that the app must stay open), and give its `clicks`, one step at a time. The instruction the job runs is one line, for example: "Follow skills/morning-brief/SKILL.md in my brain folder." (with the brain's full location).
3. If this app has no scheduler, or its screens do not match: offer the computer's own scheduler, only if an AI can run from this computer's terminal (for example Claude Code, Codex or OpenCode). With their yes, set it up yourself, show exactly what you added, and say how to remove it. Otherwise, the job runs by hand: "Each morning, open your brain in this app and say: morning brief."
4. Add one row for each job to the table in `automations/AUTOMATIONS.md`: the job, what it runs, how often, in which app, and today's date.

**What you ask:** which jobs, and when. Then the scheduler clicks, one at a time.

A scheduled job only reads and drafts. It never sends, posts or replies by itself.

**Save progress:** `python3 kit/progress.py . step 9`.

**If something fails:** if saving the job does not work, say so in one line, write it in `automations/AUTOMATIONS.md` as "run by hand", and move on.

## 9. The first real answer (done)

**What you do**

1. Ask what they would like to know first, or offer one: "What's on my plate this week?" Answer it with the matching skill, and name the file behind each point.
2. Offer: "Would you like that as a polished page?" With a yes, follow `skills/show-it-visually/SKILL.md`. (In the Claude app it appears as a page in the chat; elsewhere it is saved in the brain's `views` folder and opened.)
3. Say what to try tomorrow, in one line, for example: "Tomorrow morning, open your brain and say: morning brief."
4. Say, in a few lines, how to come back:
   - Next time: open the brain folder in your AI app. It reads level 1 by itself (`CLAUDE.md`, `GEMINI.md` or the top of `AGENTS.md`).
   - For each thing still on its way, the exact line to come back with, from `python3 kit/check_setup.py .`, for example: "When LinkedIn emails you, put the zip in your brain's exports folder, open the brain in your AI and say: add my LinkedIn."
   - To connect something new later: paste the same line again.

**Save progress:** `python3 kit/progress.py . done`

That is the setup. Stop there and wait for the person.

## Coming back later

When the person pastes the line again after setup is finished, `check_setup.py` says so on its first line. Ask what they would like: connect something new (step 3 for that one source, then step 4 for it), add a domain (step 5), or a new skill or scheduled job (steps 7 and 8). Save each change with `kit/progress.py` as above.

## Export steps

Use these when `connections.yaml` has no route for a source, or cannot be read. Files go in the brain's `exports` folder. If they land in Downloads, ask the person to drag them into `exports` (or, if your app asks to use Downloads, they can allow it once, for this chat).

**LinkedIn** (up to a day)
- Open https://www.linkedin.com/mypreferences/d/download-my-data (signed in to LinkedIn). Choose the larger archive and press **Request archive**.
- LinkedIn emails twice: a small file first, then the full one, usually within a day. Download the full zip when the second email comes (the link lasts 72 hours). Keep it zipped and put it in `exports`.
- Do not wait for it: save it as pending and carry on.

**WhatsApp** (on the phone)
- Pick three to ten chats where real work happens, not only the biggest.
- iPhone: open the chat, tap the name at the top, **Export Chat**, **Without Media**. Android: the three dots, **More**, **Export chat**, **Without media**.
- Send each file to the computer (for example by email to yourself) and put it in `exports`.
- If their phone blocks exports (some work phones do), skip it: calendar and LinkedIn are enough to start.

**Calendar**
- Google: https://takeout.google.com, press **Deselect all**, tick **Calendar**, then **Next step** and **Create export**. Apple Calendar on a Mac: **File**, **Export**, **Export...**. Outlook on the desktop: **File**, **Save Calendar**. Put the file in `exports`.

**Contacts and X**
- Contacts on a Mac: in Contacts, select all, then **File**, **Export**, **Export vCard**, into `exports`.
- X (Twitter): **Settings**, **Your account**, **Download an archive of your data**. It takes time: save it as pending and carry on.

**Anything else** (for example Notion or Slack): if your app has a connector for it, it is one sign-in in the app. If not, say plainly that the kit cannot bring it in yet.
