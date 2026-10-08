"""(run inside the --network none sandbox) Select a stratified LiveCodeBench subset and decode its tests.
Private tests are base64(zlib(pickle(json))) in the official release; decoding happens only here.
usage: lcb_prepare.py in.jsonl out.json per_difficulty seed"""
import json, sys, random, base64, zlib, pickle, collections
src, dst, per, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rows = [json.loads(l) for l in open(src)]
by = collections.defaultdict(list)
for r in rows: by[r["difficulty"]].append(r)
rnd = random.Random(seed); sel = []
for d in sorted(by): sel += rnd.sample(by[d], min(per, len(by[d])))
out = []
for r in sel:
    pub = json.loads(r["public_test_cases"])
    priv = r["private_test_cases"]
    try:
        priv = json.loads(priv)
    except Exception:
        priv = json.loads(pickle.loads(zlib.decompress(base64.b64decode(priv.encode("utf-8")))))
    meta = json.loads(r.get("metadata") or "{}")
    out.append({"id": r["question_id"], "title": r["question_title"], "difficulty": r["difficulty"], "date": r["contest_date"],
                "platform": r["platform"], "content": r["question_content"], "starter_code": r.get("starter_code") or "",
                "func_name": meta.get("func_name"), "tests": pub + priv})
json.dump(out, open(dst, "w"))
print(len(rows), "problems in file; selected", len(out), {d: len(v) for d, v in by.items()},
      "dates", min(r["contest_date"] for r in rows)[:10], "->", max(r["contest_date"] for r in rows)[:10])
