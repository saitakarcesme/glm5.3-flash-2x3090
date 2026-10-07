import json, math, sys
def load(f):
    out = []
    for row in json.load(open(f)):
        for pos in row["response"]["meta_info"]["input_top_logprobs"]:
            if pos: out.append({t: lp for lp, t, _ in pos})
    return out
def cmp(fa, fb):
    A, B = load(fa), load(fb)
    n = min(len(A), len(B)); top1 = 0; kls = []; diffs = []
    for a, b in zip(A[:n], B[:n]):
        top1 += max(a, key=a.get) == max(b, key=b.get)
        c = set(a) & set(b)
        pa = [math.exp(a[t]) for t in c]; pb = [math.exp(b[t]) for t in c]
        ta, tb = max(1e-12, 1 - sum(pa)), max(1e-12, 1 - sum(pb))
        kls.append(sum(x * math.log(x / y) for x, y in zip(pa + [ta], pb + [tb]) if x > 0))
        diffs += [abs(a[t] - b[t]) for t in c]
    return {"a": fa, "b": fb, "top1_equal": top1, "positions": n, "mean_coarsened_kl": sum(kls) / n, "max_coarsened_kl": max(kls),
            "mean_abs_logprob_difference": sum(diffs) / len(diffs)}
for pair in sys.argv[1:]:
    a, b = pair.split(","); print(json.dumps(cmp(a, b)))
