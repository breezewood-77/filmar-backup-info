# Bloat audit: skill fleet — 2026-09-13

Scope: the 42 skills synced to this session (`~/.claude/skills/synced/`).
Not covered: the Cowork vault, scheduled tasks, and scripts under
`C:\Users\Francis\Documents\Code`, which are not reachable from this session.
Run `tools/bloat_audit.py` against that path to complete the picture.

Method: `tools/bloat_audit.py`, plus a manual pass on the exclusion graph.
Every number below is measured, not estimated.

## Headline

| Signal | Measured | Read |
|---|---|---|
| Skills installed | 42 | |
| Always-loaded description text | 25,835 chars, ~6,458 tokens per turn | 29% over the 20,000 budget |
| Disambiguation collision lines | 85 | 2.1x the 40 budget |
| Skills naming another skill in their description | 27 of 42 | |
| Named components cited as owners but not installed | 15 | **the root cause** |
| Deprecated skills still installed | 1 (`trim-meeting`, retired 2026-08-09) | dead 35 days |
| Genuine content duplication between skills | 0 pairs | not a problem |

The token cost is real but small. The duplication is zero once vendored
helper scripts and licence boilerplate are excluded. The disease is routing.

## Finding 1 — the fleet routes against a namespace it cannot see

Fifteen named components are cited in skill descriptions as the owner of some
piece of work. None of them is an installed skill:

| Cited component | Cited by |
|---|---|
| `hourly-deal-reply-watch` | filmar-quote-sent, filmar-review, sales-inbox-triage |
| Command Center | build-a-system, plan-my-day, quick-visual, sales-inbox-triage |
| the 7:38 standup | plan-my-day |
| the 7:03 Daily Market Session | plan-my-day |
| the 9:08 Daily Sales Session | plan-my-day |
| Friday Work-Week Planning | plan-my-day |
| the Monday audit | error-scan |
| the Monday Filmar/GDR strategy session | leverage-audit |
| `daily-market-session` | diamond-finder |
| `scheduled-task-rotation-review` | meeting-review |
| the reply module | sales-inbox-triage |
| `production-calendar` (explicitly "not built yet") | filmar-sop |
| `build_spec_sheet.py` | filmar-configurator |
| `spec_library_inbox` | filmar-configurator |
| engineered-drawing track (Stage-2, "parked") | filmar-configurator |

Most are scheduled tasks, which legitimately live outside the skill directory.
That is the point: a skill has no way to name a task except in prose, so every
boundary between the two layers has to be re-explained in English, in every
skill that touches it. `plan-my-day` spends four separate exclusions saying
which of four scheduled sessions it is not.

This is what generates the 85 collision lines. It is not carelessness.

**Consequence:** collisions grow with (skills x tasks), not with skills. Adding
the capture system to this adds a new component that every existing Filmar
skill will eventually need an exclusion line against.

## Finding 2 — the Filmar cluster is one skill wearing six hats

Six skills whose descriptions exist largely to exclude each other:

    filmar-configurator   -> excludes draft-reply, build_spec_sheet.py, engineered track
    filmar-draft-reply    -> excludes quote-sent, call-summary, review, configurator
    filmar-quote-sent     -> excludes draft-reply, configurator, call-summary, review
    filmar-review         -> excludes quote-sent, call-summary, production-status, draft-reply, configurator
    filmar-call-summary   -> excludes review, draft-reply
    filmar-production-status -> excludes quoting, HubSpot writes, shipping emails

All six operate on the same objects: one client, one deal, one thread.
They differ only in which direction the information flows.

**Proposed merge:** one `filmar` skill with explicit modes, the pattern
`meeting-review` already proved when it absorbed `trim-meeting`:

    /filmar configure   (was filmar-configurator)
    /filmar reply       (was filmar-draft-reply)
    /filmar log         (was filmar-quote-sent)
    /filmar review      (was filmar-review)
    /filmar call        (was filmar-call-summary)
    /filmar production  (was filmar-production-status)

Modes cannot collide with each other, so roughly 20 exclusion lines
disappear by construction. No capability is lost.

## Finding 3 — the meta cluster is three skills deep on the same axis

    bearcase        one idea, stress-test
    council         one decision, three advisors
    leverage-audit  whole fleet, ranked

These three are genuinely different in scope, and each spends description
budget saying so. Lower priority than the Filmar cluster, but the same shape.
Same for `build-a-system` / `systematize` / `skill-builder`, which collectively
carry 16 collision lines.

## Finding 4 — dead weight

- `trim-meeting`: self-declared DEPRECATED on 2026-08-09, folded into
  `meeting-review`, still installed 35 days later. It still costs 292
  description chars every turn and still appears in the collision graph.
  Delete it.
- `filmar-sop` excludes a `production-calendar` skill that does not exist.
  Either build it or drop the exclusion.

## Finding 5 — what is NOT bloat

Worth stating so it does not get cut by mistake:

- **No genuine duplication.** The 25 duplicate pairs the script reports are
  all vendored helper scripts (`soffice.py`, `validate.py`, `pptx_*.py`)
  shared by the docx/pptx/xlsx skills, plus licence and font-licence files.
  That is correct packaging, not bloat.
- **No stale files.** Zero files untouched over 90 days.
- **Orphan files** are theme and example assets loaded by path at runtime,
  not dead code.
- **The 11 MB on disk** is almost entirely `canvas-design` fonts. Disk is free;
  ignore it.

## Reduction plan, ranked by collision lines removed per hour of work

| # | Action | Collisions removed | Effort |
|---|---|---|---|
| 1 | Delete `trim-meeting` | 1, plus 292 always-loaded chars | minutes |
| 2 | Merge 6 `filmar-*` into one moded `filmar` skill | ~20 | hours |
| 3 | Publish a component registry (see below) | ~15 | hours |
| 4 | Merge `build-a-system` + `systematize` | ~11 | hours |
| 5 | Trim the 7 descriptions over 900 chars to 600 | 0, but ~3,000 chars | an hour |

## The registry, which is the actual fix

One file listing every component in the system — skill, scheduled task,
script — with its name, layer, one-line job, and owner. Every skill's
description then points at registry names instead of re-explaining
boundaries in prose.

    name                      layer   job
    filmar                    skill   all client-facing Filmar work, by mode
    hourly-deal-reply-watch   task    sweeps inbox hourly, hands off to filmar
    build_spec_sheet.py       script  renders the spec-sheet PDF
    ...

Without this, collisions keep growing with (skills x tasks) no matter how
many merges are done. With it, a new component states its lane once.

## Verification of this audit

    python3 tools/bloat_audit.py ~/.claude/skills/synced/<id> --days 90

Reproduces every number in the headline table.
