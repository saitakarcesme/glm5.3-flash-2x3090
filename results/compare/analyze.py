"""Compare recorded pi sessions from the proxy request logs + the produced ./site directories.
usage: analyze.py BASE LABEL [LABEL...]   (BASE = ~/pi-compare)"""
import json, sys, os, re, statistics, pathlib

base = pathlib.Path(sys.argv[1]); out = {}
for label in sys.argv[2:]:
    rows = [json.loads(l) for l in open(base / f"{label}-requests.jsonl") if l.strip()]
    comp = sum(r["completion_tokens"] or 0 for r in rows)
    total = sum(r["total_s"] for r in rows)
    streamed = [r for r in rows if r["decode_s"] >= 2.0]          # turns whose tokens actually streamed over >= 2 s
    span = (rows[-1]["t_start"] + rows[-1]["total_s"] - rows[0]["t_start"]) if rows else 0
    site = pathlib.Path.home() / "pi-ws" / label / "site"
    files = sorted(p for p in site.rglob("*") if p.is_file()) if site.exists() else []
    idx = site / "index.html"
    missing, svg, canvas = [], 0, 0
    if idx.exists():
        h = idx.read_text(errors="replace")
        svg, canvas = h.count("<svg"), h.count("<canvas")
        for ref in re.findall(r'(?:src|href)="([^"#:?]+)"', h):
            if not ref.startswith(("http", "mailto", "data", "//")) and not (site / ref).exists():
                missing.append(ref)
    out[label] = {
        "requests": len(rows), "agent_wall_s": round(span, 1), "output_tokens": comp,
        "e2e_output_tok_s": round(comp / total, 2) if total else 0,
        "streamed_decode_tok_s": round(sum(r["completion_tokens"] for r in streamed) / sum(r["decode_s"] for r in streamed), 2) if streamed else None,
        "streamed_turns": len(streamed),
        "median_ttft_s": round(statistics.median(r["ttft_s"] for r in rows), 2) if rows else None,
        "max_prompt_tokens": max((r["prompt_tokens"] or 0) for r in rows) if rows else 0,
        "final_finish": rows[-1]["finish"] if rows else None,
        "site_files": [str(p.relative_to(site)) for p in files], "site_bytes": sum(p.stat().st_size for p in files),
        "index_html": idx.exists(), "inline_svg": svg, "canvas": canvas, "broken_local_refs": missing,
    }
print(json.dumps(out, indent=1))
