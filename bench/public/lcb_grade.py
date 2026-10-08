"""(run inside the --network none sandbox) Grade LiveCodeBench generations: every test must pass (pass@1).
stdin problems: run the program with the input, compare whitespace-normalised stdout. functional (LeetCode) problems:
call Solution().<func_name>(*args) with the JSON-decoded input lines and compare to the expected JSON value.
usage: lcb_grade.py lcb_sel.json gens.jsonl"""
import json, sys, re, subprocess, tempfile, os, collections
P = {p["id"]: p for p in json.load(open(sys.argv[1]))}
G = [json.loads(l) for l in open(sys.argv[2])]
HARNESS = r'''
import sys, json
from typing import *
import collections, heapq, bisect, itertools, functools, math, string, re
from collections import *
from heapq import *
from bisect import *
from functools import *
from itertools import *
from math import *
__CODE__
args = [json.loads(l) for l in sys.stdin.read().split("\n") if l.strip()]
res = Solution().__FN__(*args)
print(json.dumps(res))
'''


def norm(s):
    return [l.rstrip() for l in s.strip().replace("\r\n", "\n").split("\n")]


def run(code, inp, timeout=6):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir="/tmp") as t:
        t.write(code); fn = t.name
    try:
        r = subprocess.run([sys.executable, fn], input=inp, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except subprocess.TimeoutExpired:
        return -9, ""
    finally:
        os.unlink(fn)


res = collections.defaultdict(lambda: [0, 0]); rows = []
for g in G:
    p = P[g["id"]]
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", g["text"], re.S)
    code = blocks[-1] if blocks else ""
    ok = bool(code)
    for t in p["tests"] if ok else []:
        if p["func_name"]:
            rc, out = run(HARNESS.replace("__CODE__", code).replace("__FN__", p["func_name"]), t["input"])
            try:
                ok = rc == 0 and json.loads(out.strip().splitlines()[-1]) == json.loads(t["output"])
            except Exception:
                ok = False
        else:
            rc, out = run(code, t["input"])
            ok = rc == 0 and norm(out) == norm(t["output"])
        if not ok: break
    res[p["difficulty"]][0] += ok; res[p["difficulty"]][1] += 1
    rows.append({"id": g["id"], "difficulty": p["difficulty"], "pass": ok})
tot = sum(v[0] for v in res.values()); n = sum(v[1] for v in res.values())
print(json.dumps({"pass@1": round(100 * tot / max(1, n), 1), "passed": tot, "n": n,
                  "by_difficulty": {k: f"{v[0]}/{v[1]}" for k, v in sorted(res.items())}}))
json.dump(rows, open(sys.argv[2] + ".graded.json", "w"))
