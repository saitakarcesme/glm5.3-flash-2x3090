"""claude-opt: one log line per finished (or cut) job: prompt tokens, prefilled tokens, output tokens, time to first
token, decode time and decode tok/s. Used for the per-session time / context / speed / token report."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "REQLOG" not in s
old = """                print(f" -- pfx P={len(_cur)} common={_c} new={len(_cur) - _c} ttft={time.time() - _t0:.1f}s cache_hit_rate={_hr}", flush=True)"""
assert old in s
s = s.replace(old, old + "\n                _tf = time.time()", 1)
s = s.replace("""    G["pfx_prev"] = _cur; _t0 = time.time(); _first = True""",
              """    G["pfx_prev"] = _cur; _t0 = time.time(); _first = True; _tf = None""", 1)
old2 = """    finally:
        if not done:   # client went away: stop the job, free the slot"""
assert old2 in s
new2 = """    finally:
        # REQLOG
        _te = time.time(); _dec = (_te - _tf) if _tf else 0.0
        print(f" -- req P={len(_cur)} prefill={len(_cur) - _c} out={n} ttft={((_tf or _te) - _t0):.1f}s "
              f"decode={_dec:.1f}s tok_s={(n / _dec) if _dec > 0 else 0:.1f} done={done}", flush=True)
        if not done:   # client went away: stop the job, free the slot"""
s = s.replace(old2, new2, 1)
ast.parse(s); p.write_text(s); print("ok")
