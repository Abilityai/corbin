---
name: save-policy
description: Saves a standing rule the person states - always, never, prefer - with its date and source, in the one policies file every playbook reads before it starts. Use when the person says "always...", "never...", "remember that I prefer...", or corrects the same thing twice. A rule can narrow what the agent does, never widen it.
allowed-tools: Read, Write, Edit, Glob, Grep, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "<the rule, in the person's words>"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Save a policy

When the person corrects you, the correction should hold from then on.

## Step 1: Shape the rule

One line, imperative, in the person's terms, specific enough to check: "Never schedule anything
before 10:00 on Mondays in a draft", not "respect my mornings". Note the scope if it has one
(drafts, briefs, a named person or organisation).

If you noticed the same correction twice in this conversation without being asked, propose the
rule and save it only when the person agrees.

## Step 2: Check it

- A rule that would widen what you do (send, pay, post, delete, read someone else's mail) is not
  saved: say in one sentence that it is outside what you can do, and offer the nearest thing you
  can (prepare it for them).
- A rule about tone only belongs in `workspace/profile/tone.md`; a rule about a recurring task's
  steps belongs in a procedure (`/save-procedure`). Say so and put it there.
- A rule that contradicts an existing one: show both and ask which stands; save nothing yet.

## Step 3: Write

Append to `workspace/policies/policies.md`:

`- <rule> (<scope>; <date>; source: <"the person, in chat" | the file or message>)`

To change or remove a rule on the person's word, edit that line and add a dated note at the end
of it; never silently drop one. Read the file back.

## Step 4: Reply

One line: the rule as saved. Record `last_run_state`.
