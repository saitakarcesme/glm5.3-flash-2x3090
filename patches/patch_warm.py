import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
old = '''    def post_warm(self):
        p = self.pool
        torch.cuda.synchronize(self.dev)
        so = p.slotof.flatten().cpu().numpy()
        vk = np.nonzero(so >= 0)[0]
        nd = 0
        if self.wb_on:
'''
assert s.count(old) == 1
s = s.replace(old, '''    def post_warm(self):
        # claude-opt: iterate (VRAM warm from RAM -> drop RAM copies -> refill RAM by rank) until VRAM stops growing, so a
        # GPU with a small RAM tier still starts with a full VRAM cache
        p = self.pool
        prev = -1
        for it in range(int(os.environ.get("GLM53_WARM_ITERS", "12"))):
            torch.cuda.synchronize(self.dev)
            nv = int((p.slotof >= 0).sum().item())
            if nv <= prev:
                break
            prev = nv
            self._post_warm_once()
            if self.scores:
                p.warm(self.scores)
        torch.cuda.synchronize(self.dev)
        NT._log(f"nv2 iterative warm: {int((p.slotof >= 0).sum().item())} VRAM-resident of {p.S} slots after {it + 1} rounds")
        self._post_warm_once()

    def _post_warm_once(self):
        p = self.pool
        torch.cuda.synchronize(self.dev)
        so = p.slotof.flatten().cpu().numpy()
        vk = np.nonzero(so >= 0)[0]
        nd = 0
        if self.wb_on:
''')
p.write_text(s); print("ok")
