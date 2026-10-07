import pathlib
p = pathlib.Path("nv2.py"); s = p.read_text()
old_r = 'rcpus = _cpus(g("GLM53_NV_READER_CPUS", "26-39"))'
assert old_r in s
s = s.replace(old_r, 'rcpus = _cpus(g(f"GLM53_NV_READER_CPUS_{dev_idx}", g("GLM53_NV_READER_CPUS", "26-39")))  # claude-opt: per-GPU override')
old_c = 'int(g("GLM53_NV_CTL_CPU", "25"))'
assert s.count(old_c) == 1
s = s.replace(old_c, 'int(g(f"GLM53_NV_CTL_CPU_{dev_idx}", g("GLM53_NV_CTL_CPU", "25")))')
p.write_text(s)
