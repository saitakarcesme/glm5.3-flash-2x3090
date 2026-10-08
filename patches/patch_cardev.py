import pathlib
p = pathlib.Path("nv2_q.py"); s = p.read_text()
old = '                v = open("/tmp/glm53_car").read().split()\n'
assert s.count(old) == 1
s = s.replace(old, '''                f = f"/tmp/glm53_car_{self.dev.index or 0}"   # claude-opt: optional per-GPU override
                v = open(f if os.path.exists(f) else "/tmp/glm53_car").read().split()
''')
p.write_text(s); print("ok")
