"""Measure actual API usage, end-to-end rate, TTFT and server token throughput.

Streaming chunk counts are intentionally never treated as token counts.
"""
import argparse
import json
import pathlib
import statistics
import time
import urllib.request
from datetime import datetime, timezone


def request(base, path, body=None):
    req = urllib.request.Request(base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=900)


def measure(base, prompt, limit):
    body = {'model': 'glm-5.3-flash', 'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': limit, 'temperature': 0, 'stream': True,
            'stream_options': {'include_usage': True},
            'chat_template_kwargs': {'enable_thinking': False}}
    start = time.perf_counter()
    first = last = None
    usage = None
    chunks = []
    finish = None
    with request(base, '/v1/chat/completions', body) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            data = line[6:].strip()
            if data == b'[DONE]':
                break
            event = json.loads(data)
            if event.get('usage'):
                usage = event['usage']
            for choice in event.get('choices', []):
                delta = choice.get('delta', {})
                piece = delta.get('content', '') or delta.get('reasoning_content', '')
                if piece:
                    now = time.perf_counter()
                    first = first if first is not None else now
                    last = now
                    chunks.append(piece)
                if choice.get('finish_reason'):
                    finish = choice['finish_reason']
    elapsed = time.perf_counter() - start
    count = (usage or {}).get('completion_tokens')
    return {'prompt': prompt, 'text': ''.join(chunks), 'usage': usage,
            'finish_reason': finish, 'elapsed_s': elapsed,
            'ttft_s': None if first is None else first-start,
            'end_to_end_tok_s': count/elapsed if count else None,
            'delivery_duration_s': None if first is None else last-first,
            'stream_chunks': len(chunks),
            'note': 'SSE chunks are not tokens; no decode rate inferred from chunk counts.'}


def measure_decode(base, limit):
    prompt = ('[gMASK]<sop><|user|>Write a detailed explanation of how database indexes work, '
              'including B-trees, query planning and practical examples.<|assistant|><think></think>')
    with request(base, '/tokenize', {'prompt': prompt}) as response:
        ids = json.load(response)['tokens']
    body = {'input_ids': ids, 'stream': True,
            'sampling_params': {'temperature': 0, 'max_new_tokens': limit}}
    points = []
    start = time.perf_counter()
    text = ''
    with request(base, '/generate', body) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            data = line[6:].strip()
            if data == b'[DONE]':
                break
            event = json.loads(data)
            n = event.get('meta_info', {}).get('completion_tokens')
            if isinstance(n, int) and n > 0 and (not points or n > points[-1][1]):
                points.append((time.perf_counter()-start, n))
            text = event.get('text', text)
    rate = None
    if len(points) > 1 and points[-1][0] > points[0][0]:
        rate = (points[-1][1]-points[0][1]) / (points[-1][0]-points[0][0])
    return {'decode_delivery_tok_s': rate, 'token_arrival_points': points, 'text': text,
            'ttft_s': points[0][0] if points else None,
            'note': 'Rate from server cumulative token counts and client arrival times, excluding first-event prefill.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:30270')
    ap.add_argument('--output', default='benchmark.json')
    ap.add_argument('--reps', type=int, default=3)
    ap.add_argument('--max-tokens', type=int, default=512)
    args = ap.parse_args()
    prompts = [
        'Turkce cevap ver: 17 * 23 kac eder? Yalnizca sonucu yaz.',
        'Write a Python function to merge overlapping intervals. Include executable tests and explain edge cases.',
        'Explain how an NVMe-backed expert cache works in a mixture-of-experts model in about 250 words.',
    ]
    rows = [measure(args.url, p, args.max_tokens) for p in prompts for _ in range(args.reps)]
    decode = [measure_decode(args.url, args.max_tokens) for _ in range(args.reps)]
    rates = [r['end_to_end_tok_s'] for r in rows if r['end_to_end_tok_s'] is not None]
    extra = {}
    for path in ['/server_info', '/stats', '/nv_verify']:
        try:
            with request(args.url, path) as response:
                extra[path] = json.load(response)
        except Exception as error:
            extra[path] = {'error': str(error)}
    result = {'at': datetime.now(timezone.utc).isoformat(), 'url': args.url,
              'rows': rows, 'decode': decode,
              'median_end_to_end_tok_s': statistics.median(rates) if rates else None,
              'server': extra, 'quality_passed': None,
              'note': 'Task output needs inspection. This smoke suite alone does not certify model quality.'}
    pathlib.Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'requests': len(rows), 'median_end_to_end_tok_s': result['median_end_to_end_tok_s'],
                      'decode_delivery_tok_s': [r['decode_delivery_tok_s'] for r in decode]}))


if __name__ == '__main__':
    main()
