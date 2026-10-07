"""Author-written coding benchmark (32 problems). Each: prompt (signature + spec docstring), reference, tests.
Writes hard32.jsonl in HumanEval format after verifying every reference passes its tests."""
import json, textwrap
P = []
def add(name, sig, doc, ref, tests):
    prompt = f"{sig}\n    \"\"\"{textwrap.dedent(doc).strip()}\n    \"\"\"\n"
    test = "def check(candidate):\n" + "\n".join("    " + t for t in tests) + "\n"
    P.append({"task_id": f"Hard/{len(P)}", "prompt": prompt, "entry_point": name, "test": test, "ref": ref})

add("eval_expr", "def eval_expr(s: str) -> int:", """
    Evaluate an arithmetic expression with non-negative integer literals, + - * /, parentheses, spaces and unary minus.
    Usual precedence; * and / are left-associative; / is integer division truncating toward zero (like C).
    Example: eval_expr("2*(3+4) - -6/4") == 15""",
"""def eval_expr(s):
    s = s.replace(' ', ''); i = 0
    def num():
        nonlocal i
        if s[i] == '-':
            i += 1; return -num()
        if s[i] == '(':
            i += 1; v = expr(); i += 1; return v
        j = i
        while i < len(s) and s[i].isdigit(): i += 1
        return int(s[j:i])
    def term():
        nonlocal i
        v = num()
        while i < len(s) and s[i] in '*/':
            op = s[i]; i += 1; r = num()
            if op == '*': v = v * r
            else:
                q = abs(v) // abs(r); v = q if (v < 0) == (r < 0) else -q
        return v
    def expr():
        nonlocal i
        v = term()
        while i < len(s) and s[i] in '+-':
            op = s[i]; i += 1; r = term(); v = v + r if op == '+' else v - r
        return v
    return expr()""",
["assert candidate('2*(3+4) - -6/4') == 15", "assert candidate('1+2*3') == 7", "assert candidate('(1+2)*3') == 9",
 "assert candidate('7/-2') == -3", "assert candidate('-(2+3)*4') == -20", "assert candidate('100/7/2') == 7",
 "assert candidate('2-3-4') == -5", "assert candidate(' 42 ') == 42", "assert candidate('-7/2') == -3", "assert candidate('3*-(-2)') == 6"])

add("lru_simulate", "def lru_simulate(capacity: int, ops: list) -> list:", """
    Simulate an LRU cache. ops is a list of tuples: ("put", key, value) or ("get", key).
    Return the list of results of every "get" in order (-1 if missing). A get or put of an existing key makes it most
    recently used. When a put of a new key exceeds capacity, evict the least recently used key first.""",
"""def lru_simulate(capacity, ops):
    from collections import OrderedDict
    c = OrderedDict(); out = []
    for op in ops:
        if op[0] == 'get':
            if op[1] in c:
                c.move_to_end(op[1]); out.append(c[op[1]])
            else: out.append(-1)
        else:
            k, v = op[1], op[2]
            if k in c: c.move_to_end(k)
            c[k] = v
            if len(c) > capacity: c.popitem(last=False)
    return out""",
["assert candidate(2, [('put',1,1),('put',2,2),('get',1),('put',3,3),('get',2),('put',4,4),('get',1),('get',3),('get',4)]) == [1,-1,-1,3,4]",
 "assert candidate(1, [('put',1,1),('put',1,5),('get',1),('put',2,2),('get',1),('get',2)]) == [5,-1,2]",
 "assert candidate(2, [('get',9)]) == [-1]",
 "assert candidate(2, [('put',1,1),('put',2,2),('put',1,10),('put',3,3),('get',2),('get',1),('get',3)]) == [-1,10,3]"])

add("topo_order", "def topo_order(n: int, edges: list) -> list:", """
    Nodes are 0..n-1; edges is a list of (u, v) meaning u must come before v.
    Return the lexicographically smallest topological order as a list, or [] if the graph has a cycle.""",
"""def topo_order(n, edges):
    import heapq
    indeg = [0]*n; adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v); indeg[v] += 1
    h = [i for i in range(n) if indeg[i] == 0]; heapq.heapify(h); out = []
    while h:
        u = heapq.heappop(h); out.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0: heapq.heappush(h, v)
    return out if len(out) == n else []""",
["assert candidate(4, [(1,0),(2,0),(3,1),(3,2)]) == [3,1,2,0]", "assert candidate(3, [(0,1),(1,2),(2,0)]) == []",
 "assert candidate(3, []) == [0,1,2]", "assert candidate(5, [(4,0),(3,0),(0,1)]) == [2,3,4,0,1]"])

add("dijkstra", "def dijkstra(n: int, edges: list, src: int) -> list:", """
    Directed graph with nodes 0..n-1 and edges (u, v, w), w >= 0. Return a list of shortest distances from src;
    use -1 for unreachable nodes.""",
"""def dijkstra(n, edges, src):
    import heapq
    adj = [[] for _ in range(n)]
    for u, v, w in edges: adj[u].append((v, w))
    d = [None]*n; h = [(0, src)]
    while h:
        x, u = heapq.heappop(h)
        if d[u] is not None: continue
        d[u] = x
        for v, w in adj[u]:
            if d[v] is None: heapq.heappush(h, (x + w, v))
    return [-1 if x is None else x for x in d]""",
["assert candidate(4, [(0,1,4),(0,2,1),(2,1,2),(1,3,1)], 0) == [0,3,1,4]", "assert candidate(3, [(0,1,5)], 0) == [0,5,-1]",
 "assert candidate(3, [(1,0,1)], 0) == [0,-1,-1]", "assert candidate(2, [(0,1,0)], 1) == [-1,0]"])

add("edit_distance", "def edit_distance(a: str, b: str) -> int:", """
    Levenshtein distance (insert, delete, substitute each cost 1).""",
"""def edit_distance(a, b):
    p = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        c = [i]
        for j, cb in enumerate(b, 1):
            c.append(min(p[j]+1, c[j-1]+1, p[j-1]+(ca != cb)))
        p = c
    return p[-1]""",
["assert candidate('kitten','sitting') == 3", "assert candidate('','abc') == 3", "assert candidate('flaw','lawn') == 2", "assert candidate('same','same') == 0"])

add("lis_length", "def lis_length(nums: list) -> int:", """
    Length of the longest strictly increasing subsequence. Must run in O(n log n) for n up to 200000.""",
"""def lis_length(nums):
    import bisect
    t = []
    for x in nums:
        i = bisect.bisect_left(t, x)
        if i == len(t): t.append(x)
        else: t[i] = x
    return len(t)""",
["assert candidate([10,9,2,5,3,7,101,18]) == 4", "assert candidate([7,7,7]) == 1", "assert candidate([]) == 0",
 "assert candidate(list(range(200000))) == 200000", "assert candidate([3,1,2,1,8,5,6]) == 4"])

add("n_queens", "def n_queens(n: int) -> int:", """
    Number of ways to place n non-attacking queens on an n x n board.""",
"""def n_queens(n):
    def go(r, c, d1, d2):
        if r == n: return 1
        s = 0
        for x in range(n):
            if not (c >> x) & 1 and not (d1 >> (r + x)) & 1 and not (d2 >> (r - x + n)) & 1:
                s += go(r + 1, c | 1 << x, d1 | 1 << (r + x), d2 | 1 << (r - x + n))
        return s
    return go(0, 0, 0, 0)""",
["assert candidate(1) == 1", "assert candidate(4) == 2", "assert candidate(8) == 92", "assert candidate(3) == 0", "assert candidate(10) == 724"])

add("word_break_all", "def word_break_all(s: str, words: list) -> list:", """
    Return all ways to split s into a sequence of dictionary words (words may be reused), each as a space-joined
    string, sorted lexicographically.""",
"""def word_break_all(s, words):
    from functools import lru_cache
    W = set(words)
    @lru_cache(None)
    def go(i):
        if i == len(s): return [[]]
        out = []
        for j in range(i+1, len(s)+1):
            if s[i:j] in W:
                for rest in go(j): out.append([s[i:j]] + rest)
        return out
    return sorted(' '.join(x) for x in go(0))""",
["assert candidate('catsanddog', ['cat','cats','and','sand','dog']) == ['cat sand dog','cats and dog']",
 "assert candidate('aaa', ['a','aa']) == ['a a a','a aa','aa a']", "assert candidate('abc', ['ab']) == []"])

add("regex_match", "def regex_match(s: str, p: str) -> bool:", """
    Full-string match of s against pattern p supporting '.' (any single char) and '*' (zero or more of the preceding
    element).""",
"""def regex_match(s, p):
    from functools import lru_cache
    @lru_cache(None)
    def m(i, j):
        if j == len(p): return i == len(s)
        first = i < len(s) and p[j] in (s[i], '.')
        if j + 1 < len(p) and p[j+1] == '*':
            return m(i, j+2) or (first and m(i+1, j))
        return first and m(i+1, j+1)
    return m(0, 0)""",
["assert candidate('aa','a') is False", "assert candidate('aa','a*') is True", "assert candidate('ab','.*') is True",
 "assert candidate('aab','c*a*b') is True", "assert candidate('mississippi','mis*is*p*.') is False", "assert candidate('','a*b*') is True"])

add("min_window", "def min_window(s: str, t: str) -> str:", """
    Smallest substring of s containing every character of t with multiplicity. If several have the minimum length,
    return the leftmost. Return "" if none.""",
"""def min_window(s, t):
    from collections import Counter
    if not t: return ''
    need = Counter(t); miss = len(t); best = (float('inf'), 0, 0); l = 0
    for r, ch in enumerate(s):
        if need[ch] > 0: miss -= 1
        need[ch] -= 1
        while miss == 0:
            if r - l + 1 < best[0]: best = (r - l + 1, l, r + 1)
            need[s[l]] += 1
            if need[s[l]] > 0: miss += 1
            l += 1
    return s[best[1]:best[2]] if best[0] != float('inf') else ''""",
["assert candidate('ADOBECODEBANC','ABC') == 'BANC'", "assert candidate('a','aa') == ''", "assert candidate('aa','aa') == 'aa'",
 "assert candidate('abcabc','cb') == 'bc'"])

add("decode_string", "def decode_string(s: str) -> str:", """
    Decode strings like "3[a2[c]]" -> "accaccacc": k[x] repeats x k times (k >= 1, may be multi-digit, nesting allowed).""",
"""def decode_string(s):
    st = []; cur = ''; k = 0
    for ch in s:
        if ch.isdigit(): k = k*10 + int(ch)
        elif ch == '[':
            st.append((cur, k)); cur, k = '', 0
        elif ch == ']':
            prev, n = st.pop(); cur = prev + cur*n
        else: cur += ch
    return cur""",
["assert candidate('3[a2[c]]') == 'accaccacc'", "assert candidate('2[abc]3[cd]ef') == 'abcabccdcdcdef'", "assert candidate('10[a]') == 'a'*10", "assert candidate('xy') == 'xy'"])

add("max_rectangle", "def max_rectangle(heights: list) -> int:", """
    Largest rectangle area in a histogram with bar width 1. O(n) expected.""",
"""def max_rectangle(heights):
    st = []; best = 0; h = heights + [0]
    for i, x in enumerate(h):
        s = i
        while st and st[-1][1] >= x:
            s, y = st.pop(); best = max(best, y * (i - s))
        st.append((s, x))
    return best""",
["assert candidate([2,1,5,6,2,3]) == 10", "assert candidate([2,4]) == 4", "assert candidate([]) == 0", "assert candidate([3,3,3]) == 9", "assert candidate([1]*100000) == 100000"])

add("trap_rain", "def trap_rain(heights: list) -> int:", """
    Units of rain water trapped between bars of the given heights.""",
"""def trap_rain(h):
    l, r = 0, len(h) - 1; lm = rm = w = 0
    while l < r:
        if h[l] < h[r]:
            lm = max(lm, h[l]); w += lm - h[l]; l += 1
        else:
            rm = max(rm, h[r]); w += rm - h[r]; r -= 1
    return w""",
["assert candidate([0,1,0,2,1,0,1,3,2,1,2,1]) == 6", "assert candidate([4,2,0,3,2,5]) == 9", "assert candidate([]) == 0", "assert candidate([1,2,3]) == 0"])

add("flatten_dict", "def flatten_dict(d: dict, sep: str = '.') -> dict:", """
    Flatten nested dicts: {'a': {'b': 1, 'c': {'d': 2}}, 'e': 3} -> {'a.b': 1, 'a.c.d': 2, 'e': 3}.
    Empty nested dicts are dropped. Non-dict values (including lists) are kept as-is.""",
"""def flatten_dict(d, sep='.'):
    out = {}
    def go(x, pre):
        for k, v in x.items():
            key = f'{pre}{sep}{k}' if pre else str(k)
            if isinstance(v, dict): go(v, key)
            else: out[key] = v
    go(d, '')
    return out""",
["assert candidate({'a': {'b': 1, 'c': {'d': 2}}, 'e': 3}) == {'a.b': 1, 'a.c.d': 2, 'e': 3}", "assert candidate({'a': {}}) == {}",
 "assert candidate({'x': [1, {'y': 2}]}) == {'x': [1, {'y': 2}]}", "assert candidate({'a': {'b': 1}}, '/') == {'a/b': 1}"])

add("int_to_roman", "def int_to_roman(n: int) -> str:", """
    Convert 1 <= n <= 3999 to a standard Roman numeral (subtractive notation, e.g. 4 -> 'IV', 1994 -> 'MCMXCIV').""",
"""def int_to_roman(n):
    v = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
    out = ''
    for x, s in v:
        while n >= x:
            out += s; n -= x
    return out""",
["assert candidate(1994) == 'MCMXCIV'", "assert candidate(3999) == 'MMMCMXCIX'", "assert candidate(4) == 'IV'", "assert candidate(58) == 'LVIII'"])

add("count_islands", "def count_islands(grid: list) -> int:", """
    grid is a list of strings of '1' (land) and '0' (water). Count 4-directionally connected land components.
    Must handle grids up to 1000x1000 without recursion-depth errors.""",
"""def count_islands(grid):
    if not grid: return 0
    R, C = len(grid), len(grid[0]); seen = [[False]*C for _ in range(R)]; n = 0
    for i in range(R):
        for j in range(C):
            if grid[i][j] == '1' and not seen[i][j]:
                n += 1; st = [(i, j)]; seen[i][j] = True
                while st:
                    a, b = st.pop()
                    for x, y in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                        if 0 <= x < R and 0 <= y < C and grid[x][y] == '1' and not seen[x][y]:
                            seen[x][y] = True; st.append((x, y))
    return n""",
["assert candidate(['11000','11000','00100','00011']) == 3", "assert candidate([]) == 0", "assert candidate(['1'*1000]*1000) == 1",
 "assert candidate(['101','010','101']) == 5"])

add("coin_change", "def coin_change(coins: list, amount: int) -> int:", """
    Minimum number of coins (unlimited supply of each denomination) summing to amount, or -1 if impossible.""",
"""def coin_change(coins, amount):
    INF = float('inf'); d = [0] + [INF]*amount
    for a in range(1, amount+1):
        for c in coins:
            if c <= a and d[a-c] + 1 < d[a]: d[a] = d[a-c] + 1
    return -1 if d[amount] == INF else d[amount]""",
["assert candidate([1,2,5], 11) == 3", "assert candidate([2], 3) == -1", "assert candidate([1], 0) == 0", "assert candidate([186,419,83,408], 6249) == 20"])

add("knapsack", "def knapsack(weights: list, values: list, cap: int) -> int:", """
    0/1 knapsack: maximum total value with total weight <= cap.""",
"""def knapsack(weights, values, cap):
    d = [0]*(cap+1)
    for w, v in zip(weights, values):
        for c in range(cap, w-1, -1): d[c] = max(d[c], d[c-w] + v)
    return d[cap]""",
["assert candidate([1,3,4,5],[1,4,5,7],7) == 9", "assert candidate([], [], 10) == 0", "assert candidate([5],[10],4) == 0", "assert candidate([2,2,2],[3,3,3],4) == 6"])

add("sliding_median", "def sliding_median(nums: list, k: int) -> list:", """
    Medians of every window of size k (as floats; for even k the mean of the two middle values).
    Must handle len(nums) = 100000 with k = 1000 in well under 10 seconds.""",
"""def sliding_median(nums, k):
    import bisect
    w = sorted(nums[:k]); out = []
    for i in range(k, len(nums)+1):
        out.append(float(w[k//2]) if k % 2 else (w[k//2-1] + w[k//2]) / 2)
        if i == len(nums): break
        w.pop(bisect.bisect_left(w, nums[i-k])); bisect.insort(w, nums[i])
    return out""",
["assert candidate([1,3,-1,-3,5,3,6,7],3) == [1.0,-1.0,-1.0,3.0,5.0,6.0]", "assert candidate([1,2,3,4],2) == [1.5,2.5,3.5]",
 "import random; r=random.Random(1); a=[r.randint(-10**6,10**6) for _ in range(100000)]; out=candidate(a,1000); s=sorted(a[:1000]); assert len(out)==99001 and out[0]==(s[499]+s[500])/2"])

add("min_meeting_rooms", "def min_meeting_rooms(intervals: list) -> int:", """
    intervals are (start, end) half-open [start, end). Minimum number of rooms so no two overlapping meetings share one.""",
"""def min_meeting_rooms(intervals):
    ev = sorted([(s, 1) for s, e in intervals] + [(e, -1) for s, e in intervals], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d in ev:
        cur += d; best = max(best, cur)
    return best""",
["assert candidate([(0,30),(5,10),(15,20)]) == 2", "assert candidate([(7,10),(2,4)]) == 1", "assert candidate([(1,5),(5,10)]) == 1", "assert candidate([]) == 0", "assert candidate([(1,10),(2,9),(3,8)]) == 3"])

add("parse_csv_line", "def parse_csv_line(line: str) -> list:", """
    Parse one CSV line: fields separated by commas; a field may be wrapped in double quotes, in which case it may
    contain commas, and a doubled quote \"\" inside it means a literal quote. Unquoted fields are taken verbatim.
    Example: parse_csv_line('a,\"b,c\",\"say \"\"hi\"\"\",') == ['a', 'b,c', 'say \"hi\"', '']""",
"""def parse_csv_line(line):
    out = []; i = 0; n = len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1; f = ''
            while i < n:
                if line[i] == '"':
                    if i + 1 < n and line[i+1] == '"':
                        f += '"'; i += 2
                    else:
                        i += 1; break
                else:
                    f += line[i]; i += 1
            out.append(f)
        else:
            j = line.find(',', i)
            j = n if j < 0 else j
            out.append(line[i:j]); i = j
        if i < n and line[i] == ',': i += 1
        else: break
    return out""",
["assert candidate('a,\"b,c\",\"say \"\"hi\"\"\",') == ['a','b,c','say \"hi\"','']", "assert candidate('x') == ['x']",
 "assert candidate('') == ['']", "assert candidate('1,2,3') == ['1','2','3']", "assert candidate('\"\",b') == ['','b']"])

add("version_compare", "def version_compare(a: str, b: str) -> int:", """
    Compare dotted version strings numerically ("1.10" > "1.9"; missing parts count as 0, so "1.0" == "1").
    Return -1, 0 or 1.""",
"""def version_compare(a, b):
    x = [int(p) for p in a.split('.')]; y = [int(p) for p in b.split('.')]
    n = max(len(x), len(y)); x += [0]*(n-len(x)); y += [0]*(n-len(y))
    return (x > y) - (x < y)""",
["assert candidate('1.10','1.9') == 1", "assert candidate('1.0','1') == 0", "assert candidate('0.1','1.1') == -1", "assert candidate('1.0.1','1') == 1", "assert candidate('01.2','1.02') == 0"])

add("longest_palindrome", "def longest_palindrome(s: str) -> str:", """
    Longest palindromic substring; if several share the maximum length, return the leftmost one.""",
"""def longest_palindrome(s):
    best = ''
    for c in range(len(s)):
        for l, r in ((c, c), (c, c+1)):
            while l >= 0 and r < len(s) and s[l] == s[r]:
                l -= 1; r += 1
            if r - l - 1 > len(best): best = s[l+1:r]
    return best""",
["assert candidate('babad') == 'bab'", "assert candidate('cbbd') == 'bb'", "assert candidate('') == ''", "assert candidate('abacdfgdcaba') == 'aba'", "assert candidate('forgeeksskeegfor') == 'geeksskeeg'"])

add("sudoku_valid", "def sudoku_valid(board: list) -> bool:", """
    board is 9 strings of 9 chars, digits '1'-'9' or '.' for empty. Return True if no digit repeats in any row,
    column or 3x3 box (the board need not be solvable).""",
"""def sudoku_valid(board):
    seen = set()
    for i in range(9):
        for j in range(9):
            c = board[i][j]
            if c == '.': continue
            for k in (('r', i, c), ('c', j, c), ('b', i//3, j//3, c)):
                if k in seen: return False
                seen.add(k)
    return True""",
["assert candidate(['53..7....','6..195...','.98....6.','8...6...3','4..8.3..1','7...2...6','.6....28.','...419..5','....8..79']) is True",
 "assert candidate(['83..7....','6..195...','.98....6.','8...6...3','4..8.3..1','7...2...6','.6....28.','...419..5','....8..79']) is False",
 "assert candidate(['.........']*9) is True", "assert candidate(['1........','.1.......']+['.........']*7) is False"])

add("num_distinct", "def num_distinct(s: str, t: str) -> int:", """
    Number of distinct subsequences of s that equal t.""",
"""def num_distinct(s, t):
    d = [1] + [0]*len(t)
    for ch in s:
        for j in range(len(t), 0, -1):
            if t[j-1] == ch: d[j] += d[j-1]
    return d[-1]""",
["assert candidate('rabbbit','rabbit') == 3", "assert candidate('babgbag','bag') == 5", "assert candidate('abc','') == 1", "assert candidate('','a') == 0"])

add("multiply_strings", "def multiply_strings(a: str, b: str) -> str:", """
    Multiply two non-negative integers given as decimal strings without converting the whole strings to int
    (digit-by-digit). Return the product as a string without leading zeros ("0" for zero).""",
"""def multiply_strings(a, b):
    r = [0]*(len(a)+len(b))
    for i in range(len(a)-1, -1, -1):
        for j in range(len(b)-1, -1, -1):
            p = (ord(a[i])-48)*(ord(b[j])-48) + r[i+j+1]
            r[i+j+1] = p % 10; r[i+j] += p // 10
    s = ''.join(map(str, r)).lstrip('0')
    return s or '0'""",
["assert candidate('123','456') == '56088'", "assert candidate('0','999') == '0'", "assert candidate('99','99') == '9801'",
 "assert candidate('123456789123456789','987654321987654321') == str(123456789123456789*987654321987654321)"])

add("fib_mod", "def fib_mod(n: int, m: int) -> int:", """
    F(n) mod m where F(0)=0, F(1)=1, for n up to 10**18 (must be O(log n)).""",
"""def fib_mod(n, m):
    def go(k):
        if k == 0: return (0, 1)
        a, b = go(k >> 1)
        c = a * ((2*b - a) % m) % m; d = (a*a + b*b) % m
        return (d, (c + d) % m) if k & 1 else (c, d)
    return go(n)[0] % m""",
["assert candidate(10, 1000) == 55", "assert candidate(0, 7) == 0", "assert candidate(1, 1) == 0", "assert candidate(90, 10**18) == 2880067194370816120 % 10**18", "assert candidate(100, 10**18) == 354224848179261915075 % 10**18"])

add("next_permutation", "def next_permutation(nums: list) -> list:", """
    Return the next lexicographic permutation of nums as a new list; if nums is the last permutation, return the
    first (sorted ascending). Duplicates are allowed.""",
"""def next_permutation(nums):
    a = list(nums); i = len(a) - 2
    while i >= 0 and a[i] >= a[i+1]: i -= 1
    if i >= 0:
        j = len(a) - 1
        while a[j] <= a[i]: j -= 1
        a[i], a[j] = a[j], a[i]
    a[i+1:] = reversed(a[i+1:])
    return a""",
["assert candidate([1,2,3]) == [1,3,2]", "assert candidate([3,2,1]) == [1,2,3]", "assert candidate([1,1,5]) == [1,5,1]", "assert candidate([1,5,1]) == [5,1,1]", "assert candidate([]) == []"])

add("shortest_path_k", "def shortest_path_k(grid: list, k: int) -> int:", """
    grid is a list of lists of 0 (free) / 1 (obstacle). Move up/down/left/right from the top-left to the
    bottom-right cell; you may pass through at most k obstacles. Return the minimum number of steps, or -1.""",
"""def shortest_path_k(grid, k):
    from collections import deque
    R, C = len(grid), len(grid[0])
    if R == 1 and C == 1: return 0
    best = {(0, 0): k}; q = deque([(0, 0, k, 0)])
    while q:
        i, j, r, d = q.popleft()
        for x, y in ((i+1,j),(i-1,j),(i,j+1),(i,j-1)):
            if 0 <= x < R and 0 <= y < C:
                nr = r - grid[x][y]
                if nr < 0: continue
                if (x, y) == (R-1, C-1): return d + 1
                if best.get((x, y), -1) < nr:
                    best[(x, y)] = nr; q.append((x, y, nr, d + 1))
    return -1""",
["assert candidate([[0,0,0],[1,1,0],[0,0,0],[0,1,1],[0,0,0]], 1) == 6", "assert candidate([[0,1,1],[1,1,1],[1,0,0]], 1) == -1",
 "assert candidate([[0]], 0) == 0", "assert candidate([[0,1],[1,0]], 1) == 2"])

add("text_justify", "def text_justify(words: list, width: int) -> list:", """
    Full text justification: greedily pack as many words per line as fit (single spaces minimum). Every line except
    the last is padded to exactly width by distributing extra spaces between words as evenly as possible, with
    left gaps getting more; a line with one word is left-justified and padded on the right. The last line is
    left-justified (single spaces) and padded on the right to width.""",
"""def text_justify(words, width):
    out = []; i = 0
    while i < len(words):
        j = i; ln = 0
        while j < len(words) and ln + len(words[j]) + (j - i) <= width:
            ln += len(words[j]); j += 1
        gaps = j - i - 1
        if j == len(words) or gaps == 0:
            s = ' '.join(words[i:j]); out.append(s + ' '*(width - len(s)))
        else:
            sp, ex = divmod(width - ln, gaps); s = ''
            for g in range(gaps): s += words[i+g] + ' '*(sp + (g < ex))
            out.append(s + words[j-1])
        i = j
    return out""",
["assert candidate(['This','is','an','example','of','text','justification.'],16) == ['This    is    an','example  of text','justification.  ']",
 "assert candidate(['What','must','be','acknowledgment','shall','be'],16) == ['What   must   be','acknowledgment  ','shall be        ']",
 "assert candidate(['a'],3) == ['a  ']"])

add("merge_k_sorted", "def merge_k_sorted(lists: list) -> list:", """
    Merge k ascending lists into one ascending list in O(N log k).""",
"""def merge_k_sorted(lists):
    import heapq
    return list(heapq.merge(*lists))""",
["assert candidate([[1,4,5],[1,3,4],[2,6]]) == [1,1,2,3,4,4,5,6]", "assert candidate([]) == []", "assert candidate([[],[1]]) == [1]",
 "assert candidate([list(range(i, 100000, 50)) for i in range(50)]) == list(range(100000))"])

add("spiral_order", "def spiral_order(matrix: list) -> list:", """
    Elements of an m x n matrix in clockwise spiral order starting at the top-left.""",
"""def spiral_order(m):
    out = []
    while m:
        out += m[0]; m = [list(r) for r in zip(*m[1:])][::-1]
    return out""",
["assert candidate([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]", "assert candidate([[1,2,3,4],[5,6,7,8],[9,10,11,12]]) == [1,2,3,4,8,12,11,10,9,5,6,7]",
 "assert candidate([]) == []", "assert candidate([[1],[2],[3]]) == [1,2,3]"])

bad = 0
for p in P:
    g = {}
    try:
        exec(p["ref"], g); exec(p["test"], g); g["check"](g[p["entry_point"]])
    except Exception as e:
        bad += 1; print("REF FAIL", p["task_id"], p["entry_point"], repr(e))
print(len(P), "problems,", bad, "reference failures")
with open("hard32.jsonl", "w") as f:
    for p in P:
        f.write(json.dumps({k: v for k, v in p.items() if k != "ref"}) + "\n")
