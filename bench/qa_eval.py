"""Practical quality check: 16 short factual/arithmetic/code questions (exact-match substring) + repetition score of
3 long generations (fraction of repeated 4-grams over words; >0.25 = looping) + 3-prompt decode speed."""
import json, urllib.request, sys, collections, re
U = "http://127.0.0.1:30270"
Q = [("What is 17 times 23? Reply with only the number.", "391"), ("What is 48 + 76? Only the number.", "124"),
     ("What is 144 divided by 12? Only the number.", "12"), ("What is 2 to the power of 10? Only the number.", "1024"),
     ("What is 15% of 200? Only the number.", "30"), ("What is 9 times 8? Only the number.", "72"),
     ("What is the capital of Australia? One word.", "Canberra"), ("Who wrote Romeo and Juliet? Name only.", "Shakespeare"),
     ("What is the chemical symbol for gold? Symbol only.", "Au"), ("Türkiye'nin başkenti neresidir? Tek kelime.", "Ankara"),
     ("How many planets are in the solar system? Only the number.", "8"), ("What is the largest planet in the solar system? One word.", "Jupiter"),
     ("Reverse the string \"abcdef\". Output only the result.", "fedcba"), ("In Python, what does len([1, 2, 3, 4]) return? Only the number.", "4"),
     ("In Python, what is 7 // 2? Only the number.", "3"), ("What is the boiling point of water at sea level in Celsius? Only the number.", "100")]
def chat(q, n=32):
    body = {"model": "glm-5.3-flash", "messages": [{"role": "user", "content": q}], "max_tokens": n, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False}}
    r = urllib.request.Request(U + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=600))["choices"][0]["message"]["content"] or ""
ok = sum(a.lower() in chat(q).lower() for q, a in Q)
def rep(t):
    w = re.findall(r"\w+", t.lower()); g = [tuple(w[i:i + 4]) for i in range(len(w) - 3)]
    return 0 if not g else 1 - len(set(g)) / len(g)
bench = json.load(open(sys.argv[1]))
reps = [round(rep(r["text"]), 3) for r in bench["rows"][:3]]
think = sum("<think>" in r["text"] for r in bench["rows"][:3])
print(json.dumps({"factual": f"{ok}/{len(Q)}", "repetition_4gram": reps, "spurious_think": think, "agg_tok_s": round(bench["agg_tok_s"], 2)}))
