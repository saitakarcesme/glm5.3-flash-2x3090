"""claude-opt: act budget. In agent requests (tools present), if the visible answer grows past GLM53_ACT_BUDGET tokens
without starting a tool call, append a one-line nudge and continue (once per request)."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "def guarded_job" in s and "ACT_BUDGET" not in s
s = s.replace('THINK_CLOSE = "\\n\\nI have thought about this enough; now I will carry it out.\\n</think>\\n\\n"\n',
              'THINK_CLOSE = "\\n\\nI have thought about this enough; now I will carry it out.\\n</think>\\n\\n"\n'
              'ACT_BUDGET = int(os.environ.get("GLM53_ACT_BUDGET", "3000"))\n'
              'ACT_NUDGE = "\\n\\nEnough analysis — I will make the tool call now.\\n"\n')
s = s.replace("async def guarded_job(ids, sp, stops, thinking):", "async def guarded_job(ids, sp, stops, thinking, tools_present=False):")
s = s.replace("    forced = False\n    try:", "    forced = False\n    acted = False\n    try:")
old = """                    if in_think and budget and used + n >= budget:
                        restart = ("budget", ctx_extra + text, n)"""
assert old in s
new = """                    if in_think and budget and used + n >= budget:
                        restart = ("budget", ctx_extra + text, n)
                    elif (tools_present and not in_think and not acted and ACT_BUDGET and "<tool_call>" not in text
                          and len(text.split("</think>")[-1]) / 3.6 > ACT_BUDGET):
                        restart = ("act", ctx_extra + text, n)"""
s = s.replace(old, new)
old2 = """            if in_think:   # end the thinking at the cut and move on to the answer"""
assert old2 in s
s = s.replace(old2, """            if kind == "act":
                acted = True
                shown = shown + text + ACT_NUDGE
                ctx_extra = cut + ACT_NUDGE
            elif in_think:   # end the thinking at the cut and move on to the answer""")
# chat(): two call sites (stream + non-stream) get the tools flag; completions(): plain prompt, no thinking, no tools
head, sep, tail = s.partition("async def completions(")
head = head.replace("g = guarded_job(ids, sp, stops, thinking)", "g = guarded_job(ids, sp, stops, thinking, bool(tools))")
head = head.replace("async for text, n, fin in guarded_job(ids, sp, stops, thinking):", "async for text, n, fin in guarded_job(ids, sp, stops, thinking, bool(tools)):")
tail = tail.replace("g = guarded_job(ids, sp, stops, thinking)", "g = guarded_job(ids, sp, stops, False)")
s = head + sep + tail
assert s.count("bool(tools))") == 2 and "guarded_job(ids, sp, stops, False)" in s
ast.parse(s); p.write_text(s); print("ok")
