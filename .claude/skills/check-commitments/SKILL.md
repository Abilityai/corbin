---
name: check-commitments
description: Lists what the person owes others and what others owe the person, each with its source, date and days open, flags what is overdue or answered, and writes a follow-up draft for what has been owed to the person too long. Drafts are text only; nothing is sent and no line is closed without the person's word.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__trinity__report, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "[who]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Check commitments

A promise forgotten costs more than a promise kept late. Put every open one in front of the person.

## Step 1: Load

Read policies, procedures and `workspace/profile/preferences.md` (follow-up days; default 5
working days). Load `workspace/commitments/commitments.yaml`.

- Cannot be parsed: change nothing, state `blocked`, say which line.
- Items waiting in `workspace/commitments/pending.yaml` (`status: pending`) are not on the list
  yet because you do not know which attendee is the person. Say how many and from which sources,
  and end the reply with the question `/identify` defines ("Which of these is you: ...?"). If the
  person has already said who they are in this message, `/identify` runs first and they are placed.
- Missing or empty: say "Your list is empty - tell me a promise or drop a transcript and I'll
  start one." Never say "you owe nothing". State `held`.

## Step 2: Look for movement (only if a mailbox is connected)

For open lines with a `thread`, at most 30, oldest first: find later messages in that thread
with `python3 scripts/mail.py list --folder any --filter-file <file with {"thread": ...} or {"message_id": ...}>`.
Owed to the person and the other side wrote: `answered`. Owed by the person and a message of
theirs is in `sent`: `answered`. Add the evidence and a dated note. No mailbox: skip this in
silence, and use what the person told you.

## Step 3: The lists

Two tables, **You owe** and **Owed to you**: who, what, source and date, due, days open. Soonest
due first, then oldest. Mark overdue. "No date given" where `due` is blank. With `[who]`, only
lines with that party, and say the list was narrowed. Leave out lines with a future `not_before`
(count them). Then **Answered - please confirm**: lines set to `answered`, for the person to
close or reopen.

## Step 4: Follow-up drafts

For each open line owed to the person and silent longer than the follow-up days: one draft, as
`/draft-reply` Steps 3 and 4 say - to whom, what was asked and when ("my note of 3 March"), one
ask, nothing the line does not hold. Mark `Draft - not sent`. For what the person owes, write no
draft: list it; the wording is theirs.

## Step 5: Write and close

Write the changes of Step 2 only. Record metrics as CLAUDE.md, Run states, says: `last_run_state`, `i_owe_open`, `owed_to_me_open` (whole
list, not narrowed). Publish a report, `report_type` `chief_of_staff.commitments`.

Reply: counts each way, the overdue and soonest-due items, what looks answered, the drafts in
full, "Nothing was sent."
