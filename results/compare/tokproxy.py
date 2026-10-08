"""OpenAI-compatible logging proxy: forwards /v1/* to an upstream server, measures every chat completion.
Per request it logs prompt/completion tokens, TTFT and decode tok/s (first to last streamed token), appends a JSON line
to --log, and prints a running summary line (for a live on-screen tok/s panel).
usage: tokproxy.py --listen 18100 --upstream http://127.0.0.1:30270 --log run.jsonl --label GLM"""
import argparse, json, time, threading, http.server, socketserver, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--listen", type=int, required=True); ap.add_argument("--upstream", required=True)
ap.add_argument("--log", required=True); ap.add_argument("--label", default="model")
a = ap.parse_args()
lock = threading.Lock()
INFL = [0]
tot = {"req": 0, "comp": 0, "prompt": 0, "decode_s": 0.0, "wall_s": 0.0, "t0": None}


def record(row):
    with lock:
        tot["req"] += 1; tot["comp"] += row["completion_tokens"] or 0; tot["prompt"] += row["prompt_tokens"] or 0
        tot["decode_s"] += row["decode_s"]; tot["wall_s"] += row["total_s"]
        if tot["t0"] is None: tot["t0"] = row["t_start"]
        with open(a.log, "a") as f: f.write(json.dumps(row) + "\n")
        avg = tot["comp"] / tot["decode_s"] if tot["decode_s"] > 0 else 0
        print(f"[{a.label}] req {tot['req']:3d} | this: {row['completion_tokens'] or 0:5d} tok, TTFT {row['ttft_s']:6.2f}s, "
              f"decode {row['decode_tok_s']:6.1f} tok/s | session: {tot['comp']:6d} out tok, avg decode {avg:5.1f} tok/s, "
              f"prompt tok {tot['prompt']:7d} | {row.get('finish')}", flush=True)


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *x): pass

    def _fwd(self, body=None):
        req = urllib.request.Request(a.upstream + self.path, data=body, method=self.command,
                                     headers={k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length", "accept-encoding")})
        return urllib.request.urlopen(req, timeout=7200)

    def do_GET(self):
        with self._fwd() as r:
            data = r.read(); self.send_response(r.status)
            self.send_header("Content-Type", r.headers.get("Content-Type", "application/json")); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

    def _infl(self, d):
        with lock:
            INFL[0] += d
            open(a.log + ".inflight", "w").write(str(INFL[0]))

    def do_POST(self):
        self._infl(1)
        try:
            self._post()
        finally:
            self._infl(-1)

    def _post(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        chat = self.path.endswith("/chat/completions")
        stream = False
        if chat:
            try:
                j = json.loads(body); stream = bool(j.get("stream"))
                if stream:
                    j.setdefault("stream_options", {})["include_usage"] = True
                body = json.dumps(j).encode()
            except Exception:
                chat = False
        t0 = time.time(); first = last = None; usage = None; finish = None
        r = self._fwd(body)
        self.send_response(r.status)
        for k, v in r.headers.items():
            if k.lower() not in ("content-length", "transfer-encoding", "connection"): self.send_header(k, v)
        if stream:
            self.send_header("Transfer-Encoding", "chunked"); self.end_headers()
            for line in r:
                if chat and line.startswith(b"data: ") and line.strip() != b"data: [DONE]":
                    try:
                        e = json.loads(line[6:])
                        usage = e.get("usage") or usage
                        for c in e.get("choices", []):
                            finish = c.get("finish_reason") or finish
                            d = c.get("delta", {})
                            if d.get("content") or d.get("reasoning_content") or d.get("tool_calls"):
                                now = time.time(); first = first or now; last = now
                    except Exception:
                        pass
                self.wfile.write(b"%x\r\n%s\r\n" % (len(line), line)); self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
        else:
            data = r.read(); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            if chat:
                try:
                    jj = json.loads(data); usage = jj.get("usage"); finish = (jj.get("choices") or [{}])[0].get("finish_reason")
                except Exception: pass
                first = last = time.time()
        r.close()
        if chat:
            ct = (usage or {}).get("completion_tokens") or 0
            dec = (last - first) if (first and last and last > first) else 0.0
            record({"t_start": t0, "prompt_tokens": (usage or {}).get("prompt_tokens"), "completion_tokens": ct,
                    "ttft_s": round((first or time.time()) - t0, 3), "decode_s": round(dec, 3),
                    "decode_tok_s": round(ct / dec, 2) if dec > 0 else 0.0, "total_s": round(time.time() - t0, 3), "finish": finish})


class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    def handle_error(self, request, client_address):
        pass   # client closed a keep-alive connection


print(f"[{a.label}] proxy 127.0.0.1:{a.listen} -> {a.upstream}, log {a.log}", flush=True)
S(("127.0.0.1", a.listen), H).serve_forever()
