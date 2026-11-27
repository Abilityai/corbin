# Chief of Staff

A Chief of Staff agent for one person at a small company, built for
[Trinity](https://github.com/abilityai/trinity). Every new Trinity instance starts with it, next
to the [Company Brain](https://github.com/abilityai/cornelius).

It takes the administrative load off you:

- **Meetings.** Drop a transcript and get the decisions, the action items with owners and due
  dates, the open questions, and a follow-up email ready for you to send.
- **Email.** Drop an exported email and get what it needs from you, the promises in it, and a
  reply drafted in your tone.
- **Commitments.** One list of what you owe and what is owed to you, every line with its source.
  It tells you who has gone quiet and drafts the nudge.
- **A short morning brief** and **meeting preparation** from what is on record.
- **It learns how you work.** Tell it once how you handle something, or a rule you always follow,
  and it keeps it.

It never sends anything. Every email it writes is a draft for you to send.

## Try it in two minutes

No credentials are needed.

1. Open the agent in your Trinity Workspace and say **"get started"**. It sets itself up and
   shows you three things to try.
2. Drag a meeting transcript (.txt, .vtt, .docx, .pdf) onto it and say **"process this"**.
3. Drag an exported email (.eml, .txt or .pdf) onto it and say **"draft a reply"**.

## Playbooks

| Playbook | What it does |
|---|---|
| `/first-run` | Sets the agent up on first contact, proves it works on a sample, and shows what to try |
| `/process-transcript` | Turns a meeting transcript or notes into decisions, action items, open questions and a follow-up draft |
| `/triage-email` | Sorts an email by what it needs from you, records promises, drafts a reply where one is owed |
| `/daily-intake` | Processes everything you dropped since the last run, and new mail if a mailbox is connected |
| `/draft-reply` | Writes a reply in your tone for you to send |
| `/check-commitments` | Lists what you owe and what is owed to you, with follow-up drafts for what waited too long |
| `/follow-up-check` | Finds messages and meetings where you asked for something and got no answer |
| `/note-commitment` | Writes down a promise you made or were made, or marks one done, dropped or postponed |
| `/morning-brief` | A short brief: what is due, what came in, today's meetings if a calendar is connected |
| `/prep-meeting` | What is on record about the people in a meeting and what is open between you |
| `/save-procedure` | Saves how you want a recurring task done, so it is done that way next time |
| `/save-policy` | Saves a standing rule ("always...", "never...") that every playbook follows |
| `/connect` | Explains how to connect a mailbox or a calendar, if you want to (optional) |

## The Company Brain

When the agent named `cornelius` runs on the same instance, the Chief of Staff asks it first for
"what do we know about X", and offers it durable facts from your meetings and email (who someone
is, what was decided). The Brain decides what it keeps. Without it, the Chief of Staff keeps its
own notes and says so.

## Optional connections

| Credential | What it adds |
|---|---|
| `CALENDAR_READ_CREDENTIAL` | Your calendar's private iCalendar (.ics) feed address: meetings in the brief and in meeting preparation. A feed cannot be written to. |
| `MAILBOX_READ_CREDENTIAL` | A Google service-account key with read-only Gmail access (domain-wide delegation, `gmail.readonly` only): new mail is picked up without exporting it. Read only through `scripts/mail.py`, which acts as the one address you write in your profile. |

Ask the agent "how do I connect my email?" for the steps. For the mail script, install its two
libraries once: `python3 -m pip install -r requirements.txt`.

## Your data stays yours

Everything the agent writes about you and the people you work with lives in `workspace/`, and the
files you drop live in `inbox/` and `uploads/`. All three are ignored by git and never part of
this template, so updating the template never touches them, and the agent never commits or pushes.

## Layout

```
CLAUDE.md             how the agent works
template.yaml         Trinity metadata: resources, optional credentials, metrics, schedules (off)
dashboard.yaml        dashboard bound to the declared metrics
.claude/skills/       the playbooks
scripts/              extract_text.py (read a dropped file), inbox.py (what is new), mail.py (optional mailbox)
templates/profile/    the profile files copied into workspace/ on first run
```
