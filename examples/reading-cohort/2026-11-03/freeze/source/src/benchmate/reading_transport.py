"""One paid request per explicit stage, raw visible output retained, no retry."""
import base64
import json
from pathlib import Path
import time

from .records import Recorder, canonical
from .reading_rules import digest


def image_content(raw):
    from .image_archive import verify_clean_png
    verify_clean_png(raw)
    return {'type': 'input_image', 'image_url': 'data:image/png;base64,'+base64.b64encode(raw).decode()}


def call(content, *, tool, output, budget, model='muse-spark-1.3', client=None):
    import httpx
    from .config import load_keys, redact
    from .providers import PROVIDERS, reserve_budget, ProviderError
    payload = {'model': model, 'store': False, 'input': [{'role': 'user', 'content': content}]}
    if model == 'sam-3.1':
        payload.update(stream=False, metadata={'mask_encoding': 'one_bit', 'include_confidence': 'true'})
    else:
        payload.update(reasoning={'effort': 'medium'}, max_output_tokens=4096,
                       tools=[tool], tool_choice='auto', parallel_tool_calls=False)
    log = Recorder(output, mode='reading_pipeline_single_paid_request')
    request = {'model': model, 'payload_sha256': digest(payload), 'tool': tool,
               'requests_max': 1, 'automatic_retry': False, 'hardware_IO': False}
    if model == 'sam-3.1':
        import hashlib
        raw = base64.b64decode(content[1]['image_url'].split(',', 1)[1])
        log.add('sam_request_frozen', {'concept': content[0]['text'],
            'image_sha256': hashlib.sha256(raw).hexdigest(), **request})
    else:
        log.add('model_request_frozen', request)
    keys = {}; requests = 0; owned = client is None; http = None
    try:
        keys = load_keys(Path(__file__).resolve().parents[2]/'.env')
        key = keys.get('MODEL_API_KEY')
        if not key:
            raise ProviderError('Local Meta key unavailable.')
        if len(canonical(payload)) > 12_000_000:
            raise ValueError('Image request exceeds the bounded payload.')
        http = client or httpx.Client(timeout=120, follow_redirects=False)
        reserve_budget(budget, 'meta', 1.)
        requests = 1; start = time.monotonic()
        log.add('provider_request_sent', {'ordinal': 1, 'model': model})
        response = http.post(PROVIDERS['meta']['url'], json=payload, headers={'Authorization': 'Bearer '+key})
        if response.status_code >= 400:
            raise ProviderError('Meta HTTP '+str(response.status_code)+'; no retry.')
        body = response.json()
        visible = [x for x in body.get('output', []) if x.get('type') in ('message', 'function_call')]
        record = redact({'response_id': body.get('id'), 'status': body.get('status'),
            'usage': body.get('usage'), 'elapsed_s': time.monotonic()-start, 'visible_output': visible}, keys)
        (log.path/'response-visible.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
        log.add('provider_reply', record)
        if body.get('status') != 'completed':
            raise ProviderError('Incomplete response retained; no retry.')
        calls = [x for x in visible if x.get('type') == 'function_call']
        if model == 'sam-3.1':
            if calls:
                raise ProviderError('Unexpected SAM tool call.')
            text = ''.join(c.get('text', '') for x in visible if x.get('type') == 'message'
                           for c in x.get('content', []) if c.get('type') == 'output_text')
            (log.path/'output-text.txt').write_text(redact(text, keys))
            result = {'status': 'completed', 'text_empty': not bool(text.strip())}
        else:
            if len(calls) != 1 or calls[0].get('name') != tool['name']:
                raise ProviderError('Exactly one planned tool call required; no retry.')
            arguments = calls[0].get('arguments')
            if not isinstance(arguments, str) or len(arguments) > 16000:
                raise ValueError('Invalid bounded tool arguments.')
            result = {'status': 'completed', 'arguments': json.loads(redact(arguments, keys))}
        result.update(requests=requests, usage=body.get('usage'), model=model)
        (log.path/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        log.add('run_completed', result)
        return log.path, result
    except (Exception, KeyboardInterrupt) as exc:
        failure = {'status': 'failed', 'requests': requests, 'automatic_retry': False,
                   'error': str(exc) if isinstance(exc, (ValueError, ProviderError)) else type(exc).__name__}
        (log.path/'result.json').write_text(json.dumps(redact(failure, keys), indent=2)+'\n')
        log.add('run_failed', redact(failure, keys))
        raise RuntimeError('Paid stage failed; no retry. Record: '+str(log.path)) from None
    finally:
        if owned and http is not None:
            http.close()
