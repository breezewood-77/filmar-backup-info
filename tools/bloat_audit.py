#!/usr/bin/env python3
"""Bloat audit for a Cowork-style system (skills, scheduled tasks, scripts, docs).

Usage:  python3 bloat_audit.py /path/to/vault [--days 90]

Read-only. Writes nothing. Prints six sections, worst first.
Every number is measured from the files, never estimated.
"""
import os, re, sys, time, json, hashlib, argparse
from collections import defaultdict

TEXT_EXT = {".md", ".txt", ".py", ".sh", ".json", ".tsv", ".csv", ".yaml", ".yml", ".js"}
SKIP_DIR = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache", "dist", "build"}
# Boilerplate that is duplicated by design and must never count as bloat.
NOISE = re.compile(r"(LICENSE|COPYING|-OFL|NOTICE)", re.I)


def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIR and not d.startswith(".")]
        for fn in fns:
            p = os.path.join(dp, fn)
            if os.path.splitext(fn)[1].lower() in TEXT_EXT and not NOISE.search(fn):
                try:
                    yield p, open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def desc_of(text):
    fm = frontmatter(text)
    m = re.search(r"description:\s*(.*?)(?=\n[A-Za-z_-]+:\s|\Z)", fm, re.S)
    return m.group(1).strip() if m else ""


def shingles(text, n=9):
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {hashlib.blake2b(" ".join(w[i:i + n]).encode(), digest_size=8).digest()
            for i in range(max(0, len(w) - n + 1))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--days", type=int, default=90, help="staleness threshold")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    files = dict(walk(a.root))
    if not files:
        sys.exit(f"no text files found under {a.root}")

    now = time.time()
    stale_cut = now - a.days * 86400
    skills, tasks, scripts, docs = {}, {}, {}, {}
    for p, t in files.items():
        b = os.path.basename(p)
        if b == "SKILL.md":
            skills[p] = t
        elif os.path.splitext(b)[1] in (".py", ".sh", ".js"):
            scripts[p] = t
        elif re.search(r"task|meeting|session|watch|cron|schedul", p, re.I):
            tasks[p] = t
        else:
            docs[p] = t

    out = {}

    # 1. ALWAYS-LOADED COST -- the only bloat that taxes every single turn.
    rows = []
    for p, t in skills.items():
        d = desc_of(t)
        rows.append((len(d), len(t), os.path.basename(os.path.dirname(p))))
    rows.sort(reverse=True)
    always = sum(r[0] for r in rows)
    out["always_loaded"] = {"skills": len(rows), "desc_chars": always,
                            "approx_tokens": always // 4,
                            "worst": [{"skill": n, "desc_chars": d} for d, _, n in rows[:10]]}

    # 2. DUPLICATION -- near-identical prose across any two files (9-word shingles).
    sh = {p: shingles(t) for p, t in files.items() if len(t) > 1200}
    dupes = []
    keys = list(sh)
    for i, x in enumerate(keys):
        for y in keys[i + 1:]:
            if not sh[x] or not sh[y]:
                continue
            inter = len(sh[x] & sh[y])
            j = inter / min(len(sh[x]), len(sh[y]))
            if j > 0.25:
                dupes.append({"overlap_pct": round(j * 100), "shared_shingles": inter,
                              "a": os.path.relpath(x, a.root), "b": os.path.relpath(y, a.root)})
    dupes.sort(key=lambda d: -d["overlap_pct"])
    out["duplication"] = dupes[:25]

    # 3. DISAMBIGUATION DEBT -- "Do NOT use / not for" lines. Each one is a
    #    trigger collision the author had to patch in prose. High count = the
    #    fleet can no longer route itself by name alone.
    debt = []
    for p, t in {**skills, **tasks}.items():
        n = len(re.findall(r"do not use|don't use|does not|not for |instead of that|that is /", t, re.I))
        if n:
            debt.append({"file": os.path.relpath(p, a.root), "collisions": n})
    debt.sort(key=lambda d: -d["collisions"])
    out["disambiguation_debt"] = {"total": sum(d["collisions"] for d in debt), "worst": debt[:15]}

    # 4. ORPHANS -- scripts and docs nothing else names. Nothing calls them,
    #    so nothing notices when they rot.
    names = {os.path.basename(p): p for p in files}
    corpus = "\n".join(files.values())
    orphans = []
    for p in list(scripts) + list(docs):
        b = os.path.basename(p)
        stem = os.path.splitext(b)[0]
        hits = len(re.findall(re.escape(stem), corpus))
        if hits <= 1:
            orphans.append({"file": os.path.relpath(p, a.root), "bytes": len(files[p]),
                            "days_since_touch": int((now - os.path.getmtime(p)) / 86400)})
    orphans.sort(key=lambda o: -o["bytes"])
    out["orphans"] = orphans[:25]

    # 5. STALE -- untouched past the threshold. Stale is not automatically dead,
    #    but stale + orphan + duplicated is.
    stale = [{"file": os.path.relpath(p, a.root),
              "days": int((now - os.path.getmtime(p)) / 86400), "bytes": len(t)}
             for p, t in files.items() if os.path.getmtime(p) < stale_cut]
    stale.sort(key=lambda s: -s["days"])
    out["stale"] = {"count": len(stale), "bytes": sum(s["bytes"] for s in stale), "worst": stale[:20]}

    # 6. SIZE PROFILE -- what the system weighs, by layer.
    out["profile"] = {k: {"files": len(v), "bytes": sum(len(x) for x in v.values())}
                      for k, v in (("skills", skills), ("tasks", tasks),
                                   ("scripts", scripts), ("docs", docs))}

    if a.json:
        print(json.dumps(out, indent=2))
        return

    P = print
    P("=" * 64)
    P(f"BLOAT AUDIT  {a.root}   {len(files)} text files")
    P("=" * 64)
    pr = out["profile"]
    for k, v in pr.items():
        P(f"  {k:<9} {v['files']:>4} files  {v['bytes']/1024:>8.0f} KB")
    P()
    al = out["always_loaded"]
    P(f"[1] ALWAYS-LOADED  {al['skills']} skills, {al['desc_chars']} desc chars "
      f"(~{al['approx_tokens']} tokens on EVERY turn)")
    for w in al["worst"][:8]:
        P(f"      {w['desc_chars']:>5}  {w['skill']}")
    P()
    P(f"[2] DUPLICATION  {len(out['duplication'])} file pairs over 25% shared text")
    for d in out["duplication"][:8]:
        P(f"      {d['overlap_pct']:>3}%  {d['a']}  <->  {d['b']}")
    P()
    dd = out["disambiguation_debt"]
    P(f"[3] DISAMBIGUATION DEBT  {dd['total']} collision lines across {len(dd['worst'])}+ files")
    for d in dd["worst"][:8]:
        P(f"      {d['collisions']:>3}  {d['file']}")
    P()
    P(f"[4] ORPHANS  {len(out['orphans'])} files nothing else references")
    for o in out["orphans"][:8]:
        P(f"      {o['bytes']:>7}B  {o['days_since_touch']:>4}d  {o['file']}")
    P()
    st = out["stale"]
    P(f"[5] STALE  {st['count']} files untouched >{a.days}d  ({st['bytes']/1024:.0f} KB)")
    for s in st["worst"][:8]:
        P(f"      {s['days']:>4}d  {s['file']}")
    P()
    P("DELETE CANDIDATES = appears in [4] AND [5], or >60% in [2].")
    P("Everything else needs a human decision. This script never deletes.")


if __name__ == "__main__":
    main()
