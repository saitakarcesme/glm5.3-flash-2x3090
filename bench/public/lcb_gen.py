"""LiveCodeBench generation (host side: talks to the model only, executes nothing). LCB-style prompts, official
GLM sampling (thinking on, temperature 1.0, top_p 0.95, no client thinking budget). Resumable.
usage: lcb_gen.py data/lcb_sel.json out.jsonl"""
import json, sys, time, urllib.request
src, out = sys.argv[1], sys.argv[2]
P = json.load(open(src))
try:
    done = {json.loads(l)["id"] for l in open(out)}
except FileNotFoundError:
    done = set()
f = open(out, "a")
for i, p in enumerate(P):
    if p["id"] in done: continue
    if p["func_name"]:
        fmt = ("You will use the following starter code to write the solution to the problem and enclose your code within "
               "delimiters.\n```python\n" + p["starter_code"] + "\n```")
    else:
        fmt = ("Read the inputs from stdin solve the problem and write the answer to stdout (do not directly test on the sample "
               "inputs). Enclose your code within delimiters as follows.\n```python\n# YOUR CODE HERE\n```")
    prompt = ("You will be given a question (problem specification) and will generate a correct Python program that matches the "
              "specification and passes all tests.\n\nQuestion: " + p["content"] + "\n\n" + fmt)
    body = {"model": "glm-5.3-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 65536,
            "temperature": 1.0, "top_p": 0.95, "thinking_budget": 0, "chat_template_kwargs": {"enable_thinking": True}}
    t = time.time()
    req = urllib.request.Request("http://127.0.0.1:30270/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    o = json.load(urllib.request.urlopen(req, timeout=7200)); dt = time.time() - t
    rc = o["choices"][0]["message"].get("reasoning_content") or ""
    row = {"id": p["id"], "difficulty": p["difficulty"], "text": o["choices"][0]["message"].get("content") or "",
           "reasoning_len": len(rc), "reasoning_head": rc[:1500], "reasoning_tail": rc[-3000:],
           "finish": o["choices"][0].get("finish_reason"), "completion_tokens": o.get("usage", {}).get("completion_tokens"), "s": round(dt, 1)}
    f.write(json.dumps(row) + "\n"); f.flush()
    print(f"[{i + 1}/{len(P)}] {p['difficulty']:6s} {row['completion_tokens']} tok {dt:.0f}s {row['finish']}", flush=True)
