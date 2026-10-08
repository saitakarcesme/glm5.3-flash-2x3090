"""claude-opt: chat/completions sampling defaults from the model's generation_config.json (temperature 1.0, top_p 0.95
for GLM-5.3-Flash) when the client sends none. The stock default top_p 1.0 samples the full tail of a 2-bit model."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
old = '''def openai_sp(body):
    return {"temperature": body.get("temperature", 1.0), "top_p": body.get("top_p", 1.0), "top_k": body.get("top_k"),'''
assert old in s, "openai_sp signature changed"
new = '''_GEN = {}


def _gen_defaults():
    if not _GEN:
        try:
            g = json.load(open(os.path.join(args.model_dir, "generation_config.json")))
        except Exception:
            g = {}
        _GEN["t"] = float(os.environ.get("GLM53_DEFAULT_TEMPERATURE", g.get("temperature", 1.0)))
        _GEN["p"] = float(os.environ.get("GLM53_DEFAULT_TOP_P", g.get("top_p", 0.95)))
        print(f" -- sampling defaults (no client value): temperature {_GEN['t']}, top_p {_GEN['p']}", flush=True)
    return _GEN["t"], _GEN["p"]


def openai_sp(body):
    dt, dp = _gen_defaults()
    return {"temperature": body.get("temperature", dt), "top_p": body.get("top_p", dp), "top_k": body.get("top_k"),'''
s = s.replace(old, new)
ast.parse(s)
p.write_text(s)
print("ok")
