import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
old = "        if k * unit >= 240 and k >= 4:\n            return off + j"
assert old in s
s = s.replace(old, "        alnum = any(c.isalnum() for c in u)\n        if k >= 6 and k * unit >= (400 if alnum else 1000):\n            return off + j")
old2 = '            print(f" -- guard: {kind} restart #{restarts} after {used} tokens (exact={forced})", flush=True)'
assert old2 in s
s = s.replace(old2, '            print(f" -- guard: {kind} restart #{restarts} after {used} tokens (exact={forced}) cut-tail={cut[-120:]!r}", flush=True)')
ast.parse(s); p.write_text(s); print("ok")
