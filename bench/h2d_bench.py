import torch, time
from exllamav3.ext import exllamav3_ext as xe
N = 64 * 6291456  # 64 experts
for d in range(torch.cuda.device_count()):
    torch.cuda.set_device(d)
    with torch.cuda.device(d):
        h = torch.empty(N, dtype=torch.uint8).pin_memory()
    h.fill_(1)
    g = torch.empty(N, dtype=torch.uint8, device=d)
    def tm(fn, reps=5):
        fn(); torch.cuda.synchronize(d)
        t = time.perf_counter()
        for _ in range(reps): fn()
        torch.cuda.synchronize(d)
        return N * reps / (time.perf_counter() - t) / 1e9
    dma = tm(lambda: g.copy_(h, non_blocking=True))
    v = xe.pinned_cuda_view(h, d)
    zc = tm(lambda: g.copy_(v))
    d2h = tm(lambda: h.copy_(g, non_blocking=True))
    # one expert at a time (latency-dominated small copies)
    def per_expert():
        for i in range(64):
            g[i*6291456:(i+1)*6291456].copy_(h[i*6291456:(i+1)*6291456], non_blocking=True)
    pe = tm(per_expert)
    print(f"GPU{d}: H2D DMA {dma:.1f} GB/s | H2D zero-copy SM {zc:.1f} GB/s | D2H DMA {d2h:.1f} GB/s | per-expert DMA {pe:.1f} GB/s", flush=True)
    del g, h, v; torch.cuda.empty_cache()
