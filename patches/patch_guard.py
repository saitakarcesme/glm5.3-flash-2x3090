"""claude-opt reliability layer.
serve_claude.py: guarded_job() wraps run_job() for chat completions:
  * thinking budget (GLM53_THINK_BUDGET tokens, 0 = off): when the reasoning grows past it, close the think block with
    a short transition and continue generating the answer from there (budget forcing; the prefix cache makes it cheap).
  * loop guard (GLM53_LOOP_GUARD=1): if the generated text starts repeating (a unit repeated over >= 240 chars, or a
    very high 8-gram repeat rate over the last 3000 chars), cut back to where the loop began, close the thinking if
    it was inside it, and continue with cache-aware routing switched off (exact experts) for the rest of the request.
nv2_q.py: module-level CAR_OVERRIDE used by layer() when set."""
import pathlib, ast, re

# ---------------------------------------------------------------- nv2: per-request override
p = pathlib.Path("nv2_q.py"); s = p.read_text()
if "CAR_OVERRIDE" not in s:
    s = s.replace("_CAR = {}\n", "_CAR = {}\nCAR_OVERRIDE = None   # claude-opt: set by the server's loop guard (exact for the rest of a request)\n", 1)
    old = "        car = self.car\n        if car[0] and (n <= p.admit_max or car[4]):"
    assert old in s, "nv2 layer() CAR hook not found"
    s = s.replace(old, "        car = CAR_OVERRIDE if CAR_OVERRIDE is not None else self.car\n        if car[0] and (n <= p.admit_max or car[4]):")
    ast.parse(s); p.write_text(s)

# ---------------------------------------------------------------- serve: guarded_job
p = pathlib.Path("serve_claude.py"); s = p.read_text()
guard = r'''

# ---- claude-opt reliability layer ---------------------------------------------------------------------------------
THINK_BUDGET = int(os.environ.get("GLM53_THINK_BUDGET", "6144"))
LOOP_GUARD = os.environ.get("GLM53_LOOP_GUARD", "1") == "1"
THINK_CLOSE = "\n\nI have thought about this enough; now I will carry it out.\n</think>\n\n"
_WORD = re.compile(r"\w+")


def _loop_start(t):
    """Index where a degenerate loop begins in t, or None."""
    tail = t[-1500:]
    off = len(t) - len(tail)
    for unit in range(1, 201):
        if unit * 3 > len(tail):
            break
        u = tail[-unit:]
        if not u.strip():
            continue
        k, j = 1, len(tail) - unit
        while j - unit >= 0 and tail[j - unit:j] == u:
            k += 1; j -= unit
        if k * unit >= 240 and k >= 4:
            return off + j
    w = t[-3000:]
    words = _WORD.findall(w)
    if len(words) >= 300:
        g = [tuple(words[i:i + 8]) for i in range(len(words) - 7)]
        if 1 - len(set(g)) / len(g) > 0.85:
            return len(t) - len(w)
    return None


async def guarded_job(ids, sp, stops, thinking):
    """run_job with a thinking budget and a loop guard. Yields (text, completion tokens, finish) like run_job; the text
    is what the client sees (monotonic while thinking), the model context is kept consistent across restarts."""
    import nv2 as _nv2
    shown, ctx_extra, used, restarts = "", "", 0, 0
    budget = THINK_BUDGET if thinking else 0
    max_new = sp.get("max_new_tokens")
    in_think = thinking
    forced = False
    try:
        while True:
            cur_ids = ids if not ctx_extra else torch.cat([ids, tok.encode(ctx_extra, encode_special_tokens=True)], dim=-1)
            spk = dict(sp)
            if max_new is not None:
                spk["max_new_tokens"] = max(1, int(max_new) - used)
            restart = None
            g = run_job(cur_ids, spk, stops)
            last_check = 0
            async for text, n, fin in g:
                if in_think and "</think>" in text:
                    in_think = False
                if fin is None and len(text) - last_check >= 48:
                    last_check = len(text)
                    if in_think and budget and used + n >= budget:
                        restart = ("budget", ctx_extra + text, n)
                    elif LOOP_GUARD and restarts < 3:
                        full = ctx_extra + text
                        i = _loop_start(full)
                        if i is not None and i >= len(ctx_extra):
                            restart = ("loop", full[:i], n)
                if restart:
                    break
                yield shown + text, used + n, fin
                if fin is not None:
                    return
            await g.aclose()
            if not restart:
                return
            kind, cut, n = restart
            used += n; restarts += 1
            G["stats"]["guard_" + kind] = G["stats"].get("guard_" + kind, 0) + 1
            if kind == "loop" and not forced:
                _nv2.CAR_OVERRIDE = [0, 2, 0.0, 1, 1, 1]
                forced = True
            if in_think:   # end the thinking at the cut and move on to the answer
                shown = shown + (text if kind == "budget" else text[:max(0, len(cut) - len(ctx_extra))]) + THINK_CLOSE
                ctx_extra = cut + THINK_CLOSE
                in_think = False
            else:          # answer phase: drop the looping tail and continue from before it
                shown = shown + cut[len(ctx_extra):]
                ctx_extra = cut
            print(f" -- guard: {kind} restart #{restarts} after {used} tokens (exact={forced})", flush=True)
            if max_new is not None and used >= int(max_new):
                yield shown, used, {"type": "length", "reason": "guard"}
                return
    finally:
        if forced:
            _nv2.CAR_OVERRIDE = None
'''
if "def guarded_job" not in s:
    anchor = "\ndef teacher_forced("
    assert anchor in s
    s = s.replace(anchor, guard + "\n" + anchor, 1)
    # use it for chat completions (stream + non-stream)
    n1 = s.count("g = run_job(ids, sp, stops)")
    s = s.replace("            g = run_job(ids, sp, stops)\n", "            g = guarded_job(ids, sp, stops, thinking)\n")
    s = s.replace("    async for text, n, fin in run_job(ids, sp, stops):\n        pass\n    if thinking:",
                  "    async for text, n, fin in guarded_job(ids, sp, stops, thinking):\n        pass\n    if thinking:")
    assert "guarded_job(ids, sp, stops, thinking)" in s
    ast.parse(s); p.write_text(s)
print("patched; chat uses guarded_job:", s.count("guarded_job(ids, sp, stops, thinking)"))
