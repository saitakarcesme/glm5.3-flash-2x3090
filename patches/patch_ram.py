import pathlib
p = pathlib.Path("nv2.py"); s = p.read_text()
old = 'want = g("GLM53_NV_RAM_GB", "auto")'
assert s.count(old) == 1
s = s.replace(old, 'want = g(f"GLM53_NV_RAM_GB_{dev_idx}", g("GLM53_NV_RAM_GB", "auto"))  # claude-opt: per-GPU RAM tier')
p.write_text(s)
