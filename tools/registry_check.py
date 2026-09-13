#!/usr/bin/env python3
"""Enforce the component registry.

Usage:  python3 registry_check.py <system_root> [--registry tools/registry.tsv]

A skill or task may only defer work to a component that exists in the
registry. This catches the failure mode that produced 85 disambiguation
lines in the 2026-09-13 audit: skills re-explaining, in prose, boundaries
against components they cannot name because those live in another layer.

Exit 1 on any unregistered citation, so it can gate a build.
"""
import os, re, sys, csv, glob, argparse

# "that is X", "X owns that", "(that's the X)" -- the phrasings the fleet
# actually uses to hand work to another component.
CITE = re.compile(
    r"(?:that is|that's|handled by|handed off to|hands off to|owned by)\s+"
    r"(?:the\s+)?[`/]?([A-Za-z][A-Za-z0-9_. /-]{2,44}?)[`]?"
    r"(?:\s+owns that)?(?=[,.;)\n]|\s+(?:skill|task|job|owns))",
    re.I)

# A citation only counts when the cited thing is shaped like a component
# name. Prose after "that is" is not a citation, and treating it as one is
# how a checker earns its way into being ignored.
NAMELIKE = [
    re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)+$"),            # hourly-deal-reply-watch
    re.compile(r"^[\w./-]+\.(?:py|sh|js|ps1)$"),              # build_spec_sheet.py
    re.compile(r"^/[a-z][a-z0-9-]+$"),                        # /council
    re.compile(r"^(?:\d{1,2}[:h]\d{2}\s+)?[A-Za-z][\w' ]*\b"
               r"(?:session|audit|standup|watch|module|review|planning|"
               r"center|centre|brief|sweep|ritual|track|inbox|log|calendar)$", re.I),
]


def namelike(s):
    s = s.strip()
    return any(p.match(s) for p in NAMELIKE)


def load_registry(path):
    names = {}
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if not row.get("name"):
                continue
            names[row["name"].strip().lower()] = row
            for al in (row.get("aliases") or "").split(";"):
                if al.strip():
                    names[al.strip().lower()] = row
    return names


def norm(s):
    s = s.strip().strip("/`").lower()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    s = re.sub(r"'s$", "", s)
    return re.sub(r"[\s_]+", "-", s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--registry", default=os.path.join("tools", "registry.tsv"))
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    a = ap.parse_args()

    reg = load_registry(a.registry)
    # A registry name matches loosely: hyphens, underscores and spaces are
    # equivalent, so "daily market session" resolves to daily-market-session.
    reg_norm = {norm(k): v for k, v in reg.items()}

    unresolved, checked = [], 0
    targets = glob.glob(os.path.join(a.root, "**", "SKILL.md"), recursive=True)
    targets += [p for p in glob.glob(os.path.join(a.root, "**", "*.md"), recursive=True)
                if re.search(r"task|meeting|session|watch", os.path.basename(p), re.I)]
    for p in sorted(set(targets)):
        checked += 1
        text = open(p, encoding="utf-8", errors="replace").read()
        me = norm(os.path.basename(os.path.dirname(p)))
        for raw in CITE.findall(text):
            if not namelike(raw) or len(raw.split()) > 6:
                continue
            n = norm(raw)
            if n == me or n in reg_norm:
                continue
            unresolved.append((os.path.relpath(p, a.root), raw.strip()))

    rows = {r["name"]: r for r in reg.values()}
    if not a.quiet:
        print(f"registry: {len(rows)} components "
              f"({len(reg) - len(rows)} aliases)")
        print(f"scanned:  {checked} files under {a.root}")
        stale = [r for r in rows.values()
                 if r.get("status", "").upper() in ("DEPRECATED", "NOT-BUILT")]
        for r in stale:
            print(f"  STATUS  {r['name']}: {r['status']} -- retire it or build it")
        unconf = [r for r in rows.values() if r.get("status", "").upper() == "UNCONFIRMED"]
        if unconf:
            print(f"  {len(unconf)} rows still UNCONFIRMED "
                  f"(job line taken from a citing skill, not from the component itself)")

    if unresolved:
        print(f"\nFAIL: {len(unresolved)} citations resolve to nothing in the registry")
        for f, raw in unresolved:
            print(f"  {f}: cites \"{raw}\"")
        print("\nAdd the component to the registry, or stop citing it.")
        return 1
    print("\nOK: every cited component resolves to a registry row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
