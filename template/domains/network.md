# Network

The people I know, and every conversation or meeting I have had with them.

## Files

| File | What it holds | Written by |
|---|---|---|
| `people.jsonl` | One line per person, merged across LinkedIn, WhatsApp, calendar, contacts and what my AI read through a connection | The importers; notes added with my say-so |
| `interactions.jsonl` | One line per message thread, LinkedIn message, meeting, or day we were in touch through a connection, oldest first | The importers |

A person line has a stable `id` (`person_<name>`), `name`, `emails`, `phones`, `company`, `position`, `url`, `source` (every import that knows them), `confidence`, and `from`: what each source said, word for word. `confidence` is medium when the only word on someone is a WhatsApp name, or when two sources were joined by name alone; check before relying on it. Notes you add (such as `notes` or `tags`) are kept when the importers run again.

An interaction line has `id`, `type`, `date`, `with` (who), `source`, `confidence`, and `title` and `file` when the full text is elsewhere in the brain. From an export file, `type` is `whatsapp`, `linkedin_message` or `meeting`. From what my AI read through a connection in its app (`importers/from_connector.py`), `type` is the channel it came through, for example `calendar`, `email`, `whatsapp`, `slack` or `meeting`; `source` ends in `-live` (for example `gmail-live`), the line may carry a `time`, and it adds two fields: `summary` (at most one short line, never the whole message) and `read_on` (the day it was read). A person seen through a connection has `read_on` in what that source said about them, under `from`.

## What goes in

- People I know or have met, and when and how we were in touch.
- Notes about a person I have asked to keep, each with its source.

## What stays out

- Anything about a person that did not come from my own exports or from me.
- People's home addresses, health or money details, even if a chat mentions them.

## What's here

- (Written by `mine-my-context`: who the key people are and any patterns, with source and confidence.)
