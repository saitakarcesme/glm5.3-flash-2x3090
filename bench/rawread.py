import os, sys, time, random, threading, mmap
path = sys.argv[1]; rec = 6291456
fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
size = os.fstat(fd).st_size; nrec = size // rec
def temp():
    import glob
    out = []
    for f in glob.glob("/sys/class/nvme/nvme0/hwmon*/temp*_input"):
        out.append(int(open(f).read()) // 1000)
    return out
for threads, piece in [(4, rec), (8, rec), (16, rec), (8, 2359296), (16, 2359296), (32, 1048576)]:
    n_total = 400; lock = threading.Lock(); cnt = [0]
    keys = random.Random(threads).sample(range(nrec), n_total)
    def w(tid):
        buf = mmap.mmap(-1, rec)
        while True:
            with lock:
                if cnt[0] >= n_total: return
                k = keys[cnt[0]]; cnt[0] += 1
            off = k * rec
            for p in range(0, rec, piece):
                os.preadv(fd, [memoryview(buf)[p:p+piece]], off + p)
    t = time.perf_counter()
    ts = [threading.Thread(target=w, args=(i,)) for i in range(threads)]
    [x.start() for x in ts]; [x.join() for x in ts]
    dt = time.perf_counter() - t
    print(f"threads {threads:2d} piece {piece//1024:5d}KB: {n_total*rec/dt/1e9:.2f} GB/s  temp {temp()}", flush=True)
