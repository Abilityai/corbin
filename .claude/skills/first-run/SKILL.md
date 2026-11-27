---
name: first-run
description: Sets the agent up on first contact and proves it works in under two minutes - creates the person's private workspace, processes a short sample meeting without saving anything, checks whether the Company Brain is connected, tells the person the three things to try, and asks their name in its closing line without waiting for it. Needs no credentials. Safe to run again at any time.
allowed-tools: Read, Write, Bash, Glob, mcp__trinity__list_agents, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "[--verify-only]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# First run

The person has just met you. Show them, fast, that you work, and what to do next. No questions
mid-run, no credentials, nothing sent. Aim to finish in well under two minutes.

## Step 1: Create the workspace (idempotent)

```bash
mkdir -p workspace/{profile,commitments,meetings,email,notes/people,procedures,policies,briefs,ledger,memory}
for f in templates/profile/*.md; do [ -f "workspace/profile/$(basename "$f")" ] || cp "$f" workspace/profile/; done
[ -f workspace/procedures/index.md ] || printf '# Procedures\n\nHow this person wants recurring tasks done. One line per procedure: `slug` - when it applies.\n' > workspace/procedures/index.md
[ -f workspace/policies/policies.md ] || printf '# Standing rules\n\nOne rule per line, each with its date and source. Every playbook reads this file first.\n' > workspace/policies/policies.md
```

Never overwrite a file that exists: it is the person's. With `--verify-only`, create nothing and
only report what exists.

## Step 2: Prove the tools work

Run, and note each result in one word:

```bash
python3 scripts/extract_text.py --selftest
python3 scripts/inbox.py new
```

`inbox.py new` also tells you whether the person already dropped something.

## Step 3: Process the sample, without saving

Read `templates/sample/sample_meeting.txt` with `python3 scripts/extract_text.py`. Apply Steps 2
to 4 of `/process-transcript` to it **in memory only**: write nothing to `workspace/`, offer
nothing to the Company Brain. Keep the result to: two decisions, the action items (owner, what,
due as stated), the one open question, and the first two lines of a follow-up draft.

## Step 4: Check the Company Brain

Call `mcp__trinity__list_agents`. Note whether an agent named `cornelius` is listed. Do not call
it. The list shows only agents you have been given permission to call, so "not listed" means "not
connected to me yet", never "there is none". If the tool is not available (a local run), note
"not checked".

## Step 4b: Do you know who the person is?

Read `workspace/profile/about-me.md`. Note whether it holds a name (a line under `## Name and role`
that does not start with `Example:`). Do not ask now and do not wait.

## Step 5: Check the optional connections

Only whether each credential variable is set (`[ -n "$MAILBOX_READ_CREDENTIAL" ]`,
`[ -n "$CALENDAR_READ_CREDENTIAL" ]`). Never print a value. Not set is normal and not a problem.

## Step 6: Record and reply

Write `workspace/memory/first-run.json`: the time, each check's result. Record metrics as
CLAUDE.md, Run states, says: `last_run_state` = `done` (or `blocked` if Step 1 or 2 failed, naming
what), and `inbox_waiting` = the count from Step 2. Not knowing the person's name is not a reason
for `held`, and neither is a failed metrics call.

Reply, at most 16 lines:

1. One line: "I'm set up and working." (or what failed, plainly).
2. The sample result, compact, labelled "Here is what I do with a meeting (a sample, nothing saved):".
3. **Three things to try:**
   - "Drag a meeting transcript or your notes onto me and say *process this*."
   - "Drag an exported email (.eml, .txt or .pdf) onto me and say *draft a reply*."
   - "Tell me something you promised, like *I promised Ana the budget by Friday*, then ask *what do I owe?*"
4. One line on the Company Brain: listed ("I'll share what I learn with the Company Brain and ask
   it first.") or not listed ("The Company Brain isn't connected to me yet, so my notes stay here
   for now."). Not checked (a local run): leave the line out.
5. One line: "If you want, I can also read your email or calendar - ask *how do I connect my email?* It's optional."
6. If files are already waiting: "You've already dropped N files - say *catch up* and I'll process them."
7. Last line, only if the profile holds no name: "One thing: what's your name? Tell me any time
   (*I'm Sam*) so I know which items in a meeting are yours." It is a question, not a step - the
   run is already finished.

No paths, no tool names.
