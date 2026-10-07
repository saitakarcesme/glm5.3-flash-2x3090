import pathlib
p = pathlib.Path("nv2_carf.py"); s = p.read_text()
old = '''            time.sleep(1.0)
            try:
                v = open("/tmp/glm53_car").read().split()
'''
assert s.count(old) == 1
s = s.replace(old, '''            time.sleep(1.0)
            if (self.dev.index or 0) == 0 and os.path.exists("/tmp/glm53_prof"):
                try:
                    os.remove("/tmp/glm53_prof"); _gpu_trace()
                except Exception as ex:
                    print(f" !! gpu trace failed: {ex}", flush=True)
            try:
                v = open("/tmp/glm53_car").read().split()
''')
s = s.replace("_CAR = {}\n", '''_CAR = {}
def _gpu_trace(sec=4.0):
    """claude-opt: CUPTI kernel trace for sec seconds; writes /tmp/glm53_trace.json with per-device busy time and top kernels."""
    from torch.profiler import profile, ProfilerActivity
    with profile(activities=[ProfilerActivity.CUDA]) as pr:
        time.sleep(sec)
    ev = [e for e in pr.events() if e.device_type.name == "CUDA"]
    out = {}
    for d in sorted({e.device_index for e in ev}):
        ks = sorted([(e.time_range.start, e.time_range.end, e.name) for e in ev if e.device_index == d])
        busy, cur_s, cur_e = 0, None, None
        for a, b, _ in ks:
            if cur_e is None or a > cur_e:
                if cur_e is not None: busy += cur_e - cur_s
                cur_s, cur_e = a, b
            else:
                cur_e = max(cur_e, b)
        if cur_e is not None: busy += cur_e - cur_s
        span = (ks[-1][1] - ks[0][0]) if ks else 1
        agg = collections.Counter(); cnt = collections.Counter()
        for a, b, n in ks: agg[n[:90]] += b - a; cnt[n[:90]] += 1
        out[str(d)] = {"kernels": len(ks), "span_us": span, "busy_us": busy, "busy_frac": busy / max(1, span),
                       "top": [(n, round(t / 1e3, 2), cnt[n]) for n, t in agg.most_common(25)]}
    json.dump(out, open("/tmp/glm53_trace.json", "w"), indent=1)
    print(" -- gpu trace written", flush=True)

''', 1)
p.write_text(s); print("ok")
