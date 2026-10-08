"""Prefix-reuse correctness. Builds a long multi-turn agent-style chat (system + file dumps as tool results).
  --phase warm : send turn A (primes the prefix cache), then turn B (reuses it); save B's greedy output
  --phase fresh: (run right after a server restart) send turn B only; save its greedy output
  --compare    : compare the two outputs
Raw /generate with token ids so both phases see byte-identical inputs."""
import json, sys, argparse, urllib.request, pathlib, time
ap = argparse.ArgumentParser(); ap.add_argument("--phase"); ap.add_argument("--out"); ap.add_argument("--compare", nargs=2)
ap.add_argument("--files", nargs="*"); ap.add_argument("--url", default="http://127.0.0.1:30270"); ap.add_argument("--n", type=int, default=200)
a = ap.parse_args()
def req(path, body):
    r = urllib.request.Request(a.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=3600))
if a.compare:
    x, y = [json.load(open(f)) for f in a.compare]
    tx, ty = x["text"], y["text"]
    i = next((k for k, (c, d) in enumerate(zip(tx, ty)) if c != d), min(len(tx), len(ty)))
    print(json.dumps({"identical": tx == ty, "first_diff_char": i, "len": [len(tx), len(ty)]}))
    print("A:", repr(tx[max(0, i - 80): i + 200])); print("B:", repr(ty[max(0, i - 80): i + 200])); sys.exit()
docs = "".join(f"<|observation|>{open(f).read()}" for f in a.files)
sysmsg = "[gMASK]<sop><|system|>You are a precise assistant working in a repository. Answer only from the files.<|user|>Read the research files."
turn_a = sysmsg + "<|assistant|><think></think>I will read them." + docs + "<|user|>In one sentence: what GPU setup is used?<|assistant|><think></think>"
turn_b = sysmsg + "<|assistant|><think></think>I will read them." + docs + "<|user|>List every idea that did NOT help, with its measured result, as a bullet list.<|assistant|><think></think>"
ib = req("/tokenize", {"prompt": turn_b})["tokens"]
if a.phase == "warm":
    ia = req("/tokenize", {"prompt": turn_a})["tokens"]
    t = time.time(); req("/generate", {"input_ids": ia, "sampling_params": {"temperature": 0, "max_new_tokens": 40}}); ta = time.time() - t
else:
    ta = None
t = time.time(); o = req("/generate", {"input_ids": ib, "sampling_params": {"temperature": 0, "max_new_tokens": a.n}}); tb = time.time() - t
pathlib.Path(a.out).write_text(json.dumps({"phase": a.phase, "prompt_tokens": len(ib), "t_a": ta, "t_b": tb, "text": o["text"]}))
print(a.phase, "prompt_tokens", len(ib), "t_a", ta and round(ta, 1), "t_b", round(tb, 1)); print(o["text"][:500])
