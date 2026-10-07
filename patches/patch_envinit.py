import pathlib
p = pathlib.Path("nv2_carf.py"); s = p.read_text()
old = '''                    int(g("GLM53_CAR_RENORM", "1")), int(g("GLM53_CAR_SMALL", "1"))]\n'''
assert s.count(old) == 1
s = s.replace(old, '''                    int(g("GLM53_CAR_RENORM", "1")), int(g("GLM53_CAR_SMALL", "1")), int(g("GLM53_CAR_PF", "1")),
                    float(g("GLM53_CAR_TNV", "1.01"))]\n''')
p.write_text(s); print("ok")
