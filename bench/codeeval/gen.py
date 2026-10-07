"""Generate solutions for a JSONL of coding problems (HumanEval format) via the chat API. Records tokens and time."""
import json, time, urllib.request, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--problems", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--max-tokens", type=int, default=1536); ap.add_argument("--think", type=int, default=0)
ap.add_argument("--limit", type=int, default=0); ap.add_argument("--url", default="http://127.0.0.1:30270")
a = ap.parse_args()
P = [json.loads(l) for l in open(a.problems)][: a.limit or None]
try:
    done = {json.loads(l)["task_id"] for l in open(a.out)}
except FileNotFoundError:
    done = set()
f = open(a.out, "a")
for p in P:
    if p["task_id"] in done:
        continue
    msg = ("Complete the following Python function. Reply with the complete function (including the signature and any imports "
           "it needs) in a single ```python code block.\n\n```python\n" + p["prompt"] + "```")
    body = {"model": "glm-5.3-flash", "messages": [{"role": "user", "content": msg}], "max_tokens": a.max_tokens,
            "temperature": 0, "chat_template_kwargs": {"enable_thinking": bool(a.think)}}
    r = urllib.request.Request(a.url + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    o = json.load(urllib.request.urlopen(r, timeout=3600))
    dt = time.perf_counter() - t
    m = o["choices"][0]["message"]
    f.write(json.dumps({"task_id": p["task_id"], "text": m.get("content") or "", "reasoning_len": len(m.get("reasoning_content") or ""),
                        "completion_tokens": o.get("usage", {}).get("completion_tokens"), "s": dt}) + "\n")
    f.flush()
    print(p["task_id"], o.get("usage", {}).get("completion_tokens"), round(dt, 1), flush=True)
