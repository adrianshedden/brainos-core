# Network

The people I know, and every conversation or meeting I have had with them.

## Files

| File | What it holds | Written by |
|---|---|---|
| `people.jsonl` | One line per person, merged across LinkedIn, WhatsApp, calendar and contacts | The importers; notes added with my say-so |
| `interactions.jsonl` | One line per message thread, LinkedIn message or meeting with someone, oldest first | The importers |

A person line has a stable `id` (`person_<name>`), `name`, `emails`, `phones`, `company`, `position`, `url`, `source` (every import that knows them), `confidence`, and `from`: what each source said, word for word. `confidence` is medium when the only word on someone is a WhatsApp name, or when two sources were joined by name alone; check before relying on it. Notes you add (such as `notes` or `tags`) are kept when the importers run again.

An interaction line has `id`, `type` (`whatsapp`, `linkedin_message` or `meeting`), `date`, `with` (who), `title`, `source`, `confidence`, and `file` when the full text is elsewhere in the brain.

## What goes in

- People I know or have met, and when and how we were in touch.
- Notes about a person I have asked to keep, each with its source.

## What stays out

- Anything about a person that did not come from my own exports or from me.
- People's home addresses, health or money details, even if a chat mentions them.

## What's here

- (Written by `mine-my-context`: who the key people are and any patterns, with source and confidence.)
