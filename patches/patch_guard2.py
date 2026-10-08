"""claude-opt guard v2:
  * loop detector: units up to 600 chars over a 3000-char window; n-gram rule 0.75 over >= 200 words in 3000 chars
  * think-stop guard: in an agent request, a turn that ends (EOS) while still inside the think block, with no answer and
    no tool call, is closed and continued (exact experts) instead of being returned as an empty turn."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "THINK_STOP_GUARD" not in s

old = s[s.index("def _loop_start(t):"):s.index("async def with_keepalive(")]
new = '''def _loop_start(t):
    """Index where a degenerate loop begins in t, or None."""
    tail = t[-3000:]
    off = len(t) - len(tail)
    for unit in range(1, 601):
        if unit * 3 > len(tail):
            break
        u = tail[-unit:]
        if not u.strip():
            continue
        k, j = 1, len(tail) - unit
        while j - unit >= 0 and tail[j - unit:j] == u:
            k += 1; j -= unit
        alnum = any(c.isalnum() for c in u)
        if k >= (6 if unit < 200 else 4) and k * unit >= (400 if alnum else 1000):
            return off + j
    w = t[-3000:]
    words = _WORD.findall(w)
    if len(words) >= 200:
        g = [tuple(words[i:i + 8]) for i in range(len(words) - 7)]
        if 1 - len(set(g)) / len(g) > 0.75:
            return len(t) - len(w)
    return None


KEEPALIVE_S = float(os.environ.get("GLM53_SSE_KEEPALIVE_S", "10"))


'''
assert "KEEPALIVE_S = float" in old
s = s.replace(old, new)

# think-stop guard: inside guarded_job, before yielding a final event that ends inside thinking
old2 = """                if restart:
                    break
                yield shown + text, used + n, fin"""
assert old2 in s
new2 = """                if (not restart and fin is not None and fin.get("type") == "stop" and tools_present and in_think
                        and restarts < 3):   # THINK_STOP_GUARD: an agent turn must not end inside its think block
                    restart = ("thinkstop", ctx_extra + text, n)
                if restart:
                    break
                yield shown + text, used + n, fin"""
s = s.replace(old2, new2)
old3 = """            if kind == "loop" and not forced:"""
assert old3 in s
s = s.replace(old3, """            if kind in ("loop", "thinkstop") and not forced:""")
ast.parse(s); p.write_text(s); print("ok")
