"""Dump the structure of a pi session: per assistant turn the stop reason, output tokens, thinking length, tool calls
(write/edit content sizes with head/tail) and tool errors."""
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
for i, r in enumerate(rows):
    m = r.get("message") or {}
    role = m.get("role")
    if role == "assistant":
        think = sum(len(x.get("thinking", "")) for x in m.get("content") or [] if x.get("type") == "thinking")
        text = sum(len(x.get("text", "")) for x in m.get("content") or [] if x.get("type") == "text")
        calls = [x for x in m.get("content") or [] if x.get("type") == "toolCall"]
        out = (m.get("usage") or {}).get("output")
        print(f"#{i:3d} assistant stop={m.get('stopReason')} out={out} think={think} text={text} calls={[c.get('name') for c in calls]}")
        for c in calls:
            a = c.get("arguments") or {}
            if c.get("name") in ("write", "edit"):
                body = a.get("content") or a.get("newText") or a.get("new_string") or ""
                print(f"       {c['name']} path={a.get('path')} keys={list(a)} len={len(body)}")
                print("       HEAD:", repr(body[:140]))
                print("       TAIL:", repr(body[-160:]))
            elif c.get("name") == "bash":
                print("       bash:", a.get("command", "")[:150].replace("\n", " "))
    elif role == "toolResult":
        txt = " ".join(x.get("text", "") for x in m.get("content") or [] if isinstance(x, dict))
        if m.get("isError") or m.get("toolName") in ("write", "edit"):
            print(f"#{i:3d} result {m.get('toolName')} isError={m.get('isError')}: {txt[:200]!r}")
