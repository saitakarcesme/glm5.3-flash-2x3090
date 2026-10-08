"""claude-opt: SSE keep-alive for chat streams. Tool-call content is held until it can be parsed, and guard restarts
re-prefill, so the client can see no bytes for minutes; HTTP clients (undici: 300 s body timeout) then drop the
connection ("terminated"). Emit an SSE comment every GLM53_SSE_KEEPALIVE_S seconds without a real event."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "def with_keepalive" not in s
helper = '''

KEEPALIVE_S = float(os.environ.get("GLM53_SSE_KEEPALIVE_S", "10"))


async def with_keepalive(agen, interval=KEEPALIVE_S):
    """Re-yield agen's items; yield None whenever nothing arrived for interval seconds."""
    it = agen.__aiter__()
    nxt = asyncio.ensure_future(it.__anext__())
    try:
        while True:
            done, _ = await asyncio.wait({nxt}, timeout=interval)
            if not done:
                yield None
                continue
            try:
                item = nxt.result()
            except StopAsyncIteration:
                return
            yield item
            nxt = asyncio.ensure_future(it.__anext__())
    finally:
        if not nxt.done():
            nxt.cancel()
'''
anchor = "\n\nasync def guarded_job("
assert anchor in s
s = s.replace(anchor, helper + anchor, 1)
# chat streaming loop: iterate through the keep-alive wrapper
head, sep, tail = s.partition("async def completions(")
old = "                async for text, n, fin in g:\n                    new = text[sent:]"
assert head.count(old) == 1, head.count(old)
head = head.replace(old, '''                async for item in with_keepalive(g):
                    if item is None:
                        yield ": keep-alive\\n\\n"
                        continue
                    text, n, fin = item
                    new = text[sent:]''')
s = head + sep + tail
ast.parse(s); p.write_text(s); print("ok")
