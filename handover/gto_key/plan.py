#!/usr/bin/env python3
"""Print the next spot URLs for one solution/depth from what spots.jsonl already holds."""
import json, sys, os, re
S = os.path.dirname(os.path.abspath(__file__))
SEATS = {2: ["SB","BB"], 6: ["UTG","HJ","CO","BTN","SB","BB"],
         8: ["UTG","UTG1","LJ","HJ","CO","BTN","SB","BB"],
         9: ["UTG","UTG1","UTG2","LJ","HJ","CO","BTN","SB","BB"]}
def load():
    recs = {}
    p = os.path.join(S, "spots.jsonl")
    if os.path.exists(p):
        for line in open(p):
            r = json.loads(line); recs[(r["code"], str(r["depth"]), r["actions"])] = r
    return recs
def token(label):
    if label.startswith("Raise "): return "R" + label.split()[1]
    if label.startswith("Allin "): return "R" + label.split()[1]
    if label == "Call": return "C"
    if label == "Fold": return "F"
    return None
def main_raise(rec):
    """the non-allin raise with the largest frequency"""
    best = None
    for a in rec["acts"]:
        if a["label"].startswith("Raise "):
            if best is None or a["freq"] > best["freq"]: best = a
    return best
def url(code, depth, actions):
    q = f"solution_type=gwiz&gametype={code}&depth={depth}"
    if actions: q += f"&preflop_actions={actions}"
    q += f"&history_spot={len(actions.split('-')) if actions else 0}"
    return "https://app.gtowizard.com/solutions?" + q
def plan(code, depth, n, limit, kinds):
    recs = load(); seats = SEATS[n]; want = []; done = 0
    def have(a): return (code, str(depth), a) in recs
    def add(a, kind, acting):
        nonlocal done
        if have(a): done += 1
        else: want.append((a, kind, acting))
    # opens
    for i in range(n-1):
        add("-".join(["F"]*i), "open", seats[i])
    for i in range(n-1):
        o = recs.get((code, str(depth), "-".join(["F"]*i)))
        if not o: continue
        orz = main_raise(o)
        if not orz: continue
        ot = token(orz["label"])
        for j in range(i+1, n):
            fa = "-".join(["F"]*i + [ot] + ["F"]*(j-i-1))
            if "facing" in kinds: add(fa, "facing", seats[j])
            f = recs.get((code, str(depth), fa))
            if not f: continue
            trz = main_raise(f)
            if not trz: continue
            v3 = "-".join([fa, token(trz["label"])] + ["F"]*(n-1-j))
            if "vs3bet" in kinds: add(v3, "vs3bet", seats[i])
            v = recs.get((code, str(depth), v3))
            if not v: continue
            frz = main_raise(v)
            if not frz: continue
            v4 = v3 + "-" + token(frz["label"])
            if "vs4bet" in kinds: add(v4, "vs4bet", seats[j])
    out = [{"url": url(code, depth, a), "kind": k, "acting": s, "actions": a} for a, k, s in want[:limit]]
    print(json.dumps({"done": done, "pending_total": len(want), "batch": out}, indent=0))
if __name__ == "__main__":
    code, depth, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    kinds = sys.argv[5].split(",") if len(sys.argv) > 5 else ["facing","vs3bet","vs4bet"]
    plan(code, depth, n, limit, kinds)
