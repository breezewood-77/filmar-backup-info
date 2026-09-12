# System hygiene rules

Four rules. They are enforceable by the audit script in this folder, which is
the point: a rule nothing measures is a rule nothing follows.

## 1. Admission gate — one in, one out
No new skill, scheduled task or script is added until one of these is true:
- it replaces a named existing component (say which, and retire that one), or
- the audit shows no existing component within 25% text overlap of it.
A new component that needs a "Do NOT use for X" line to explain itself is a
sign that X should have absorbed it instead.

## 2. Budget, not appetite
Hard caps, checked monthly by `bloat_audit.py`:
- always-loaded description text: **20,000 chars** total across all skills
- per-skill description: **600 chars**
- disambiguation collision lines: **40** fleet-wide
Over budget means the next build is a merge, not an addition.

## 3. Expiry date on every component
Every skill, task and script carries `last_reviewed:` in its frontmatter.
Anything unreviewed for 90 days and unreferenced by any other file is a
delete candidate at the next audit. Default is delete; keeping it requires
a one-line reason written into the file.

## 4. Measure before you build, measure after
Run `bloat_audit.py` before adding anything and after any build session.
Two numbers go in the log: always-loaded tokens, and collision lines. If a
build session raised either without retiring something, it added bloat.

## Monthly run
    python3 tools/bloat_audit.py /path/to/vault --days 90
    python3 tools/bloat_audit.py /path/to/vault --days 90 --json > audit-$(date +%F).json

Diff this month's JSON against last month's. Growth in [1] and [3] with no
matching retirement is the only bloat signal that matters.
