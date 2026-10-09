"""claude-opt: strip Claude Code's per-request billing header from the prompt. Claude Code prepends
'x-anthropic-billing-header: cc_version=...; cc_entrypoint=...; cch=<random>;' to the system prompt and the cch value
changes on every request, so the prompt diverges at that point and the prefix cache can never be reused (every agent
turn re-prefilled ~6-20k tokens: 50-110 s per turn). It is billing metadata, not instructions."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "BILLING_RE" not in s
s = s.replace("def normalize_messages(messages):",
'''BILLING_RE = re.compile(r"x-anthropic-billing-header:(?:\\s*[\\w.-]+=[^;\\n]*;)+\\s*")


def _strip_billing(c):
    if isinstance(c, str):
        return BILLING_RE.sub("", c)
    if isinstance(c, list):
        return [dict(x, text=BILLING_RE.sub("", x["text"])) if isinstance(x, dict) and isinstance(x.get("text"), str)
                else x for x in c]
    return c


def normalize_messages(messages):''', 1)
old = """        if m.get("content") is None:
            m["content"] = ""
"""
assert old in s
s = s.replace(old, old + """        if m.get("role") == "system":
            m["content"] = _strip_billing(m["content"])
""", 1)
ast.parse(s); p.write_text(s); print("ok")
