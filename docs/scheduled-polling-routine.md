# Setting up an hourly polling Routine

## Why this exists

`.github/workflows/log-and-plot.yml` has a `*/5 * * * *` schedule trigger,
but as of 2026-09-20/21 it has never actually fired on `main` — every run in
the workflow's history has been `workflow_dispatch` (manual/API-triggered),
never `schedule`. This is a known GitHub Actions limitation: scheduled
workflows run on a shared, best-effort queue and can be delayed or dropped
entirely, especially on repos with light activity.

This Routine is a stopgap: it calls the workflow's `workflow_dispatch`
trigger on a fixed schedule from outside GitHub, so the device keeps getting
polled even while the native cron stays silent.

A prior attempt used a **session-scoped** `CronCreate` job for a tighter
10-minute cadence, backed by an hourly Routine that re-created it whenever
it disappeared. That session-scoped job kept dying (every model switch and
every MCP reconnect wiped it), so in practice the watchdog's hourly firing
was the only reliable part of that setup. This Routine replaces the whole
thing with one durable, hourly job and drops the fragile 10-minute layer.

## What a Routine is

A Routine is a scheduled trigger stored server-side on your Anthropic
account — not inside any particular chat session. It keeps firing on its
own schedule independent of whether a session is open, a model has been
switched, or an MCP server has reconnected. That's the property the
session-scoped cron job didn't have.

## How to create it

**Option A — ask Claude to do it** (fastest): open a Claude Code session
with access to this repo and say:

> Create an hourly Routine that triggers the "log-and-plot.yml" GitHub
> Actions workflow on camsonne/Ecoflow2logger's main branch via
> workflow_dispatch, as a stopgap while the native */5 schedule trigger
> isn't firing.

**Option B — set it up yourself** via the Routines UI on claude.ai, using
these settings:

- **Name:** `Poll EcoFlow logger workflow (hourly)`
- **Schedule:** hourly — cron `0 * * * *` (the platform anchors this to the
  creation minute, so runs won't all land on the same clock minute as every
  other hourly job on the platform)
- **Prompt:**
  ```
  Trigger the GitHub Actions workflow "log-and-plot.yml" on
  camsonne/Ecoflow2logger's main branch via workflow_dispatch
  (mcp__github__actions_run_trigger, method="run_workflow",
  owner="camsonne", repo="Ecoflow2logger", workflow_id="log-and-plot.yml",
  ref="main"). This is a stopgap poll while GitHub's own */5 cron schedule
  hasn't reliably self-triggered. Fire it silently — do not message the
  user unless the trigger call fails, or unless a run with event="schedule"
  has appeared in the workflow run history (check via
  mcp__github__actions_list, method="list_workflow_runs"), in which case
  tell the user the native cron is now confirmed working and ask whether
  they'd like this Routine disabled.
  ```
- **Mode:** either fire into a fresh session each time, or bind to an
  existing session — a fresh session is simpler here since the task is
  self-contained and doesn't need prior conversation context.

## Known platform limit

Routines have a **1-hour minimum interval**. A cron expression asking for
anything more frequent (e.g. every 10 minutes) is rejected outright. Hourly
is the tightest cadence this mechanism can provide — it cannot substitute
for a genuinely working 5-minute native schedule trigger.

## When to retire this

Once a run with `event: "schedule"` shows up in the Actions run history for
`log-and-plot.yml` on `main` (check via the Actions tab, or
`gh run list --workflow=log-and-plot.yml --json event,headBranch`), the
native cron is working and this Routine is no longer needed. Disable or
delete it from the Routines list at that point.
