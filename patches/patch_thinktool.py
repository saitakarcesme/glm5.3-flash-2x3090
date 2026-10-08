"""claude-opt: GLM sometimes starts a tool call without closing its think block ("...<tool_call>name<arg_key>..."). The
stock server then reports the whole call as reasoning, returns no tool call and finish=stop, so the agent quits.
Treat "<tool_call>" inside the thinking phase as the end of the thinking (streaming, non-streaming, guard)."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "THINK_TOOL_FIX" not in s

# 1. non-streaming split
old = '''def split_reasoning(text):
    """GLM-5.3 thinks inside <think>...</think>; the prompt already opened the block."""
    if "</think>" in text:'''
assert old in s
s = s.replace(old, '''def split_reasoning(text):
    """GLM-5.3 thinks inside <think>...</think>; the prompt already opened the block."""
    # THINK_TOOL_FIX: a tool call that starts before </think> ends the reasoning there
    tc, ct = text.find("<tool_call>"), text.find("</think>")
    if tc >= 0 and (ct < 0 or tc < ct):
        return text[:tc].replace("<think>", "").strip(), text[tc:].replace("</think>", "").strip()
    if "</think>" in text:''')

# 2. streaming: hold back partial "<tool_call>" too, and treat it as the end of the thinking
old_hold = '''                        for k in range(min(len("</think>") - 1, len(new)), 0, -1):
                            if "</think>".startswith(new[-k:]):
                                hold = k; break'''
assert old_hold in s
s = s.replace(old_hold, '''                        for k in range(min(len("<tool_call>") - 1, len(new)), 0, -1):
                            if "</think>".startswith(new[-k:]) or "<tool_call>".startswith(new[-k:]):
                                hold = k; break''')
old_part = '''                            r, sep, rest = new.partition("</think>")'''
assert old_part in s
s = s.replace(old_part, '''                            tc, ct = new.find("<tool_call>"), new.find("</think>")
                            if tc >= 0 and (ct < 0 or tc < ct):   # THINK_TOOL_FIX
                                r, sep, rest = new[:tc], "</think>", new[tc:]
                            else:
                                r, sep, rest = new.partition("</think>")''')

# 3. guard phase tracking
old_g = '''                if in_think and "</think>" in text:'''
assert old_g in s
s = s.replace(old_g, '''                if in_think and ("</think>" in text or "<tool_call>" in text):''')
ast.parse(s); p.write_text(s); print("ok")
