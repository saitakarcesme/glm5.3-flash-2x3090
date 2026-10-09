import json, re, sys, os
R, wall = sys.argv[1], int(sys.argv[2])
reqs = [dict(re.findall(r"(\w+)=([\d.]+|True|False)", l)) for l in open(f"{R}/server.log") if "-- req " in l]
guards = sum(1 for l in open(f"{R}/server.log") if "-- guard" in l)
out = sum(int(r["out"]) for r in reqs); pre = sum(int(r["prefill"]) for r in reqs)
dec = sum(float(r["decode"]) for r in reqs); ttft = sum(float(r["ttft"]) for r in reqs)
peak = max((int(r["P"]) for r in reqs), default=0)
res = {}
for l in open(f"{R}/session.jsonl"):
    try: e = json.loads(l)
    except ValueError: continue
    if e.get("type") == "result": res = e
files = [os.path.join(dp, f) for dp, dn, fn in os.walk(R.replace(".run", "")) if "node_modules" not in dp for f in fn]
print(f"""# Session report — {os.path.basename(R)}
| Metric | Value |
|---|---|
| Wall time | {wall // 60} min {wall % 60} s |
| Agent turns (model requests) | {len(reqs)} (Claude Code num_turns {res.get('num_turns')}) |
| Output tokens (incl. thinking) | {out:,} |
| Prompt tokens processed (prefill, after cache reuse) | {pre:,} |
| Peak context | {peak:,} tokens (of 131,072) |
| Decode speed | {out / dec if dec else 0:.1f} tok/s (output tokens / decode time) |
| Time waiting for first token (sum) | {ttft:.0f} s |
| Time generating (sum) | {dec:.0f} s |
| Loop/turn guards triggered | {guards} |
| Result | {res.get('subtype')} {'(error)' if res.get('is_error') else ''} |
| Files created (excl. node_modules) | {len(files)} |
""")
