"""Long-context needle test: varied synthetic records (fill), a unique code at a given depth, question at the end.
Reports prefill time (TTFT), answer, pass. usage: needle.py SIZE[,SIZE..] [depth]"""
import json, sys, time, random, urllib.request
U = "http://127.0.0.1:30270"
def req(path, body, t=3600):
    r = urllib.request.Request(U + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=t))
rnd = random.Random(7)
cities = ["Lyon", "Izmir", "Osaka", "Quito", "Perth", "Tallinn", "Accra", "Hanoi", "Bergen", "Cusco"]
def record(i):
    return (f"Record {i}: shipment {rnd.randint(10000,99999)} left {rnd.choice(cities)} on day {rnd.randint(1,365)} "
            f"carrying {rnd.randint(1,900)} crates of part {rnd.choice('ABCDEFGHJK')}{rnd.randint(100,999)}; inspector notes were routine. ")
pre = req("/tokenize", {"prompt": "[gMASK]<sop><|user|>Below is a long log. Read it carefully.\n"})["tokens"]
depth = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
for size in [int(x) for x in sys.argv[1].split(",")]:
    code = f"{rnd.randint(1000,9999)}-{rnd.choice(['ORCHID','PELICAN','GRANITE','MERIDIAN'])}"
    needle = req("/tokenize", {"prompt": f" IMPORTANT: the vault access code is {code}. Remember it. "})["tokens"]
    q = req("/tokenize", {"prompt": "\nQuestion: what is the vault access code mentioned in the log? Answer with the code only.<|assistant|><think></think>"})["tokens"]
    body_toks, i = [], 0
    while len(body_toks) < size:
        chunk = "".join(record(j) for j in range(i, i + 200)); i += 200
        body_toks += req("/tokenize", {"prompt": chunk})["tokens"]
    body_toks = body_toks[: size - len(pre) - len(q) - len(needle)]
    at = int(len(body_toks) * depth)
    ids = pre + body_toks[:at] + needle + body_toks[at:] + q
    t = time.perf_counter()
    o = req("/generate", {"input_ids": ids, "sampling_params": {"temperature": 0, "max_new_tokens": 16}})
    dt = time.perf_counter() - t
    ans = o.get("text", "").strip()
    print(json.dumps({"tokens": len(ids), "depth": depth, "elapsed_s": round(dt, 1), "prefill_tok_s": round(len(ids) / dt, 1),
                      "expected": code, "answer": ans[:40], "pass": code in ans}), flush=True)
