import pathlib
p = pathlib.Path("nv2_carf.py"); s = p.read_text()
old = "                                          float(car[2]), car[3])\n"
assert s.count(old) == 1
s = s.replace(old, "                                          float(car[2]), car[3], float(car[6]) if len(car) > 6 else 1.01)\n")
old2 = "+ ([int(v[5])] if len(v) > 5 else [])\n"
assert s.count(old2) == 1
s = s.replace(old2, "+ ([int(v[5])] if len(v) > 5 else []) + ([float(v[6])] if len(v) > 6 else [])\n")
s = s.replace('name=f"glm53_car_{i}"', 'name=f"glm53_car2_{i}"')
p.write_text(s); print("ok")
