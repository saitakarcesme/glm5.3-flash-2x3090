"""claude-opt: stream each parallel tool call in its own SSE chunk (like OpenAI does). With all calls in one delta,
LiteLLM's Anthropic adapter concatenated their arguments into one tool_use ('{...}{...}{...}' -> Claude Code
InputValidationError, the agent had to retry)."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
old = """                        yield sse(dict(base, choices=[{"index": 0, "delta": {"tool_calls": [dict(c, index=i) for i, c in enumerate(calls)]}, "finish_reason": None}]))"""
assert old in s
new = """                        for i, c in enumerate(calls):   # TCSPLIT: one chunk per tool call
                            yield sse(dict(base, choices=[{"index": 0, "delta": {"tool_calls": [dict(c, index=i)]}, "finish_reason": None}]))"""
s = s.replace(old, new, 1)
ast.parse(s); p.write_text(s); print("ok")
