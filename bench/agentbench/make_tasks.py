"""Agent reliability suite: 5 small realistic coding-agent tasks, each a directory with starting files, a prompt and an
automatic checker (stdlib only; run inside a --network none container). Writes tasks/<name>/{files..., PROMPT.txt, check.py}."""
import pathlib, textwrap, json
T = pathlib.Path("tasks")

def task(name, prompt, files, check):
    d = T / name; (d / "start").mkdir(parents=True, exist_ok=True)
    for p, c in files.items():
        f = d / "start" / p; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(textwrap.dedent(c).lstrip())
    (d / "PROMPT.txt").write_text(textwrap.dedent(prompt).strip() + "\n")
    (d / "check.py").write_text(textwrap.dedent(check).lstrip())

# 1. multi-file static site with exact requirements
task("webpage", """
    Create a small static website in ./site with three files: index.html, style.css and app.js (no CDNs, no frameworks).
    Requirements:
    - <title> is exactly "Rig Report".
    - A <nav> with three links to sections with ids "hardware", "results" and "notes".
    - The "results" section contains a <table> with a header row and exactly these three data rows:
      Start profile | 8.5 tok/s ; Exact profile | 14.1 tok/s ; Fast profile | 54.4 tok/s
    - The "results" section also contains an inline <svg> bar chart with one <rect> bar per row (3 bars), bar heights
      proportional to the three values.
    - A <button id="theme"> that toggles the class "dark" on <body>; the click handler lives in app.js.
    - style.css defines a rule for body.dark.
    - index.html links style.css and app.js.
    """, {"README.md": "# rig report\nBuild the site described in the task.\n"}, """
    import re, sys, pathlib
    s = pathlib.Path("site"); h = (s / "index.html").read_text(); css = (s / "style.css").read_text(); js = (s / "app.js").read_text()
    ok = []
    ok.append(re.search(r"<title>\\s*Rig Report\\s*</title>", h) is not None)
    ok.append(all(re.search(fr'id=["\\']{i}["\\']', h) for i in ("hardware", "results", "notes")))
    ok.append(all(re.search(fr'href=["\\']#{i}["\\']', h) for i in ("hardware", "results", "notes")))
    res = h[h.find('id="results"') if 'id="results"' in h else h.find("id='results'"):]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", res, re.S)
    data = [r for r in rows if "<td" in r]
    ok.append(len(data) == 3 and all(v in res for v in ("8.5", "14.1", "54.4")))
    ok.append(len(re.findall(r"<rect", res)) >= 3 and "<svg" in res)
    ok.append(re.search(r'<button[^>]*id=["\\']theme["\\']', h) is not None and "dark" in js and "addEventListener" in js or "onclick" in js)
    ok.append(re.search(r"body\\.dark", css) is not None)
    ok.append("style.css" in h and "app.js" in h)
    print(sum(ok), len(ok)); sys.exit(0 if all(ok) else 1)
    """)

# 2. bug fix with tests
task("bugfix", """
    The tests in tests/test_intervals.py fail. Fix the bug(s) in intervals.py so that `python -m unittest discover -s tests`
    passes. Do not modify the tests.
    """, {
    "intervals.py": '''
    def merge(intervals):
        """Merge overlapping closed intervals [a, b]; touching intervals ([1,2],[2,3]) merge too. Returns sorted list."""
        out = []
        for a, b in intervals:
            if out and a < out[-1][1]:
                out[-1][1] = b
            else:
                out.append([a, b])
        return out


    def total_length(intervals):
        """Sum of lengths of the merged intervals."""
        return sum(b - a for a, b in merge(intervals))
    ''',
    "tests/test_intervals.py": '''
    import unittest, sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from intervals import merge, total_length

    class T(unittest.TestCase):
        def test_basic(self): self.assertEqual(merge([[1, 3], [2, 6], [8, 10]]), [[1, 6], [8, 10]])
        def test_unsorted(self): self.assertEqual(merge([[8, 10], [1, 3], [2, 6]]), [[1, 6], [8, 10]])
        def test_touch(self): self.assertEqual(merge([[1, 2], [2, 3]]), [[1, 3]])
        def test_contained(self): self.assertEqual(merge([[1, 10], [2, 3]]), [[1, 10]])
        def test_len(self): self.assertEqual(total_length([[1, 10], [2, 3], [12, 14]]), 11)
        def test_empty(self): self.assertEqual(merge([]), [])

    if __name__ == "__main__": unittest.main()
    '''}, """
    import subprocess, sys, hashlib, pathlib
    t = pathlib.Path("tests/test_intervals.py").read_text()
    if "test_contained" not in t or "total_length([[1, 10], [2, 3], [12, 14]]), 11" not in t: print("tests modified"); sys.exit(1)
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], capture_output=True, text=True)
    print(r.stderr[-300:]); sys.exit(r.returncode)
    """)

# 3. feature: CLI option + docs
task("feature", """
    Add a --top N option to report.py (default 3) that limits how many rows are printed, keeping the existing sort
    (highest score first). Also document the option in README.md under a "## Usage" heading. Make sure
    `python report.py data.csv --top 2` prints exactly two data lines after the header line.
    """, {
    "report.py": '''
    import csv, sys

    def main():
        path = sys.argv[1]
        rows = list(csv.DictReader(open(path)))
        rows.sort(key=lambda r: -float(r["score"]))
        print("name,score")
        for r in rows[:3]:
            print(f"{r['name']},{r['score']}")

    if __name__ == "__main__":
        main()
    ''',
    "data.csv": "name,score\nalpha,3.5\nbeta,9.25\ngamma,7\ndelta,1\nepsilon,8\n",
    "README.md": "# report\nPrints the highest-scoring rows of a CSV file.\n"}, """
    import subprocess, sys, pathlib
    def run(*a): return subprocess.run([sys.executable, "report.py", "data.csv", *a], capture_output=True, text=True).stdout.strip().splitlines()
    ok = [run("--top", "2") == ["name,score", "beta,9.25", "epsilon,8"],
          run() == ["name,score", "beta,9.25", "epsilon,8", "gamma,7"],
          run("--top", "5")[-1] == "delta,1",
          "## Usage" in pathlib.Path("README.md").read_text() and "--top" in pathlib.Path("README.md").read_text()]
    print(ok); sys.exit(0 if all(ok) else 1)
    """)

# 4. data processing to JSON
task("data", """
    logs/requests.log contains one request per line: "<iso-timestamp> <endpoint> <status> <latency_ms>".
    Write a script stats.py that reads it and writes stats.json with: "total" (number of requests), "errors" (status >= 500),
    "p50_ms" and "p90_ms" (nearest-rank percentiles of latency over all requests), and "by_endpoint" (object mapping each
    endpoint to its request count). Run the script so stats.json exists.
    """, {"logs/requests.log": "\n".join(
        f"2026-10-08T10:{i // 60:02d}:{i % 60:02d}Z /{['api/users', 'api/orders', 'health'][i % 3]} {[200, 200, 500, 404, 200, 503][i % 6]} {(i * 37) % 250 + 5}"
        for i in range(120)) + "\n"}, """
    import json, sys, math
    lines = [l.split() for l in open("logs/requests.log") if l.strip()]
    lat = sorted(int(l[3]) for l in lines)
    nr = lambda p: lat[max(0, math.ceil(p / 100 * len(lat)) - 1)]
    want = {"total": len(lines), "errors": sum(int(l[2]) >= 500 for l in lines), "p50_ms": nr(50), "p90_ms": nr(90)}
    by = {}
    for l in lines: by[l[1]] = by.get(l[1], 0) + 1
    got = json.load(open("stats.json"))
    ok = [got.get(k) == v for k, v in want.items()] + [got.get("by_endpoint") == by]
    print(ok, want); sys.exit(0 if all(ok) else 1)
    """)

# 5. refactor across files
task("refactor", """
    Rename the function `calc_total` to `compute_total` everywhere in this package (definition and all call sites), and
    make it accept an optional keyword argument `tax` (default 0.0) that multiplies the result by (1 + tax).
    `python -m unittest discover -s tests` must pass, and no file may still mention calc_total.
    """, {
    "shop/__init__.py": "",
    "shop/cart.py": '''
    def calc_total(items):
        return round(sum(p * q for p, q in items), 2)
    ''',
    "shop/checkout.py": '''
    from .cart import calc_total

    def checkout(items):
        return {"total": calc_total(items), "count": sum(q for _, q in items)}
    ''',
    "tests/test_shop.py": '''
    import unittest, sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from shop.cart import compute_total
    from shop.checkout import checkout

    class T(unittest.TestCase):
        def test_total(self): self.assertEqual(compute_total([(2.5, 2), (1.0, 3)]), 8.0)
        def test_tax(self): self.assertEqual(compute_total([(10.0, 1)], tax=0.2), 12.0)
        def test_checkout(self): self.assertEqual(checkout([(2.5, 2)]), {"total": 5.0, "count": 2})

    if __name__ == "__main__": unittest.main()
    '''}, """
    import subprocess, sys, pathlib
    left = [str(p) for p in pathlib.Path(".").rglob("*.py") if p.name != ".check.py" and "calc_total" in p.read_text()]
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], capture_output=True, text=True)
    print(left, r.stderr[-200:]); sys.exit(0 if (not left and r.returncode == 0) else 1)
    """)

# 6. the recorded failure: synthesise a real website from long research notes (notes copied in by the runner)
task("report_site", """
    ./research contains the notes and raw results of an inference-optimization study (GLM-5.3-Flash on 2x RTX 3090).
    Build a static website in ./web (index.html, style.css, app.js; no CDNs) that presents the study. It must have at least
    five <section> elements: overview, hardware, timeline, results and quality. Use only facts from ./research, and
    include the key measured numbers: the start, exact and fast decode tok/s, the 27/15 layer split, GPU1's 6.4 GB/s link,
    the coding results (exact 54/64 vs fast 53/64) and the 128k context. Include an inline <svg> bar chart of the decode
    speeds with one <rect> per profile. Link style.css and app.js from index.html; app.js must add some interactivity.
    """, {"README.md": "# study site\n"}, """
    import re, sys, pathlib
    w = pathlib.Path("web"); h = (w / "index.html").read_text(); css = (w / "style.css").read_text(); js = (w / "app.js").read_text()
    facts = ["8.5", "14.1", "27/15", "6.4", "54/64", "53/64", "128k"]
    fast = any(x in h for x in ("53.8", "54.4", "55.5", "54"))
    ok = {"sections": len(re.findall(r"<section", h)) >= 5, "facts": all(f in h for f in facts) and fast,
          "svg": "<svg" in h and len(re.findall(r"<rect", h)) >= 3, "links": "style.css" in h and "app.js" in h,
          "css": len(css) > 200, "js": "addEventListener" in js or "onclick" in js, "size": len(h) > 4000}
    print(ok); sys.exit(0 if all(ok.values()) else 1)
    """)
print(sorted(p.name for p in T.iterdir()))
