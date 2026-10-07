"""claude-opt: refill the VRAM expert cache after an elastic prefill.
Patches expert_cache_claude.py (record the keys evicted from the flex chunks, refill after _elastic_exit) and
nv2_q.py (Nv2.refill: RAM-resident keys admitted directly, the rest read from NVMe into RAM in batches first)."""
import pathlib

ec = pathlib.Path("expert_cache_claude.py"); s = ec.read_text()
old = '''        if self.nv2 is not None:
            self.elastic_stats["wb"] = self.elastic_stats.get("wb", 0) + self.nv2.elastic_writeback(self.flex)
'''
assert s.count(old) == 1
s = s.replace(old, '''        if self.nv2 is not None and os.environ.get("GLM53_REFILL", "1") == "1":
            own = self.owner.cpu().numpy()
            self._flex_keys = [int(own[x]) for c in self.flex for x in range(c * self.spc, (c + 1) * self.spc) if own[x] >= 0]
''' + old)
old2 = '''        self.in_prefill = False
        self.elastic_stats["exit"] += 1
'''
assert s.count(old2) == 1
s = s.replace(old2, old2 + '''        keys = getattr(self, "_flex_keys", None)
        if keys and self.nv2 is not None and hasattr(self.nv2, "refill"):
            self._flex_keys = None
            t = time.perf_counter()
            n = self.nv2.refill(keys)
            self.elastic_stats["refilled"] = self.elastic_stats.get("refilled", 0) + n
            self.elastic_stats["refill_ms"] = round(self.elastic_stats.get("refill_ms", 0) + (time.perf_counter() - t) * 1e3, 1)
''')
if "\nimport time" not in s and "import time" not in s.split("\n\n")[0]:
    s = "import time\n" + s
ec.write_text(s)

nv = pathlib.Path("nv2_q.py"); s = nv.read_text()
old3 = "    def _post_warm_once(self):\n"
assert s.count(old3) == 1
s = s.replace(old3, '''    def refill(self, keys):
        """Re-admit experts evicted by an elastic prefill. Returns the number of keys VRAM-resident again."""
        p = self.pool
        keys = np.unique(np.asarray([k for k in keys if 0 <= k < self.K], np.int64))
        if len(keys) == 0:
            return 0
        for it in range(int(os.environ.get("GLM53_REFILL_ITERS", "12"))):
            torch.cuda.synchronize(self.dev)
            so = p.slotof.flatten().cpu().numpy()
            todo = keys[so[keys] < 0]
            if len(todo) == 0:
                break
            ks = self.e.state()[1].numpy()
            inram = todo[ks[todo] == 2]
            if len(inram) == 0:
                miss = todo[ks[todo] == 0]
                if len(miss) == 0:
                    break
                self.e.warm_read(torch.from_numpy(miss[: max(1, self.nram - 16)].copy()))
                ks = self.e.state()[1].numpy()
                inram = todo[ks[todo] == 2]
                if len(inram) == 0:
                    break
            with torch.cuda.device(self.dev):
                for li in np.unique(inram // self.E):
                    e = inram[inram // self.E == li] % self.E + p.first
                    for c in range(0, len(e), 256):
                        p.step(int(li), torch.from_numpy(e[c:c + 256].copy()).to(self.dev), True)
            torch.cuda.synchronize(self.dev)
            if self.wb_on:
                so = p.slotof.flatten().cpu().numpy()
                vk = keys[so[keys] >= 0]
                if len(vk):
                    self.e.drop_keys(torch.from_numpy(vk.copy()))
        self.e.nv_rows_all(self.L, self.E, p.slotof, self.a["home"], p.tabs)
        torch.cuda.synchronize(self.dev)
        so = p.slotof.flatten().cpu().numpy()
        return int((so[keys] >= 0).sum())

''' + old3)
nv.write_text(s)
print("ok")
