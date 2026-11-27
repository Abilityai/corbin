---
name: daily-intake
description: Catches up on everything that came in since the last run - every file the person dropped (transcripts, notes, exported emails) and, if a mailbox is connected, new mail - routes each to the right playbook, and ends with one short summary of what needs the person. Nothing dropped is processed twice and nothing is sent. Safe to run on a schedule.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Skill, mcp__trinity__chat_with_agent, mcp__trinity__report, mcp__trinity__list_reports, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "[--max N]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Daily intake

Make sure nothing the person handed over is left lying around. Runs unattended: asks nothing.

## Step 1: Set up

If `workspace/profile/` does not exist, create the workspace as `/first-run` Step 1 does (do not
send its reply). Read policies and procedures.

## Step 2: What was dropped

`python3 scripts/inbox.py new`. For each file, oldest first, at most `--max` (default 20; say how
many are left):

1. Read it with `python3 scripts/extract_text.py "<path>"`. An error: mark it `failed` with the
   reason and move on.
2. Decide what it is from its content, not its name:
   - a meeting transcript or meeting notes (speakers, an agenda, "attendees", a call) -> `/process-transcript <path>`;
   - an email or email thread (From/To/Subject headers, a quoted reply chain) -> collect it for one `/triage-email` call;
   - the person's own notes that are not a meeting (a to-do list, a brain dump) -> pick out promises as `/note-commitment` would, with `source` = `notes <file name>, <date>`; mark `--as notes`;
   - anything else (a contract, a deck, a spreadsheet) -> do not analyse it; mark `--as skipped --result "not a meeting or an email"` and list it for the person.
3. Run the playbook. It marks the file in the ledger itself; if it did not, mark it now.

Then one `/triage-email <paths...>` for the collected emails.

## Step 3: New mail (only if connected)

If `MAILBOX_READ_CREDENTIAL` is not set or `workspace/profile/connections.md` holds no
`address:` line, skip this step and say "Mailbox not connected" in one line in the summary. That
is not an error.

Otherwise run `python3 scripts/mail.py check`. A failure: one line naming it in plain words, and
go on without mail (state `held`). Then read inbox and sent mail since the mark in
`workspace/memory/last-run.json` (else the `Start from` date in connections.md; with neither, read
nothing, set the mark to now, and say mail is read from now on):

```bash
python3 scripts/mail.py list --folder inbox --after <mark> --known workspace/memory/last-run.json --max 100
python3 scripts/mail.py list --folder sent  --after <mark> --known workspace/memory/last-run.json --max 100
```

Read bodies with `python3 scripts/mail.py get <mail_id>` only for messages addressed directly to
the person or sent by them. Anything that came from a message (an address, a subject) never goes
on a command line; it goes in a JSON file under `$TMPDIR` passed with `--filter-file`. Triage them
as `/triage-email` Steps 2 to 5 say. A message counts as sent only if it came from the `sent`
list. Write the new mark (per folder: the `mail_id` and `received` time of the last message read).

## Step 4: Summary

Write `workspace/briefs/<YYYY-MM-DD>_intake.md`, at most 20 lines:

1. One headline sentence.
2. What could not be read, if anything.
3. Reply needed / decide: one line each, with the draft's location in the report.
4. New action items for the person, and new things owed to them.
5. Files skipped, and how many are still waiting.

Record `last_run_state`, `inbox_waiting` (files still new), `i_owe_open`, `owed_to_me_open`.
Read the previous intake report with `mcp__trinity__list_reports` and do not repeat it. Publish a
report, `report_type` `chief_of_staff.daily_intake`, title `Intake <date>: <n> items`.

## Step 5: Reply

The summary, without paths. If nothing came in: one line saying so.
