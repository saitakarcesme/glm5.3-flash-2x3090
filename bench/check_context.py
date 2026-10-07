import json,pathlib,time
from benchmark import request
base="http://127.0.0.1:30270"
def tokenize(s):
 with request(base,"/tokenize",{"prompt":s}) as r:return json.load(r)["tokens"]
prefix=tokenize("[gMASK]<sop><|user|>Background records follow. ")
fill=tokenize(" This is a synthetic background record about a local inference experiment."*800)
suffix=tokenize("\nFinal instruction: output exactly RIGOK and nothing else.<|assistant|><think></think>")
ids=prefix+fill[:6800-len(prefix)-len(suffix)]+suffix
start=time.perf_counter()
with request(base,"/generate",{"input_ids":ids,"sampling_params":{"temperature":0,"max_new_tokens":16}}) as r:out=json.load(r)
result={"input_tokens":len(ids),"elapsed_s":time.perf_counter()-start,"response":out,"sentinel_passed":out.get("text","").strip()=="RIGOK"}
pathlib.Path("receipts/context-6800.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
raise SystemExit(0 if result["sentinel_passed"] else 1)
