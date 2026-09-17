#!/usr/bin/env python3
"""Read blocks from stdin: a line 'U|code|depth|actions' followed by one 'S|...' line; append JSON to spots.jsonl."""
import sys, json, os
S = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(S, "spots.jsonl")
lines = [l.rstrip("\n") for l in sys.stdin if l.strip()]
recs = []; i = 0
while i < len(lines):
    u = lines[i]; i += 1
    if not u.startswith("U|"): print("skip", u[:40]); continue
    _, code, depth, actions = u.split("|", 3)
    s = lines[i]; i += 1
    assert s.startswith("S|"), s[:40]
    f = s.split("|")
    _, acting, bar, pot, acts, hands, unknown = f[:7]
    acts = [a.split("~") for a in acts.split(";") if a]
    acts = [{"label": a[0], "freq": float(a[1]) if a[1] else None, "combos": float(a[2]) if a[2] else None} for a in acts]
    hd = {}
    for h in hands.split(";"):
        if not h: continue
        parts = h.split(" "); name = parts[0]; hd[name] = []
        for p in parts[1:]:
            if p == "-": continue
            if ":" in p: k, fr = p.split(":"); hd[name].append([int(k) if k != "?" else "?", float(fr)])
            else: hd[name].append([int(p) if p != "?" else "?", 100.0])
    n = len(hd)
    recs.append({"code": code, "depth": depth, "actions": actions, "acting": acting, "bar": bar, "pot": pot.split("~"), "acts": acts, "hands": hd, "unknown": unknown, "n_hands": n})
existing = set()
if os.path.exists(OUT):
    for l in open(OUT):
        r = json.loads(l); existing.add((r["code"], r["depth"], r["actions"]))
added = 0
with open(OUT, "a") as f:
    for r in recs:
        key = (r["code"], r["depth"], r["actions"])
        if r["n_hands"] != 169: print("INCOMPLETE", key, r["n_hands"]); continue
        if key in existing: print("dup", key); continue
        f.write(json.dumps(r, separators=(",", ":")) + "\n"); existing.add(key); added += 1
print("added", added, "total", len(existing))
