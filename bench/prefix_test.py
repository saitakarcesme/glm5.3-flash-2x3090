"""Prefix reuse: the same long chat prefix sent 3 times with different final questions (agent-style turns)."""
import json, time, urllib.request, random
U = "http://127.0.0.1:30270"
rnd = random.Random(3)
code = "\n".join(f"def helper_{i}(x):\n    # utility {i}\n    return (x * {rnd.randint(2,99)} + {rnd.randint(0,999)}) % {rnd.randint(1000,9999)}\n" for i in range(700))
qs = ["What does helper_17 return for x=3? Compute it exactly.", "Which helper uses the largest modulus? Name only.", "How many helper functions are defined? Number only."]
for q in qs:
    body = {"model": "glm-5.3-flash", "messages": [{"role": "system", "content": "You are a precise coding assistant."},
            {"role": "user", "content": "Here is a Python module:\n```python\n" + code + "\n```\n" + q}],
            "max_tokens": 64, "temperature": 0, "stream": True, "stream_options": {"include_usage": True}, "chat_template_kwargs": {"enable_thinking": False}}
    r = urllib.request.Request(U + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.perf_counter(); first = None; text = ""; usage = None
    for line in urllib.request.urlopen(r, timeout=3600):
        if not line.startswith(b"data: ") or line.strip() == b"data: [DONE]": continue
        e = json.loads(line[6:]); usage = e.get("usage") or usage
        for c in e.get("choices", []):
            p = c.get("delta", {}).get("content") or ""
            if p and first is None: first = time.perf_counter() - t
            text += p
    print(json.dumps({"prompt_tokens": (usage or {}).get("prompt_tokens"), "ttft_s": round(first or -1, 2), "total_s": round(time.perf_counter() - t, 2), "answer": text.strip()[:80]}), flush=True)
