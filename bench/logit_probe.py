import argparse,json,pathlib
from benchmark import request
ap=argparse.ArgumentParser();ap.add_argument("--output",required=True);a=ap.parse_args()
prompts=[
 "[gMASK]<sop><|user|>What is 17 times 23? Answer with the integer only.<|assistant|><think></think>",
 "[gMASK]<sop><|user|>Explain how database indexes work, including B-trees and query planning.<|assistant|><think></think>",
 "[gMASK]<sop><|user|>Sort 3, 1, 2 and return only a JSON array.<|assistant|><think></think>",
]
rows=[]
for prompt in prompts:
 with request("http://127.0.0.1:30270","/tokenize",{"prompt":prompt}) as response:ids=json.load(response)["tokens"]
 with request("http://127.0.0.1:30270","/generate",{"input_ids":ids,"return_logprob":True,"logprob_start_len":max(1,len(ids)-6),"top_logprobs_num":30}) as response:out=json.load(response)
 rows.append({"prompt":prompt,"input_ids":ids,"response":out})
pathlib.Path(a.output).write_text(json.dumps(rows,indent=2)+"\n")
print("Saved",len(rows),"fixed-input teacher-forced distributions",flush=True)
