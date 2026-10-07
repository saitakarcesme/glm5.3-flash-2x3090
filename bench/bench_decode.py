"""Decode benchmark: same prompt/protocol as archive benchmark.measure_decode, N reps, plus nv2 counter deltas."""
import sys, json, time, statistics, urllib.request, pathlib, argparse
sys.path.insert(0, "/home/isa/Experiments/glm53-flash-fit")
from benchmark import measure_decode
ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:30270")
ap.add_argument("--reps", type=int, default=3)
ap.add_argument("--tokens", type=int, default=256)
ap.add_argument("--warm", type=int, default=0)
ap.add_argument("--out", required=True)
a = ap.parse_args()
def stats():
    return json.load(urllib.request.urlopen(a.url + "/stats", timeout=60))
for _ in range(a.warm):
    measure_decode(a.url, a.tokens)
rows = []
for i in range(a.reps):
    b = stats()
    r = measure_decode(a.url, a.tokens)
    s = stats()
    d = {}
    for dev, x in s.get("nv2", {}).items():
        y = b["nv2"][dev]
        d[dev] = {k: x["host"][k] - y["host"][k] for k in ("picks", "vram", "ram", "nvme", "reads", "read_bytes", "evictions", "prefetch")}
        d[dev]["nv_wait_s"] = (x["dev"]["nv_wait_ns"] - y["dev"]["nv_wait_ns"]) / 1e9
        L = x.get("latency", {})
        d[dev]["lat_p50"] = {k: L[k]["p50"] for k in ("us_step_wait", "us_copy", "us_gap_copy_to_next_pub", "us_layer_total") if isinstance(L.get(k), dict)}
        d[dev]["lat_mean"] = {k: L[k]["mean"] for k in ("us_step_wait", "us_copy", "us_gap_copy_to_next_pub") if isinstance(L.get(k), dict)}
    acc = s.get("accepted_draft_tokens", 0) - b.get("accepted_draft_tokens", 0)
    rej = s.get("rejected_draft_tokens", 0) - b.get("rejected_draft_tokens", 0)
    rows.append({"tok_s": r["decode_delivery_tok_s"], "ttft_s": r["ttft_s"], "n": r["token_arrival_points"][-1][1],
                 "accept": acc, "reject": rej, "nv": d, "text_head": r["text"][:300], "text": r["text"]})
    print(json.dumps({k: v for k, v in rows[-1].items() if k not in ("text", "text_head")}), flush=True)
med = statistics.median([r["tok_s"] for r in rows])
pathlib.Path(a.out).write_text(json.dumps({"at": time.time(), "median_tok_s": med, "rows": rows}, indent=1))
print("MEDIAN", round(med, 4))
