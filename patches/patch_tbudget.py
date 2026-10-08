"""claude-opt: per-request thinking budget. Body field "thinking_budget" (tokens; 0 = off) overrides GLM53_THINK_BUDGET,
so benchmarks can run with full reasoning like the official evaluations while agent clients keep the default guard."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "thinking_budget" not in s
s = s.replace("async def guarded_job(ids, sp, stops, thinking, tools_present=False):",
              "async def guarded_job(ids, sp, stops, thinking, tools_present=False, think_budget=None):")
old = "    budget = THINK_BUDGET if thinking else 0\n"
assert old in s
s = s.replace(old, "    budget = (THINK_BUDGET if think_budget is None else int(think_budget)) if thinking else 0\n")
head, sep, tail = s.partition("async def completions(")
assert head.count("guarded_job(ids, sp, stops, thinking, bool(tools))") == 2
head = head.replace("guarded_job(ids, sp, stops, thinking, bool(tools))", 'guarded_job(ids, sp, stops, thinking, bool(tools), body.get("thinking_budget"))')
s = head + sep + tail
ast.parse(s); p.write_text(s); print("ok")
