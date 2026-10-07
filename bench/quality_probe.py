"""Teacher-forced quality probe over long continuations. --make-ref: greedy 256-token references (run with CAR off).
Otherwise: teacher-force prompt+reference, collect top-20 logprobs per continuation position, save."""
import json, sys, argparse, urllib.request, pathlib, math
ap = argparse.ArgumentParser(); ap.add_argument("--url", default="http://127.0.0.1:30270")
ap.add_argument("--ref", required=True); ap.add_argument("--make-ref", action="store_true"); ap.add_argument("--out")
ap.add_argument("--cmp", nargs=2); a = ap.parse_args()
P = ["Write a detailed explanation of how database indexes work, including B-trees, query planning and practical examples.",
     "Write a Python function to merge overlapping intervals. Include executable tests and explain edge cases.",
     "Türkçe olarak, İstanbul'da bir sonbahar gününü anlatan uzun ve betimleyici bir hikaye yaz.",
     "What is 17 times 23? Explain step by step, then give the final answer.",
     "List the planets of the solar system in order from the sun, with one fact about each."]
def req(path, body):
    r = urllib.request.Request(a.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=1800))
def dist(pos): return {t: lp for lp, t, _ in pos}
if a.cmp:
    A, B = json.load(open(a.cmp[0])), json.load(open(a.cmp[1]))
    kl = []; top1 = 0; n = 0; nll_a = nll_b = 0.0
    for ra, rb in zip(A, B):
        for pa, pb, ta, tb in zip(ra["top"], rb["top"], ra["tok"], rb["tok"]):
            da, db = dist(pa), dist(pb); n += 1
            top1 += max(da, key=da.get) == max(db, key=db.get)
            c = set(da) & set(db); xa = [math.exp(da[t]) for t in c]; xb = [math.exp(db[t]) for t in c]
            xa.append(max(1e-9, 1 - sum(xa))); xb.append(max(1e-9, 1 - sum(xb)))
            kl.append(sum(p * math.log(p / q) for p, q in zip(xa, xb) if p > 0))
            nll_a -= ta[0]; nll_b -= tb[0]
    kl.sort()
    print(json.dumps({"positions": n, "top1_agree": round(top1 / n, 4), "mean_kl": round(sum(kl) / n, 5), "p99_kl": round(kl[int(0.99 * n)], 4),
                      "ppl_ref_model": round(math.exp(nll_a / n), 4), "ppl_test_model": round(math.exp(nll_b / n), 4)}))
    sys.exit()
if a.make_ref:
    refs = []
    for p in P:
        ids = req("/tokenize", {"prompt": f"[gMASK]<sop><|user|>{p}<|assistant|><think></think>"})["tokens"]
        o = req("/generate", {"input_ids": ids, "sampling_params": {"temperature": 0, "max_new_tokens": 256}})
        out = req("/tokenize", {"prompt": o["text"]})["tokens"]
        refs.append({"prompt_ids": ids, "out_ids": out, "text": o["text"]})
    pathlib.Path(a.ref).write_text(json.dumps(refs, ensure_ascii=False)); print("refs", [len(r["out_ids"]) for r in refs]); sys.exit()
refs = json.load(open(a.ref)); rows = []
for r in refs:
    ids = r["prompt_ids"] + r["out_ids"]
    o = req("/generate", {"input_ids": ids, "return_logprob": True, "logprob_start_len": len(r["prompt_ids"]) - 1,
                          "top_logprobs_num": 20, "sampling_params": {"temperature": 0, "max_new_tokens": 1}})
    top = o["meta_info"]["input_top_logprobs"][1:len(r["out_ids"]) + 1]
    tok = []
    for pos, t in zip(top, r["out_ids"]):
        d = {tt: lp for lp, tt, _ in pos}; tok.append([d.get(t, min(d.values()))])
    rows.append({"top": top, "tok": tok})
pathlib.Path(a.out).write_text(json.dumps(rows)); print("saved", [len(x["top"]) for x in rows])
