import pathlib
p = pathlib.Path("nv2.py"); s = p.read_text()
# 1) device view of the mapped RAM-residency table + runtime CAR config
anchor = '        # ---- host engine\n'
assert s.count(anchor) == 1
s = s.replace(anchor, '''        # ---- claude-opt: cache-aware routing (CAR). Runtime config file /tmp/glm53_car: "mode keep thresh renorm small"
        #   mode 0 off | 1 drop non-VRAM picks | 2 drop picks neither in VRAM nor RAM; keep = top-k (by weight) always computed;
        #   thresh = also keep picks with weight >= thresh * row sum; renorm = rescale kept weights to the original row sum;
        #   small = also apply to small (non-decode, non-staged) forwards
        from exllamav3.ext import exllamav3_ext as _xe
        self.res_dev = _xe.pinned_cuda_view(self.ct[self.off["res"]: self.off["res"] + self.K * 4], dev_idx).view(torch.int32)
        self.car = [int(g("GLM53_CAR", "0")), int(g("GLM53_CAR_KEEP", "2")), float(g("GLM53_CAR_THRESH", "0")),
                    int(g("GLM53_CAR_RENORM", "1")), int(g("GLM53_CAR_SMALL", "1"))]
        self.st["car_dropped_calls"] = 0
''' + anchor)
# 2) watchdog polls the runtime config
old_wd = '            time.sleep(1.0)\n'
assert s.count(old_wd) == 1
s = s.replace(old_wd, '''            time.sleep(1.0)
            try:
                v = open("/tmp/glm53_car").read().split()
                self.car = [int(v[0]), int(v[1]), float(v[2]), int(v[3]), int(v[4])]
            except Exception:
                pass
''')
# 3) apply in layer() for non-staged calls
old_l = '''        if p.stage_n:
            p._stage_hook_nv2(li, n)
        dec = n <= p.admit_max
'''
assert s.count(old_l) == 1
s = s.replace(old_l, '''        if p.stage_n:
            p._stage_hook_nv2(li, n)
        car = self.car
        if car[0] and (n <= p.admit_max or car[4]):
            sel, w = self._car(li, sel, w, car)
        dec = n <= p.admit_max
''')
# 4) the CAR function
old_p = '    def _predict(self, lj, z, bsz):\n'
s = s.replace(old_p, '''    def _car(self, li, sel, w, car):
        p = self.pool
        k = sel.shape[-1]
        s2 = sel.reshape(-1, k).long()
        loc = s2.clamp(0, self.E - 1)
        keep = p.slotof[li][loc] >= 0
        if car[0] == 2:
            keep |= self.res_dev[li * self.E + loc] == 1
        wf = w.reshape(-1, k).float()
        if car[1] > 0:
            keep |= wf.argsort(-1, descending=True).argsort(-1) < car[1]
        tot = wf.sum(-1, keepdim=True)
        if car[2] > 0:
            keep |= wf >= car[2] * tot
        keep &= s2 >= 0
        wn = torch.where(keep, wf, torch.zeros_like(wf))
        if car[3]:
            wn = wn * (tot / wn.sum(-1, keepdim=True).clamp_min(1e-20))
        so = torch.where(keep, s2, torch.full_like(s2, -1))
        self.st["car_dropped_calls"] += 1
        return so.to(sel.dtype).view(sel.shape), wn.to(w.dtype).view(w.shape)

''' + old_p)
p.write_text(s)
print("patched")
