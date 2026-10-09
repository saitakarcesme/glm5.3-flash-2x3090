"""claude-opt guard v3 (Terminal-Bench findings):
  * structured agent output (tool-call / JSON batches like {"keystrokes": ..., "duration": 0.1}) is legitimately
    repetitive: inside it the n-gram rule is off and the unit rule needs >= 12 repeats.
  * the loop fallback is configurable (GLM53_GUARD_FALLBACK, default gentle CAR "3 1 0.10 1 1 0 0.30 1.5") instead of
    exact experts, which is too slow for agent timeouts."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "GUARD_FALLBACK" not in s
old = 'def _loop_start(t):\n    """Index where a degenerate loop begins in t, or None."""\n    tail = t[-3000:]'
assert old in s
s = s.replace(old, '''GUARD_FALLBACK = [float(x) if "." in x else int(x) for x in os.environ.get("GLM53_GUARD_FALLBACK", "3 1 0.10 1 1 0 0.30 1.5").split()]


def _structured(t):
    """True if the recent text is a tool call or a JSON command batch (legitimately repetitive)."""
    w = t[-3000:]
    return ("<tool_call>" in w or "<arg_value>" in w or w.count('": ') >= 12 or w.count("keystrokes") >= 3)


def _loop_start(t):
    """Index where a degenerate loop begins in t, or None."""
    structured = _structured(t)
    tail = t[-3000:]''')
old2 = "        if k >= (6 if unit < 200 else 4) and k * unit >= (400 if alnum else 1000):\n            return off + j"
assert old2 in s
s = s.replace(old2, "        need = 12 if structured else (6 if unit < 200 else 4)\n        if k >= need and k * unit >= (400 if alnum else 1000):\n            return off + j")
old3 = "    w = t[-3000:]\n    words = _WORD.findall(w)\n    if len(words) >= 200:"
assert old3 in s
s = s.replace(old3, "    if structured:\n        return None\n    w = t[-3000:]\n    words = _WORD.findall(w)\n    if len(words) >= 200:")
old4 = "                _nv2.CAR_OVERRIDE = [0, 2, 0.0, 1, 1, 1]"
assert old4 in s
s = s.replace(old4, "                _nv2.CAR_OVERRIDE = list(GUARD_FALLBACK)")
ast.parse(s); p.write_text(s); print("ok")
