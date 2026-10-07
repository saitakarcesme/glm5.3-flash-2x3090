import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
old = '''    def _car(self, li, sel, w, car):
        p = self.pool
'''
assert s.count(old) == 1
s = s.replace(old, '''    def _car(self, li, sel, w, car):
        p = self.pool
        if _car_ext(self.dev) is not None and w.dtype == torch.half and sel.is_contiguous() and w.is_contiguous():
            so, wo = torch.empty_like(sel), torch.empty_like(w)
            _CAR[self.dev.index or 0].car(sel, w, so, wo, p.slotof[li], self.res_addr + li * self.E * 4, car[0], car[1],
                                          float(car[2]), car[3])
            self.st["car_fused_calls"] += 1
            return so, wo
''')
old2 = 'class Nv2:\n'
s = s.replace(old2, '''_CAR = {}
def _car_ext(device):
    """claude-opt fused CAR kernel, built once per device (build dir inside the container)."""
    i = torch.device(device).index or 0
    if i not in _CAR:
        try:
            from torch.utils.cpp_extension import load
            b = f"/tmp/car_build_{i}"; os.makedirs(b, exist_ok=True)
            with torch.cuda.device(i):
                _CAR[i] = load(name=f"glm53_car_{i}", sources=["/opt/glm53/car_kernel/car.cu"], build_directory=b,
                               extra_cuda_cflags=["-O3"], verbose=False)
        except Exception as ex:
            print(f" !! CAR fused kernel unavailable ({ex}); torch fallback", flush=True)
            _CAR[i] = None
    return _CAR[i]


''' + old2, 1)
old3 = '        self.st["car_dropped_calls"] = 0\n'
s = s.replace(old3, old3 + '        self.res_addr = self.cbase_addr + self.off["res"]\n        _car_ext(self.dev)\n')
p.write_text(s); print("ok")
