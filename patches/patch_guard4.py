"""claude-opt guard v4 (Terminal-Bench): never let one agent turn spin.
  * after the 3rd loop restart, a further loop ends the turn: the text before the loop is returned with finish=stop
  * agent requests (tools present) end after GLM53_AGENT_TURN_CAP tokens (default 12288) without a tool call"""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "AGENT_TURN_CAP" not in s
s = s.replace("ACT_BUDGET = int(", 'AGENT_TURN_CAP = int(os.environ.get("GLM53_AGENT_TURN_CAP", "12288"))\nACT_BUDGET = int(', 1)
old = """                    elif LOOP_GUARD and restarts < 3:
                        full = ctx_extra + text
                        i = _loop_start(full)
                        if i is not None and i >= len(ctx_extra):
                            restart = ("loop", full[:i], n)"""
assert old in s
new = """                    elif LOOP_GUARD:
                        full = ctx_extra + text
                        i = _loop_start(full)
                        if i is not None and i >= len(ctx_extra):
                            if restarts < 3:
                                restart = ("loop", full[:i], n)
                            else:   # GUARD v4: stop spinning, end the turn with what came before the loop
                                G["stats"]["guard_endturn"] = G["stats"].get("guard_endturn", 0) + 1
                                print(f" -- guard: 4th loop, ending turn after {used + n} tokens", flush=True)
                                await g.aclose()
                                yield shown + text[:max(0, i - len(ctx_extra))], used + n, {"type": "stop", "reason": "guard_endturn"}
                                return
                    if (not restart and tools_present and AGENT_TURN_CAP and used + n >= AGENT_TURN_CAP
                            and "<tool_call>" not in text):
                        G["stats"]["guard_turncap"] = G["stats"].get("guard_turncap", 0) + 1
                        print(f" -- guard: agent turn cap {AGENT_TURN_CAP} reached, ending turn", flush=True)
                        await g.aclose()
                        yield shown + text, used + n, {"type": "stop", "reason": "guard_turncap"}
                        return"""
s = s.replace(old, new)
ast.parse(s); p.write_text(s); print("ok")
