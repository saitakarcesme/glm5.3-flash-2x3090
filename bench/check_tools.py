"""A local inventory fixture checks tool-call parsing and continuation."""
import json
import re
import pathlib
from benchmark import request

BASE = 'http://127.0.0.1:30270'
tool = {'type': 'function', 'function': {'name': 'lookup_inventory',
        'description': 'Return the available quantity for a SKU from inventory.',
        'parameters': {'type': 'object', 'properties': {'sku': {'type': 'string'}},
                       'required': ['sku'], 'additionalProperties': False}}}
messages = [{'role': 'user', 'content': 'Use lookup_inventory to find the available quantity for SKU RIG-3090. Do not invent the quantity.'}]
body = {'model': 'glm-5.3-flash', 'messages': messages, 'tools': [tool],
        'max_tokens': 128, 'temperature': 0,
        'chat_template_kwargs': {'enable_thinking': False}}
with request(BASE, '/v1/chat/completions', body) as response:
    first = json.load(response)
message = first['choices'][0]['message']
calls = message.get('tool_calls') or []
passed = (len(calls) == 1 and calls[0]['function']['name'] == 'lookup_inventory'
          and json.loads(calls[0]['function']['arguments']) == {'sku': 'RIG-3090'})
second = None
if passed:
    messages += [message, {'role': 'tool', 'tool_call_id': calls[0]['id'],
                 'content': json.dumps({'sku': 'RIG-3090', 'available_qty': 2})}]
    with request(BASE, '/v1/chat/completions', body) as response:
        second = json.load(response)
result = {'tool_call_schema_and_arguments_passed': passed, 'first': first,
          'continuation': second, 'note': 'Inventory is an isolated local fixture, not a live inventory service. Continuation text needs review.'}
result["continuation_quantity_passed"] = bool(second and re.search(r"\b(?:2|two)\b", second["choices"][0]["message"].get("content", ""), re.I))
pathlib.Path('receipts/tools.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'tool_call_schema_and_arguments_passed': passed}))
raise SystemExit(0 if passed and result["continuation_quantity_passed"] else 1)
