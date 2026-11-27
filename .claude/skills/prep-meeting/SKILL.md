---
name: prep-meeting
description: Prepares the person for one meeting - who will be there, what the Company Brain and this agent's notes hold about each of them, the last contact, and what is open in either direction - each fact with its source. Works from what the person names when no calendar is connected. Sends nothing and looks nobody up on the web.
allowed-tools: Read, Write, Bash, Glob, Grep, mcp__trinity__chat_with_agent, mcp__trinity__report, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "<meeting or 'next'> [attendees]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Prepare a meeting

Walk into the meeting knowing who is there, where things stand and what to settle.

## Step 1: Find the meeting

- Calendar connected: `python3 scripts/calendar.py events --from <today> --days 7 --tz <tz>`; pick
  the event the person means (`next` = the next one with another attendee). None or several fit:
  name the candidates and stop (`held`).
- No calendar: use what the person named - title, time, attendees. No attendees given: ask for
  them in the reply and prepare what you can (`held`).

## Step 2: For each attendee (at most eight)

In this order, stopping when the picture is clear:

1. **The Company Brain**: `/ref-query <name or organisation>` as CLAUDE.md says. Not reachable:
   one line saying so, then go on.
2. **Your own record**: open lines with them in the commitments list (both directions), meeting
   notes and email notes in `workspace/` that name them, `workspace/notes/people/<name>.md`.
3. **The mailbox, if connected**: mail with their address in the last 90 days, newest first, at
   most 20, through `python3 scripts/mail.py list --folder any --filter-file <{"with": "<address>"}> --newest-first --max 20`.

A role or organisation no source states is "not on file", never guessed. Someone with no record
is "new to your records".

## Step 3: Write

`workspace/meetings/<YYYY-MM-DD>_<slug>_prep.md`: what could not be read; when, where, who;
per attendee - who they are (with source), last contact (date, subject, one line), what is open
each way; **To settle**: open lines and the agenda; **Worth asking**: two or three suggestions,
each marked as a suggestion. End with: "Afterwards, drop the transcript or tell me what was
agreed."

## Step 4: Close

Record `last_run_state`. Publish a report, `report_type` `chief_of_staff.meeting_prep`. Reply
with the two or three things that matter most and what is open each way.
