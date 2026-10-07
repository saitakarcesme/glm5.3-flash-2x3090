"""Multi-prompt decode benchmark. Each request: raw /generate, greedy, N tokens; decode rate excludes first event (TTFT).
Score = aggregate decode tok/s over all measured requests (sum tokens / sum decode time); per-prompt medians reported."""
import json, time, statistics, urllib.request, pathlib, argparse
ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:30270"); ap.add_argument("--reps", type=int, default=2)
ap.add_argument("--tokens", type=int, default=256); ap.add_argument("--warm", type=int, default=1); ap.add_argument("--out", required=True)
a = ap.parse_args()
P = ["Write a detailed explanation of how database indexes work, including B-trees, query planning and practical examples.",
     "Write a Python function to merge overlapping intervals. Include executable tests and explain edge cases.",
     "Türkçe olarak, İstanbul'da bir sonbahar gününü anlatan uzun ve betimleyici bir hikaye yaz."]
def req(path, body):
    r = urllib.request.Request(a.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(r, timeout=900)
def run(p):
    prompt = f"[gMASK]<sop><|user|>{p}<|assistant|><think></think>"
    with req("/tokenize", {"prompt": prompt}) as r: ids = json.load(r)["tokens"]
    pts, text, t0 = [], "", time.perf_counter()
    with req("/generate", {"input_ids": ids, "stream": True, "sampling_params": {"temperature": 0, "max_new_tokens": a.tokens}}) as r:
        for line in r:
            if not line.startswith(b"data: "): continue
            d = line[6:].strip()
            if d == b"[DONE]": break
            e = json.loads(d); n = e.get("meta_info", {}).get("completion_tokens")
            if isinstance(n, int) and n > 0 and (not pts or n > pts[-1][1]): pts.append((time.perf_counter() - t0, n))
            text = e.get("text", text)
    return {"ttft": pts[0][0], "tok": pts[-1][1] - pts[0][1], "dt": pts[-1][0] - pts[0][0], "text": text}
for _ in range(a.warm):
    for p in P: run(p)
rows = []
for rep in range(a.reps):
    for i, p in enumerate(P):
        r = run(p); r["prompt"] = i; r["tok_s"] = r["tok"] / r["dt"]; rows.append(r)
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "text"}), flush=True)
agg = sum(r["tok"] for r in rows) / sum(r["dt"] for r in rows)
per = {i: statistics.median([r["tok_s"] for r in rows if r["prompt"] == i]) for i in range(len(P))}
ttft = statistics.median([r["ttft"] for r in rows])
pathlib.Path(a.out).write_text(json.dumps({"agg_tok_s": agg, "per_prompt": per, "ttft_median": ttft, "rows": rows}, ensure_ascii=False, indent=1))
print("AGG", round(agg, 3), "PER", {k: round(v, 2) for k, v in per.items()}, "TTFT", round(ttft, 2))
