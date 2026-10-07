import os, sys, time, random, threading, mmap, glob
path = sys.argv[1]; dur = float(sys.argv[2]); rec = 6291456
fd = os.open(path, os.O_RDONLY | os.O_DIRECT); nrec = os.fstat(fd).st_size // rec
temps = lambda: [int(open(f).read()) // 1000 for f in sorted(glob.glob("/sys/class/nvme/nvme0/hwmon*/temp*_input"))]
done = [0]; stop = time.time() + dur
def w(i):
    buf = mmap.mmap(-1, rec); r = random.Random(i)
    while time.time() < stop:
        os.preadv(fd, [buf], r.randrange(nrec) * rec); done[0] += 1
ts = [threading.Thread(target=w, args=(i,)) for i in range(4)]; [t.start() for t in ts]
last, lt = 0, time.time()
while time.time() < stop:
    time.sleep(5); n = done[0]; t = time.time()
    print(f"{(n-last)*rec/(t-lt)/1e9:.2f} GB/s temps {temps()}", flush=True); last, lt = n, t
[t.join() for t in ts]
