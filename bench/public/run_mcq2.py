"""Multiple-choice benchmark runner (MMLU-Pro / GPQA format) against the local OpenAI-compatible server.
Official-style settings: thinking on, temperature 1.0, top_p 0.95, no client-side thinking budget. Resumable.
usage: run_mcq.py --data items.json --out run.jsonl [--per-cat 10] [--seed 0] [--max-tokens 32768]"""
import json, random, re, time, argparse, urllib.request, collections, math
ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--per-cat", type=int, default=10); ap.add_argument("--n", type=int, default=0); ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--max-tokens", type=int, default=65536); ap.add_argument("--url", default="http://127.0.0.1:30270")
ap.add_argument("--summary", action="store_true"); ap.add_argument("--ids"); ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--extra", default="{}", help="extra JSON sampling fields, e.g. {\"dry_multiplier\": 0.8}")
a = ap.parse_args()
L = "ABCDEFGHIJ"


def pick(items):
    r = random.Random(a.seed)
    if a.n:
        return r.sample(items, a.n)
    by = collections.defaultdict(list)
    for it in items: by[it["category"]].append(it)
    out = []
    for c in sorted(by): out += r.sample(by[c], min(a.per_cat, len(by[c])))
    return out


def summary(rows):
    n = len(rows); k = sum(r["correct"] for r in rows); p = k / n if n else 0
    se = math.sqrt(p * (1 - p) / n) if n else 0
    toks = sum(r["completion_tokens"] or 0 for r in rows); secs = sum(r["s"] for r in rows)
    return {"n": n, "correct": k, "accuracy": round(100 * p, 2), "ci95": round(196 * se, 2), "no_answer": sum(r["pred"] is None for r in rows),
            "avg_completion_tokens": round(toks / n) if n else 0, "e2e_tok_s": round(toks / secs, 1) if secs else 0}


items = json.load(open(a.data))
sel = pick(items)
if a.ids:
    want = json.load(open(a.ids))[: a.limit or None]; byid = {it["question_id"]: it for it in items}; sel = [byid[i] for i in want]
try:
    done = {json.loads(l)["question_id"]: json.loads(l) for l in open(a.out)}
except FileNotFoundError:
    done = {}
if a.summary:
    rows = [done[it["question_id"]] for it in sel if it["question_id"] in done]
    print(json.dumps(summary(rows))); raise SystemExit
f = open(a.out, "a")
for i, it in enumerate(sel):
    if it["question_id"] in done: continue
    opts = "\n".join(f"{L[j]}. {o}" for j, o in enumerate(it["options"]))
    prompt = (f"The following is a multiple choice question about {it['category']}. Think step by step and then finish your "
              f"answer with \"the answer is (X)\" where X is the correct letter choice.\n\nQuestion: {it['question']}\nOptions:\n{opts}")
    body = {"model": "glm-5.3-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": a.max_tokens,
            "temperature": 1.0, "top_p": 0.95, **{"thinking_budget": 0, **json.loads(a.extra)}, "chat_template_kwargs": {"enable_thinking": True}}
    t = time.time()
    req = urllib.request.Request(a.url + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    o = json.load(urllib.request.urlopen(req, timeout=7200)); dt = time.time() - t
    msg = o["choices"][0]["message"]; txt = msg.get("content") or ""
    m = re.findall(r"answer is \(?\**([A-J])\**\)?", txt) or re.findall(r"\b([A-J])\b\)?\s*$", txt.strip())
    pred = m[-1] if m else None
    row = {"question_id": it["question_id"], "category": it["category"], "gold": it["answer"], "pred": pred, "correct": pred == it["answer"],
           "completion_tokens": o.get("usage", {}).get("completion_tokens"), "finish": o["choices"][0].get("finish_reason"),
           "s": round(dt, 1), "answer_tail": txt[-200:], "reasoning_len": len(msg.get("reasoning_content") or ""), "reasoning_tail": (msg.get("reasoning_content") or "")[-3000:]}
    f.write(json.dumps(row) + "\n"); f.flush(); done[it["question_id"]] = row
    rows = [done[x["question_id"]] for x in sel if x["question_id"] in done]
    print(f"[{len(rows)}/{len(sel)}] {it['category'][:12]:12s} gold {it['answer']} pred {pred} {'OK ' if row['correct'] else 'BAD'} "
          f"{row['completion_tokens']} tok {dt:.0f}s | running {json.dumps(summary(rows))}", flush=True)
print("FINAL", json.dumps(summary([done[x["question_id"]] for x in sel if x["question_id"] in done])))
