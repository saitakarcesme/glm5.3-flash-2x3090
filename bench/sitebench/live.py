# pretty live view of a Claude Code stream-json session (for the rig desktop window)
import json, sys, time
f = open(sys.argv[1])
while True:
    l = f.readline()
    if not l:
        time.sleep(0.5); continue
    try: e = json.loads(l)
    except ValueError: continue
    if e.get("type") == "assistant":
        for c in e["message"].get("content", []):
            if c.get("type") == "text": print("\033[1;32mGLM:\033[0m", c["text"][:1500], flush=True)
            elif c.get("type") == "thinking": print("\033[2m(thinking) " + c["thinking"][:300].replace("\n", " ") + "…\033[0m", flush=True)
            elif c.get("type") == "tool_use": print("\033[1;36m→ " + c["name"] + "\033[0m", json.dumps(c["input"])[:300], flush=True)
    elif e.get("type") == "user":
        for c in e["message"].get("content", []) if isinstance(e["message"].get("content"), list) else []:
            if c.get("type") == "tool_result":
                t = c.get("content"); t = t if isinstance(t, str) else json.dumps(t)
                print("\033[33m  ←", t[:300].replace("\n", " "), "\033[0m", flush=True)
    elif e.get("type") == "result":
        print("\n\033[1;35m=== DONE:", e.get("subtype"), "turns", e.get("num_turns"), "===\033[0m", flush=True)
