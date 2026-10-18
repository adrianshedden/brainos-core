# BrainOS setup, kit version 1.0

For the AI. The person pasted one instruction asking you to set up their BrainOS from this kit. Follow these steps in order. Each step says when to stop and wait for the person.

How to work, the whole way through:

- Plain English and British spelling. Short messages. One question at a time, unless a step says to ask two together.
- Ask before you create anything. Change files only inside the brain folder the person chooses (and your own scratch space, if your app has one). Never delete anything.
- Never send, upload or post the person's files anywhere. The kit's scripts never use the internet.
- Show each command before you run it, and say in one line what it does. Your app may also ask the person to approve it: that is normal.
- Never block the setup on something slow. If an export is still on its way, carry on with the rest and tell the person how to add it later.

## 1. Check you can do this here

You need to open and change a folder on the person's computer and run Python 3 (`python3 --version`; on Windows `py --version` also works).

- If you cannot reach folders on their computer (for example ChatGPT chat, the Gemini web app, or any phone app), stop and say, in one or two lines: "I can't work on folders on your computer from here. Open the Claude app, the ChatGPT desktop app (Codex), Google's Antigravity or Cursor on your computer, and paste the same instruction there."
- If Python 3 is missing, say so in one line and offer to walk them through installing it from python.org. Do not install anything without their yes.

## 2. Ask where the brain should live, then build it

Ask, in one message:

"What shall we call your brain, and where should it live: Desktop, Documents, or somewhere else? If you're not sure, I'll make a folder called brain in your Documents. I'll create it once you say."

Wait for the answer. Then:

1. Work out the full path (for example `~/Documents/brain`). If you cannot reach that place, tell them how to let you: in the Claude app, start a new chat with **Project or folder** and choose the place (Desktop or Documents); in Codex, Antigravity or Cursor, open that place as the folder to work in. Then carry on.
2. If that folder is already a brain (it has a `brain.yaml`), do not build it again: put the kit back in its `kit` folder if it is missing (point 3), then go to step 3. If it holds other files, do not touch it: ask for another name.
3. Make the empty folder. Download this kit into a folder called `kit` inside it, at the version named in the person's instruction. Either `git clone --depth 1 --branch <version> https://github.com/adrianshedden/remyn-core kit`, or download the zip of that version from GitHub and unpack its contents into `kit`. If you cannot download, ask the person to download the kit's zip from GitHub and drag the unpacked folder into the brain folder, named `kit`.
4. From inside the brain folder, build the brain with the network and work areas: `python3 kit/create_brain.py . --domains network,work`. Say once that more areas (family, health, finance, knowledge) can be added later.
5. Check the three front doors match: `python3 scripts/level1.py check .` It should say level 1 is the same in `CLAUDE.md`, `GEMINI.md` and the top of `AGENTS.md`.
6. Read level 1 (your front door) and the level 2 manual in `AGENTS.md`. From now on, follow them.
7. Tell the person, in two lines: where the brain is, and that it is a plain folder of text files they can open any time.

## 3. Ask what to connect first

Send this list, most popular first, and ask them to pick any (numbers are fine), or "none for now":

1. **Email (Gmail or Outlook)**: who you write to, and who is waiting on you.
2. **Calendar (Google, Outlook or Apple)**: who you meet and how often, which shows your real priorities.
3. **LinkedIn**: everyone you know at work, and your career story. LinkedIn takes up to a day to send it, so start it first.
4. **WhatsApp**: where a lot of real work talk happens, and how you sound when you write.
5. **Google Drive**: what you are working on, in your own documents.
6. **Something else**: for example your contacts, X (Twitter) or Notion. Name it and I'll say how.

Wait for the answer. Give steps only for what they picked. Never list steps for the others.

## 4. Steps for what they picked, slow ones first

Work through the picks in this order: LinkedIn, WhatsApp, then the rest. One source at a time: give the steps, wait until they say it is done or "skip", then go on. Export files go in the brain's `exports` folder. If they land in Downloads, ask the person to drag them into `exports` (or, if your app asks to use Downloads, they can allow it once, for this chat).

**LinkedIn** (export, up to a day)
- Open https://www.linkedin.com/mypreferences/d/download-my-data (signed in to LinkedIn). Choose the larger archive and press **Request archive**.
- LinkedIn emails twice: a small file first, then the full one, usually within a day. Download the full zip when the second email comes (the link lasts 72 hours). Keep it zipped and put it in `exports`.
- Do not wait for it. Say: "That's started. We'll carry on, and you can add it when it arrives." Go on.

**WhatsApp** (export, on the phone)
- Pick three to ten chats where real work happens, not just the biggest.
- iPhone: open the chat, tap the name at the top, **Export Chat**, **Without Media**. Android: the three dots, **More**, **Export chat**, **Without media**.
- Send each file to the computer (for example by email to yourself) and put it in `exports`.
- If their phone blocks exports (some work phones do), skip it: calendar and LinkedIn are enough to start.

**Calendar**
- If your app has a calendar connection (the Claude app: **Customize**, then **Connectors**; the ChatGPT app: **Settings**, then **Apps**), ask them to switch on Google Calendar or Outlook Calendar there and sign in. It is one sign-in, done in the app, never in the brain. Ask them to allow read-only access if offered.
- Otherwise, an export file: Google at https://takeout.google.com (press **Deselect all**, tick **Calendar**, then **Next step** and **Create export**); Apple Calendar on a Mac: **File**, **Export**, **Export...**; Outlook on the desktop: **File**, **Save Calendar**. Put the file in `exports`.

**Email**
- Only through your app's own connection: the Claude app (**Customize**, **Connectors**, Gmail, or Microsoft 365 for Outlook) or the ChatGPT app (**Settings**, **Apps**, Gmail or Outlook). One sign-in.
- If your app has no email connection (for example Antigravity or Cursor), say so in one line and offer the calendar instead. There is no email export to import.

**Google Drive**
- Only through your app's own connection (the Claude app: **Customize**, **Connectors**, Google Drive; the ChatGPT app: **Settings**, **Apps**, Google Drive). One sign-in. If your app has none, say so and skip it.

**Something else**
- Contacts on a Mac: in Contacts, select all, then **File**, **Export**, **Export vCard**, into `exports`.
- X (Twitter): **Settings**, **Your account**, **Download an archive of your data**. It also takes time: carry on, add it later.
- Anything else (for example Notion or Slack): check whether your app has a connection for it. If it does, it is one sign-in in the app. If not, say plainly that the kit cannot bring it in yet.

## 5. Bring in what is ready now

1. Tell the person once where their data goes, in the words under "Where the data goes" in `kit/INSTRUCTIONS.md`. Then go ahead.
2. Run `python3 kit/check_setup.py .` It lists the export files in `exports` and the exact line to run for each. Run them. Before the first WhatsApp import, ask once for their own name as it shows in their chats.
3. Each connection they switched on: add its line to `tools/TOOLS.md` and tell them in one line. Use it to answer their questions. Do not copy whole mailboxes, calendars or drives into the brain. With their yes, add the people they deal with most (up to 20) to the people list named in `AGENTS.md`, each with `"source": "<connection>, <date>"` and `"confidence": "medium"`.
4. Say what came in, in plain numbers: people, messages, meetings, and anything skipped.

## 6. Get to know them, then answer one real question

1. Follow `skills/mine-my-context/SKILL.md`: at most five short questions; write only what they confirm. It ends by running `python3 scripts/level1.py sync .`
2. Ask what they would like to know first, or offer one: "What's on my plate this week?" Answer it with the matching skill, and name the file behind each point.

## 7. Finish with a clear way back

Say, in a few lines:

- Next time: open the brain folder in your AI app. It reads level 1 by itself (`CLAUDE.md`, `GEMINI.md` or the top of `AGENTS.md`).
- For each export still on its way, the exact line to come back with, for example: "When LinkedIn emails you, put the zip in your brain's exports folder, open the brain in your AI and say: add my LinkedIn." Or: "When your WhatsApp exports are in exports, say: add my WhatsApp."
- To keep it fresh: new exports into `exports`, then "import my new exports".

That is the setup. Stop there and wait for the person.
