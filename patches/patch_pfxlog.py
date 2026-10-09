"""claude-opt: prefix-reuse diagnostics. Each job logs prompt length, the common prefix with the previous prompt,
cache hit rate and time to first token; the last prompts are kept in /tmp/glm53_prompts/ for diffing."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "PFXLOG" not in s
old = """    G["stats"]["requests"] += 1
    n, text, done = 0, "", False"""
assert old in s
new = """    G["stats"]["requests"] += 1
    # PFXLOG: how much of this prompt matches the previous one (prefix reuse diagnostics)
    _prev = G.get("pfx_prev"); _cur = ids[0].tolist(); _c = 0
    if _prev is not None:
        _m = min(len(_prev), len(_cur))
        while _c < _m and _prev[_c] == _cur[_c]: _c += 1
    G["pfx_prev"] = _cur; _t0 = time.time(); _first = True
    try:
        os.makedirs("/tmp/glm53_prompts", exist_ok=True); _k = G["stats"]["requests"] % 6
        open(f"/tmp/glm53_prompts/p{_k}.txt", "w").write(tok.decode(ids, decode_special_tokens=True)[0] if hasattr(tok, "decode") else "")
    except Exception as _e:
        print(" -- pfxlog dump failed", _e, flush=True)
    n, text, done = 0, "", False"""
s = s.replace(old, new, 1)
old2 = """            chunk = r.get("text") or ""
            tids = r.get("token_ids")"""
assert old2 in s
new2 = """            if _first:
                _first = False
                try: _hr = gen.get_cache_stats().get("hit_rate")
                except Exception: _hr = None
                print(f" -- pfx P={len(_cur)} common={_c} new={len(_cur) - _c} ttft={time.time() - _t0:.1f}s cache_hit_rate={_hr}", flush=True)
            chunk = r.get("text") or ""
            tids = r.get("token_ids")"""
s = s.replace(old2, new2, 1)
if "\nimport time" not in s and "import time" not in s.split("\n\n")[0]:
    s = "import time\n" + s
ast.parse(s); p.write_text(s); print("ok")
