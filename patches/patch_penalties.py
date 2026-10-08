"""claude-opt: anti-repetition sampling. OpenAI presence_penalty / frequency_penalty / repetition_penalty and DRY
(dry_multiplier, dry_base, dry_allowed_length, dry_range) are passed to ExLlamaV3's ComboSampler; server-side defaults
via GLM53_DEFAULT_PRES_P / GLM53_DEFAULT_DRY (multiplier) / GLM53_DEFAULT_DRY_RANGE apply when the client sends none."""
import pathlib, ast
p = pathlib.Path("serve_claude.py"); s = p.read_text()
assert "pres_p" not in s
old = '''def make_sampler(sp):
    t = float(sp.get("temperature", 1.0) if sp.get("temperature") is not None else 1.0)
    if t <= 0:
        return ArgmaxSampler()
    return ComboSampler(temperature=t, top_p=float(sp.get("top_p") or 1.0), top_k=int(sp.get("top_k") or 0),
                        min_p=float(sp.get("min_p") or 0.0))'''
assert old in s
new = '''def make_sampler(sp):
    t = float(sp.get("temperature", 1.0) if sp.get("temperature") is not None else 1.0)
    if t <= 0:
        return ArgmaxSampler()
    f = lambda k, env, d: float(sp[k]) if sp.get(k) is not None else float(os.environ.get(env, d))
    dry = f("dry_multiplier", "GLM53_DEFAULT_DRY", "0")
    return ComboSampler(temperature=t, top_p=float(sp.get("top_p") or 1.0), top_k=int(sp.get("top_k") or 0),
                        min_p=float(sp.get("min_p") or 0.0),
                        pres_p=f("presence_penalty", "GLM53_DEFAULT_PRES_P", "0"), freq_p=f("frequency_penalty", "GLM53_DEFAULT_FREQ_P", "0"),
                        rep_p=f("repetition_penalty", "GLM53_DEFAULT_REP_P", "1.0"),
                        dry_multiplier=dry, dry_base=f("dry_base", "GLM53_DEFAULT_DRY_BASE", "1.75"),
                        dry_allowed_length=int(f("dry_allowed_length", "GLM53_DEFAULT_DRY_ALLOWED", "4")),
                        dry_range=int(f("dry_range", "GLM53_DEFAULT_DRY_RANGE", "4096")) if dry > 0 else 0)'''
s = s.replace(old, new)
old2 = '''    return {"temperature": body.get("temperature", dt), "top_p": body.get("top_p", dp), "top_k": body.get("top_k"),'''
assert old2 in s
s = s.replace(old2, '''    return {"presence_penalty": body.get("presence_penalty"), "frequency_penalty": body.get("frequency_penalty"),
            "repetition_penalty": body.get("repetition_penalty"), "dry_multiplier": body.get("dry_multiplier"),
            "dry_base": body.get("dry_base"), "dry_allowed_length": body.get("dry_allowed_length"), "dry_range": body.get("dry_range"),
            "temperature": body.get("temperature", dt), "top_p": body.get("top_p", dp), "top_k": body.get("top_k"),''')
ast.parse(s); p.write_text(s); print("ok")
