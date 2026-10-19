# Connect WhatsApp live (afternoon, if you want it)

**Tell your AI:** Connect my WhatsApp using WHATSAPP-LIVE.md from the BrainOS kit at github.com/adrianshedden/brainos-core.

For the AI, when the person sends that line: read this whole guide first, then follow it from section 1. Say the risks and wait for a clear yes before you install or change anything. Work in their brain folder (`SETUP.md` step 1 says how to find it); its `kit` folder holds the scripts named below. If they have no brain yet, offer to set one up first with `SETUP.md`.

For the AI. Optional, and not part of setup: setup only brings in chats the person exports from their phone. Use this only when the person asks for a live link to WhatsApp after setup, for example in an afternoon build session. Speak as `SETUP.md` says: plain words, one step at a time, wait for "done". Run commands from inside the brain folder; on Windows, type `py` instead of `python3`.

## 1. The risks, and a yes

Before you install or change anything, send this in a message of its own:

"Before we start, three things to know.
- WhatsApp has no official way to let an AI read your chats. Both ways of doing it link to your WhatsApp the same way WhatsApp on a computer does.
- WhatsApp can ban a number it thinks is automated. Reading is a small risk. Sending is a bigger one. If you are worried, use a number you can afford to lose access to, not the one your business runs on.
- What I read from your chats goes to my provider (for Claude, Anthropic), like anything else in our chat. Leave out client, medical and children's groups.
It's up to you whether to try it. You can switch it off at any time, and remove it completely.
Do you want to go ahead? I won't install anything until you say yes."

Wait for a clear yes. Anything else is a no: stop, and remind them that exporting chats carries no risk.

## 2. Pick a route

- **Quick route: wacli.** A small free program (github.com/openclaw/wacli) that links to WhatsApp and keeps a copy of your chats on your computer. About ten minutes. Mac (macOS 15 or newer) and Windows. Works with Claude Code (in a terminal), Codex, OpenCode and Orca: the AI runs it for you. Not in the Claude app's chat.
- **Sustainable route: Beeper.** A free chat app (beeper.com) that holds WhatsApp beside your other chats and lets your AI apps read it. Longer to set up, and the better choice to keep. Mac and Windows. Works in every AI app the kit supports.

Sending, with a yes for each message, works only in Claude Code, on either route. Only Claude Code lets the kit add a check before each message goes (the send guard). Everywhere else, it is reading only. The Windows steps have not yet been tried: if a screen looks different, stop and offer the export. New messages do not arrive by themselves on either route: you read WhatsApp when the person asks.

## 3. Read

**Quick route (wacli):**
1. The person installs it. Mac: in Terminal, `brew install openclaw/tap/wacli` (needs Homebrew). Windows, or a Mac without Homebrew: download the file for their computer from github.com/openclaw/wacli/releases, unzip it, and put `wacli` where the AI can run it.
2. The person links it, in their own terminal: `wacli auth`. On the phone: WhatsApp, **Settings** (iPhone) or the three dots (Android), **Linked devices**, **Link a device**, and scan the code in the terminal. It then copies recent chats.
3. Read only with `--read-only`, for example `wacli --read-only --json chats list` or `wacli --read-only --json messages search "invoice"`. To bring the copy up to date: `wacli sync --once`.

**Sustainable route (Beeper):**
1. beeper.com/download: install Beeper, open it and make a free account. Add WhatsApp and scan the code from the phone's **Linked devices** screen. In Beeper, **Settings**, **Integrations**: check the **Desktop API** is on (the switch that lets apps read Beeper).
2. Connect your AI to Beeper with the `whatsapp` route for this app in `kit/connections.yaml` (type `local`). Allow the search and read tools; always deny sending.

**Then, in Claude Code (either route):** show `python3 kit/whatsapp_live.py . read`, which changes nothing. Say: "This adds a check to Claude Code's own settings, outside your brain folder. It lets me read WhatsApp and refuses any send. Shall I add it?" With a yes: `python3 kit/whatsapp_live.py . read --apply`, then ask them to restart Claude Code.

Check it works: list the names of the 3 most recent chats, and nothing else. Save it: `python3 kit/progress.py . connected whatsapp local` (or `cli` for wacli), and a line in `tools/TOOLS.md`: "WhatsApp, live (wacli or Beeper): reading only, since <date>." Read only the chats the person names. Keep who and when, never whole chats.

## 4. Send (a second yes, Claude Code only)

Only when they ask, after reading works. Say: "Sending is a separate yes. Every message is a draft you approve: I write it here, and when you say send, Claude Code shows you the chat and the exact words. Nothing goes until you click yes. At most 20 a day. Sending carries more risk of a ban than reading. Shall I set it up?" Wait for a clear yes, then show `python3 kit/whatsapp_live.py . write` and, with their yes, run `python3 kit/whatsapp_live.py . write --apply` and restart Claude Code.

Every time: write the message in the chat first and name the chat. Send only when they say "send". One message per yes, only to the chat they named, never on your own. With wacli, send only with `wacli send text --to "<chat>" --message "<words>"`. If the guard refuses, say so in one line and do not try another way.

## 5. Switch it off or remove it

- **Off:** `python3 kit/whatsapp_live.py . off --apply` (after showing it without `--apply`): Claude Code can then use neither route. Or quit Beeper, or stop asking the AI to run wacli.
- **Remove completely**, one step at a time:
  1. Phone: WhatsApp, **Linked devices**, tap wacli or Beeper, **Log out**. From then on nothing can read your WhatsApp.
  2. wacli: delete the program, and its copy of your chats (the `.wacli` folder in your home folder). Beeper: Mac, drag it from Applications to the Bin; Windows, **Settings**, **Apps**, Beeper, **Uninstall**. Take the Beeper connection out of the AI app (Claude Code: `claude mcp remove beeper -s user`, with a yes).
  3. Claude Code: `python3 kit/whatsapp_live.py . remove --apply`, which takes out the guard and its rules.
  4. Take the line out of `tools/TOOLS.md`.

## How does it work on an always-on server?

Some people run WhatsApp on a computer that never switches off. That uses WAHA, a ready-made WhatsApp Web server: it links like WhatsApp on a computer, and a small program passes messages between it and the AI. The same risks apply. It is not part of this kit.
