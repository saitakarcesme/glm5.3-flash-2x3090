"""Run generated solutions against the problem tests. Intended to run inside a no-network, memory-capped container.
usage: run_tests.py problems.jsonl gens.jsonl"""
import json, sys, re, subprocess, tempfile, os
P = {json.loads(l)["task_id"]: json.loads(l) for l in open(sys.argv[1])}
G = [json.loads(l) for l in open(sys.argv[2])]
ok = 0
res = []
for g in G:
    p = P[g["task_id"]]
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", g["text"], re.S)
    code = max(blocks, key=len) if blocks else g["text"]
    if f"def {p['entry_point']}" not in code:
        code = p["prompt"] + code
    prog = code + "\n\n" + p["test"] + f"\n\ncheck({p['entry_point']})\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir="/tmp") as t:
        t.write(prog)
        fn = t.name
    try:
        r = subprocess.run([sys.executable, fn], capture_output=True, timeout=20)
        passed = r.returncode == 0
        err = r.stderr.decode(errors="replace")[-300:]
    except subprocess.TimeoutExpired:
        passed, err = False, "timeout"
    os.unlink(fn)
    ok += passed
    res.append({"task_id": g["task_id"], "passed": passed, "err": "" if passed else err})
print(json.dumps({"passed": ok, "total": len(G), "pass_rate": round(ok / max(1, len(G)), 4),
                  "failed": [r["task_id"] for r in res if not r["passed"]]}))
