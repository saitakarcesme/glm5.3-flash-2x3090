"""Agent-scale long-context quality check. Builds a ~N-token chat (research notes + source files as tool outputs, like
an agent that has read a repo) and asks fact questions with verifiable answers. Greedy, thinking off.
usage: longctx_quality.py --files f1 f2 ... --tag TAG [--target 45000]"""
import json, argparse, urllib.request, re, time, pathlib
ap = argparse.ArgumentParser(); ap.add_argument("--files", nargs="+"); ap.add_argument("--tag", required=True)
ap.add_argument("--target", type=int, default=45000); ap.add_argument("--url", default="http://127.0.0.1:30270")
a = ap.parse_args()
def req(path, body):
    r = urllib.request.Request(a.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=3600))
Q = [("What decode tok/s did the starting profile (21/21 split) reach on the 3-prompt benchmark? Number only.", [r"8\.5"]),
     ("How many of the 64 coding problems does the exact profile solve, and how many does the current fast profile solve? Answer as 'exact X, fast Y'.", [r"54", r"53"]),
     ("What is the measured H2D bandwidth of GPU1 on its chipset x4 link, in GB/s? Number only.", [r"6\.4"]),
     ("In the CAR rules, an NVMe-only expert is kept only above what routing-weight percentage? Number only.", [r"30"]),
     ("Which layer split (GPU0/GPU1 MoE layers) does the final profile use? Answer like 'A/B'.", [r"27\s*/\s*15"]),
     ("What prefill speed in tok/s was measured with 4096-token chunks? Give the range.", [r"5[0-3]\d"])]
blocks = []
for f in a.files:
    blocks.append(f"<|observation|>File: {f}\n{open(f, errors='replace').read()}")
ctx = ""
for b in blocks:
    ctx += b
    if len(ctx) > a.target * 3.6: break
base = ("[gMASK]<sop><|system|>You are a careful coding agent. Answer strictly from the files you have read.<|user|>"
        "Read the project files, then answer my questions.<|assistant|><think></think>Reading the files." + ctx)
rows, ok = [], 0
for q, pats in Q:
    ids = req("/tokenize", {"prompt": base + f"<|user|>{q}<|assistant|><think></think>"})["tokens"]
    t = time.time(); o = req("/generate", {"input_ids": ids, "sampling_params": {"temperature": 0, "max_new_tokens": 60}}); dt = time.time() - t
    ans = o["text"].strip(); hit = all(re.search(p, ans) for p in pats); ok += hit
    rows.append({"q": q, "answer": ans, "pass": hit, "s": round(dt, 1), "prompt_tokens": len(ids)})
    print(("PASS" if hit else "FAIL"), len(ids), round(dt, 1), repr(ans[:120]), flush=True)
pathlib.Path(f"lq-{a.tag}.json").write_text(json.dumps(rows, indent=1))
print(f"[{a.tag}] {ok}/{len(Q)} correct at ~{rows[0]['prompt_tokens']} tokens")
