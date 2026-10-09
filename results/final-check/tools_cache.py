"""Final check: single + parallel tool calls (direct, streamed) and prompt-cache reuse."""
import json, time, urllib.request
U = "http://127.0.0.1:30270/v1/chat/completions"
def post(body, stream=False):
    req = urllib.request.Request(U, json.dumps(body).encode(), {"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=1800)
    if not stream: return json.load(r)
    calls = {}
    for line in r:
        line = line.decode().strip()
        if not line.startswith("data:") or line == "data: [DONE]": continue
        for ch in json.loads(line[5:]).get("choices", []):
            for tc in (ch.get("delta") or {}).get("tool_calls") or []:
                c = calls.setdefault(tc["index"], {"name": "", "args": ""})
                c["name"] += (tc.get("function") or {}).get("name") or ""; c["args"] += (tc.get("function") or {}).get("arguments") or ""
    return calls
tool = [{"type": "function", "function": {"name": "write_file", "description": "Write a file",
         "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
        {"type": "function", "function": {"name": "get_weather", "description": "Weather for a city",
         "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]
res = {}
c = post({"model": "g", "tools": tool, "max_tokens": 3000, "stream": True, "messages": [{"role": "user", "content": "What is the weather in Istanbul? Use the tool."}]}, True)
ok1 = len(c) == 1 and c[0]["name"] == "get_weather" and json.loads(c[0]["args"]).get("city", "").lower().startswith("istanbul")
c = post({"model": "g", "tools": tool, "max_tokens": 4000, "stream": True, "messages": [{"role": "user", "content": "In ONE response call write_file three times in parallel: a.txt='A', b.txt='B', c.txt='C'. No explanation."}]}, True)
ok3 = len(c) == 3 and all(json.loads(v["args"]).get("path") in ("a.txt", "b.txt", "c.txt") for v in c.values())
big = open("/home/isa/Experiments/glm53-flash-fit/claude-opt/serve_claude.py").read()[:50000]
m = [{"role": "system", "content": big}, {"role": "user", "content": "Reply OK."}]
t = time.time(); post({"model": "g", "messages": m, "max_tokens": 1, "chat_template_kwargs": {"enable_thinking": False}}); cold = time.time() - t
t = time.time(); post({"model": "g", "messages": m + [{"role": "assistant", "content": "OK."}, {"role": "user", "content": "Again."}], "max_tokens": 1, "chat_template_kwargs": {"enable_thinking": False}}); warm = time.time() - t
print(json.dumps({"single_tool_call": ok1, "parallel_tool_calls_3": ok3, "prefill_cold_s": round(cold, 1), "prefill_cached_s": round(warm, 1)}))
