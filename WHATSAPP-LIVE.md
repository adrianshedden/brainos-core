# Connect WhatsApp live (afternoon, if you want it)

For the AI. This is optional, and it is not part of setup. Setup (`SETUP.md`) only brings in a few chats the person exports from their phone. Use this guide only when the person asks for a live link to WhatsApp, after setup, for example in an afternoon build session.

Speak to the person as `SETUP.md` says: plain British English, short messages, one step at a time, button names in bold, wait for "done". Run every command from inside the brain folder. On Windows, type `py` instead of `python3`.

There are three parts, each with its own yes: reading (section 3), then sending (section 4), which needs a second yes. Section 5 switches it off and section 6 removes it.

## 1. Say the risks first

Before you install or change anything, send the person this, in a message of its own:

"Before we start, three things to know.
- WhatsApp has no official way to let an AI read your chats. This uses Beeper, a free app from another company. It links to your WhatsApp the same way WhatsApp on a computer does.
- WhatsApp can ban a number it thinks is automated. Reading is a small risk. Sending is a bigger one. If you are worried, use a number you can afford to lose access to, not the one your business runs on.
- What I read from your chats goes to my provider (for Claude, Anthropic), like anything else in our chat. Leave out client, medical and children's groups.
You can switch it off at any time, and remove it completely.
Do you want to go ahead? I won't install anything until you say yes."

Wait for a clear yes. Anything else, including silence or "maybe", is a no: stop, and remind them that exporting chats (setup step 3) carries no risk.

Do not go ahead on a work laptop if their company blocks extra apps, or on a work phone that blocks linked devices. Say so in one line and suggest the export instead.

## 2. What works where

Tell the person only the line that applies to them.

- **Reading** works on a Mac and on Windows, in the Claude app, Claude Code, the ChatGPT app (with Codex), Cursor, OpenCode and Orca.
- **Sending** works only in Claude Code (in a terminal, or in the Claude app's Code tab), on a Mac or on Windows. Only Claude Code lets the kit add a check before each message goes (the send guard). In the Claude app's chat, ChatGPT, Cursor and OpenCode it is reading only. Say so plainly if they ask.
- **Windows:** Beeper and Claude Code both run on Windows, but these steps have not yet been tried on Windows. If a screen looks different, stop, say what you see, and offer the export.
- **New messages do not arrive by themselves.** You read WhatsApp when the person asks. A set-up where new messages come in on their own (a "channel") is not in this kit.
- Beeper must stay open. When it is closed, nothing can be read or sent.

## 3. Reading (the first yes)

1. **Install Beeper and link WhatsApp.** Give the person these steps one at a time:
   - Go to beeper.com/download, install Beeper and open it. Make a free account with your email.
   - In Beeper, add WhatsApp. On your phone, open WhatsApp, then **Settings** (iPhone) or the three dots (Android), then **Linked devices**, then **Link a device**. Scan the code on the screen. Keep the phone close while your chats load.
   - In Beeper, open **Settings**, then **Integrations**, and check the **Desktop API** is on (the switch that lets apps read Beeper).
2. **Connect your AI to Beeper.** Use the `whatsapp` route for this app in `kit/connections.yaml` (type `local`). Give its clicks as usual. Pick read-only wherever it is offered. When the app asks to use a Beeper tool, allow the search and read ones, and always deny sending (`send_message`). For Claude Code, the route's notes give the line that adds the connection; say what it adds and run it only after a yes.
3. **Claude Code only: turn on the read-only guard.** First show what would change, then ask:
   - `python3 kit/whatsapp_live.py . read` shows the changes and changes nothing. Tell the person in one or two lines: "This adds a check to Claude Code's own settings, outside your brain folder. It lets me read WhatsApp and refuses any send. Shall I add it?"
   - With their yes: `python3 kit/whatsapp_live.py . read --apply`. It saves a copy of the settings first. Then ask them to quit Claude Code and open it again.
4. **Check it works:** list the names of the 3 most recent chats. Do not open, send or mark anything. Say in one line what you saw.
5. **Save it:** `python3 kit/progress.py . connected whatsapp local`, and add a line to `tools/TOOLS.md`: "WhatsApp, live through Beeper: reading only, since <date>."

How to read, from now on: only the chats the person names, and only what the question needs. Keep who and when in the brain, as `SETUP.md` step 4 says. Never copy whole chats into the brain.

## 4. Sending (a second yes, Claude Code only)

Only when the person asks to send messages from their AI, and only after reading works.

1. Say this, then wait for a clear yes:
   "Sending is a separate step. Every message is a draft you approve. I write it here first. When you say send, Claude Code shows you the chat and the exact words, and nothing goes until you click yes. There is a limit of 20 a day. Sending carries more risk of a ban than reading. Shall I set it up?"
2. Show the changes: `python3 kit/whatsapp_live.py . write`. With their yes: `python3 kit/whatsapp_live.py . write --apply`. Then ask them to quit Claude Code and open it again.
3. Update the line in `tools/TOOLS.md`: "reading, and sending with your yes for each message".

How to send, every time:

- Write the message in the chat first, and name the chat it goes to. Wait for the person to say "send" (or to change it).
- Then send it. Claude Code shows them the chat and the words and asks. That question appears even if Claude Code is set to skip other questions.
- One message per yes. Only to the chat the person named. Never send to someone they did not name, never send in a group they did not pick, and never reply on your own.
- If the guard refuses (for example the daily limit), say so in one line. Do not try another way to send.

## 5. Switch it off

Any time the person says stop, or switch it off:

- Claude Code: show `python3 kit/whatsapp_live.py . off`, then, with their yes, run `python3 kit/whatsapp_live.py . off --apply`. After a restart, no WhatsApp tool can be used at all. To turn reading back on later: `read --apply`.
- Other apps: switch the Beeper connection off in the app's own settings (the same place it was added).
- Quickest of all: quit Beeper. Nothing can be read or sent while it is closed.

Update the line in `tools/TOOLS.md` to say it is off.

## 6. Remove it completely

Give these one at a time, and wait for "done" after each.

1. On the phone: open WhatsApp, then **Settings** (iPhone) or the three dots (Android), then **Linked devices**. Tap Beeper, then **Log out**. From this moment nothing can read your WhatsApp.
2. Take the connection out of your AI app:
   - Claude Code: run `claude mcp remove beeper -s user`, with their yes. Then `python3 kit/whatsapp_live.py . remove --apply`, which takes out the guard and its rules.
   - The Claude app: **Settings**, then **Extensions**. Find Beeper and uninstall it.
   - ChatGPT (Codex), Cursor, OpenCode or Orca: with their yes, take out the beeper entry you added to the app's own settings.
3. Uninstall Beeper. Mac: drag Beeper from Applications to the Bin. Windows: **Settings**, **Apps**, find Beeper, **Uninstall**.
4. Take the line out of `tools/TOOLS.md`.

What stays: anything already in the brain (who and when), and any chats they exported. Those are their own files.
