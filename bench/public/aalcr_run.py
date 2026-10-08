"""AA-LCR v1.1 runner: official prompt template (documents in data_source_filenames order), official sampling for GLM
(thinking on, temperature 1.0, top_p 0.95, no client thinking budget), then grading with the official v1.1 judge system
+ user prompts. The official judge model (GPT-5.6 Luna) is not available locally: the judge here is the same local
GLM with thinking off and temperature 0. Random seeded subset, resumable.
usage: aalcr_run.py --n 20 --out aalcr-fast.jsonl"""
import csv, json, os, random, re, time, argparse, urllib.request, math
ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=20); ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", required=True); ap.add_argument("--root", default="data/aalcr_text/lcr")
a = ap.parse_args()
U = "http://127.0.0.1:30270/v1/chat/completions"
JUDGE_SYS = """Decide whether the CANDIDATE ANSWER is correct or incorrect against the OFFICIAL ANSWER.
Note the following points when assessing correctness:

- Numbers should still match when they are the same value written differently, e.g., a
  percentage, a count of percentage points, and the equivalent decimal fraction are the same
  value: 0.675, "67.5%" and "67.5 percentage points" all match. So do different scales
  (thousand, million, bn) and different notations (thousands separators, currency symbols,
  LaTeX markup, and numbers written as words).
- Where the question asks for a particular format (e.g., a percentage, a number of decimal
  places, a unit, a rounding, or an ordering) the CANDIDATE ANSWER must meet it. If the
  question asks for no particular format, accept any equivalent form.
- In cases where the question asks for an ordered list, a title, honorific or article added
  to an entry in the CANDIDATE ANSWER can change where that entry sorts. Accept the ordering
  if it is correct either with those additions or without them.
- Grade the value the CANDIDATE ANSWER finally commits to, and it must commit to one. Values
  reached while working, and alternatives it considers and sets aside, do not count. If it
  offers several values without selecting one, it is incorrect even if one of them is right.
  Hedging is fine as long as one clearly definitive answer is given."""
JUDGE_USER = """Assess whether the following CANDIDATE ANSWER is CORRECT or INCORRECT.
For the CANDIDATE ANSWER to be correct, it must be consistent with the OFFICIAL ANSWER.

The question, for reference only: START QUESTION {question}

END QUESTION

The OFFICIAL ANSWER: {official_answer}

END OFFICIAL ANSWER

BEGIN CANDIDATE ANSWER TO ASSESS

{candidate_answer}

END CANDIDATE ANSWER TO ASSESS

Reply as JSON, with a verdict of CORRECT or INCORRECT."""


def chat(messages, **kw):
    body = {"model": "glm-5.3-flash", "messages": messages, **kw}
    r = urllib.request.Request(U, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=7200))


qs = list(csv.DictReader(open("data/aalcr.csv", encoding="utf-8")))
qs = [q for q in qs if all(os.path.exists(os.path.join(a.root, q["document_category"], q["document_set_id"], fn)) for fn in q["data_source_filenames"].split(";"))]   # 3 questions have unmatched document filenames
sel = random.Random(a.seed).sample(qs, a.n)
try:
    done = {json.loads(l)["question_id"]: json.loads(l) for l in open(a.out)}
except FileNotFoundError:
    done = {}
f = open(a.out, "a")
for q in sel:
    if q["question_id"] in done: continue
    docs = [open(os.path.join(a.root, q["document_category"], q["document_set_id"], fn), encoding="utf-8").read()
            for fn in q["data_source_filenames"].split(";")]
    documents_text = "\n\n".join(f"BEGIN DOCUMENT {i + 1}:\n{d}\nEND DOCUMENT {i + 1}" for i, d in enumerate(docs))
    prompt = f"""BEGIN INPUT DOCUMENTS

{documents_text}

END INPUT DOCUMENTS

Answer the following question using the input documents provided above.

START QUESTION

{q['question']}

END QUESTION
"""
    t = time.time()
    try:
        o = chat([{"role": "user", "content": prompt}], max_tokens=32768, temperature=1.0, top_p=0.95, thinking_budget=0,
                 chat_template_kwargs={"enable_thinking": True})
        ans = o["choices"][0]["message"].get("content") or ""; fin = o["choices"][0].get("finish_reason")
        usage = o.get("usage", {})
    except Exception as ex:
        ans, fin, usage = "", f"error: {ex}", {}
    dt = time.time() - t
    j = chat([{"role": "system", "content": JUDGE_SYS}, {"role": "user", "content": JUDGE_USER.format(
        question=q["question"], official_answer=q["answer"], candidate_answer=ans or "(no answer)")}],
        max_tokens=200, temperature=0, thinking_budget=0, chat_template_kwargs={"enable_thinking": False})
    jt = j["choices"][0]["message"].get("content") or ""
    correct = bool(re.search(r"\bCORRECT\b", jt)) and not re.search(r"INCORRECT", jt)
    row = {"question_id": q["question_id"], "category": q["document_category"], "input_tokens_cl100k": int(q["input_tokens"]),
           "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"), "finish": fin,
           "s": round(dt, 1), "official": q["answer"], "answer": ans[-600:], "judge": jt[-200:], "correct": correct}
    f.write(json.dumps(row) + "\n"); f.flush(); done[q["question_id"]] = row
    rows = [done[x["question_id"]] for x in sel if x["question_id"] in done]
    k = sum(r["correct"] for r in rows); n = len(rows); p = k / n
    print(f"[{n}/{len(sel)}] q{q['question_id']} {row['prompt_tokens']} prompt tok, {row['completion_tokens']} out, {dt:.0f}s, "
          f"{'CORRECT' if correct else 'wrong'} | running {k}/{n} = {100 * p:.1f}% ±{196 * math.sqrt(p * (1 - p) / n):.1f}", flush=True)
rows = [done[x["question_id"]] for x in sel if x["question_id"] in done]
print("FINAL", json.dumps({"n": len(rows), "correct": sum(r["correct"] for r in rows), "accuracy": round(100 * sum(r["correct"] for r in rows) / max(1, len(rows)), 1)}))
