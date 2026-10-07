import pathlib
p = pathlib.Path("nv2_carf.py"); s = p.read_text()
old = '                self.car = [int(v[0]), int(v[1]), float(v[2]), int(v[3]), int(v[4])]\n'
assert s.count(old) == 1
s = s.replace(old, '                self.car = [int(v[0]), int(v[1]), float(v[2]), int(v[3]), int(v[4])] + ([int(v[5])] if len(v) > 5 else [])\n')
old2 = '        if self.prefetch and dec and li + 1 < self.L and bsz <= 8:\n'
assert s.count(old2) == 1
s = s.replace(old2, '        if self.prefetch and (len(car) < 6 or car[5]) and dec and li + 1 < self.L and bsz <= 8:\n')
p.write_text(s); print("ok")
