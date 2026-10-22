"""Small reusable HTTPS sessions; provider errors never expose credentials."""
import os
import threading
import copy
import logging
import secrets
import time
import math
from datetime import timezone
from email.utils import parsedate_to_datetime
import requests

_local = threading.local()


def post(*args, **kwargs):
    if not hasattr(_local, 'session'):
        _local.session = requests.Session()
    return _local.session.post(*args, **kwargs)


class ProviderError(RuntimeError):
    def __init__(self, code, message, status=502, retry_after=None):
        super().__init__(message)
        self.code, self.status, self.retry_after = code, status, retry_after
        self.reference = secrets.token_hex(4)


def retry_after_seconds(response):
    """Honor both HTTP Retry-After forms without logging provider headers."""
    value = str(getattr(response, 'headers', {}).get('Retry-After', '')).strip()
    if not value:
        return None
    try:
        if value.isascii() and value.isdigit():
            # Do not expose an unbounded provider header as a huge JSON number.
            return int(value) if len(value) <= 12 else None
        until = parsedate_to_datetime(value)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return max(0, math.ceil(until.timestamp() - time.time()))
    except (ValueError, TypeError, OverflowError):
        return None


def provider_error(response):
    status = response.status_code
    try:
        detail = response.json().get('error', {})
        text = str(detail.get('message', '')).lower()
    except (ValueError, AttributeError, TypeError):
        text = ''
    if status in (401, 403) or (status == 400 and any(word in text for word in ('api key', 'api_key', 'key expired'))):
        error = ProviderError('AI_ACCESS', 'Saathi’s AI connection needs attention. Please contact support; retrying this message will not fix the connection.', status)
    elif status == 429:
        error = ProviderError('AI_QUOTA', 'The AI service has reached its usage limit. Please try later. Your message is kept here.', status, retry_after_seconds(response))
    elif status == 404:
        error = ProviderError('AI_MODEL', 'The selected AI model is unavailable. Please contact support so the connection can be updated.', status)
    elif status == 400 and ('billing' in text or 'region' in text or 'location' in text):
        error = ProviderError('AI_CONFIGURATION', 'The AI service is not available with the current server setup. Please contact support.', status)
    elif status in (408, 500, 502, 503, 504):
        error = ProviderError('AI_BUSY', 'The AI service is temporarily busy. Please retry in a moment; your message is kept here.', status, retry_after_seconds(response))
    else:
        error = ProviderError('AI_REQUEST', 'The AI service could not accept this message. Try a shorter message or remove the attachment.', status)
    # Never log provider bodies, prompts, response text or credentials.
    logging.getLogger(__name__).warning('Gemini rejected request code=%s status=%s reference=%s', error.code, status, error.reference)
    return error


_choices = {}
_choice_lock = threading.Lock()


def discover_model(key, fast=True, exclude=None):
    if not key or key in ('fixture', 'secret-key', 'test-key'):
        return None
    try:
        r = requests.get('https://generativelanguage.googleapis.com/v1beta/models',
                         headers={'x-goog-api-key': key}, timeout=4)
        if r.status_code == 200:
            models = r.json().get('models', [])
            available = [
                m['name'].replace('models/', '')
                for m in models
                if 'generateContent' in m.get('supportedGenerationMethods', [])
                and m.get('name', '').startswith('models/gemini-')
                and not any(word in m['name'] for word in ('tts', 'image', 'audio', 'live', 'robotics', 'computer-use', 'transcribe', 'omni', 'customtools'))
            ]
            if exclude:
                available = [a for a in available if a != exclude]
            fast_pref = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-flash-lite-latest', 'gemini-2.5-flash-lite', 'gemini-2.5-flash']
            study_pref = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-flash-lite-latest', 'gemini-2.5-flash', 'gemini-2.5-flash-lite']
            prefs = fast_pref if fast else study_pref
            for p in prefs:
                if p in available:
                    return p
            for a in available:
                if 'flash' in a:
                    return a
            if available:
                return available[0]
    except Exception:
        pass
    return None


def model_payload(model, payload):
    """Omit sampling fields deprecated by the newer GenerateContent models."""
    body = copy.deepcopy(payload)
    if model in ('gemini-3.5-flash-lite', 'gemini-3.6-flash',
                 'gemini-3.7-flash', 'gemini-3.8-flash'):
        config = body.get('generationConfig', {})
        for field in ('temperature', 'topP', 'topK'):
            config.pop(field, None)
    return body


def send(post_request, key, model, payload, *, fast=False, stream=False, fallback_payload=None):
    """Recover one invalid model/configuration before output; never retry quota/access failures."""
    key = (key or '').strip("\"' \t\r\n")
    fast_fallbacks = ('gemini-3.5-flash-lite', 'gemini-3.1-flash-lite')
    fallback = os.environ.get('GEMINI_FALLBACK_MODEL')
    if not fallback:
        for f in fast_fallbacks:
            if f != model:
                fallback = f
                break
    with _choice_lock:
        cached = _choices.get((model, fast))
    if cached and cached[2] <= time.monotonic():
        cached = None
    current = cached[0] if cached else model
    omit_thinking = cached[1] if cached else False
    body = copy.deepcopy(payload)
    if omit_thinking:
        body.get('generationConfig', {}).pop('thinkingConfig', None)
    deadline = time.monotonic() + (40 if fast else 65)
    def remaining_time():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderError('AI_TIMEOUT', 'The AI service took too long to start. Please retry; your message is kept here.')
        return remaining

    def switch_available_model():
        nonlocal current, omit_thinking, body
        remaining_time()
        candidate = discover_model(key, fast=True, exclude=current) or fallback
        if not candidate or candidate == current or 'flash' not in candidate:
            return False
        current, omit_thinking = candidate, fast
        if fast and fallback_payload is not None:
            body = copy.deepcopy(fallback_payload)
        if omit_thinking:
            body.get('generationConfig', {}).pop('thinkingConfig', None)
        return True

    for attempt in range(2):
        attempted_model=current
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + current
        url += ':streamGenerateContent?alt=sse' if stream else ':generateContent'
        response = None
        try:
            remaining = remaining_time()
            recoverable_lite = current in fast_fallbacks
            read_limit = 15 if (fast or recoverable_lite) and attempt == 0 else 30 if fast else 45
            connect_limit = min(5, remaining / 2)
            options = dict(headers={'x-goog-api-key': key}, json=model_payload(current, body), timeout=(connect_limit, min(read_limit, remaining - connect_limit)))
            if stream:
                options['stream'] = True
            response = post_request(url, **options)
            response.raise_for_status()
            logging.getLogger(__name__).info('Gemini accepted model=%s fast=%s stream=%s attempt=%s',current,fast,stream,attempt+1)
            if current != model or omit_thinking:
                with _choice_lock:
                    _choices[(model, fast)] = (current, omit_thinking, time.monotonic() + 180)
            return response
        except requests.HTTPError as exc:
            rejected = response if response is not None else exc.response
            if rejected is None:
                raise ProviderError('AI_CONNECTION', 'Saathi could not connect to the AI service. Please retry.') from None
            try:
                detail = str(rejected.json().get('error', {}).get('message', '')).lower()
            except (ValueError, AttributeError, TypeError):
                detail = ''
            # A received 5xx rejection has no response output to replay. Recover once
                # within the same time budget; never replay output or quota failures.
            retry_value = getattr(rejected, 'headers', {}).get('Retry-After', '')
            retry_delay = retry_after_seconds(rejected) if retry_value else 1
            if attempt == 0 and rejected.status_code in (500, 502, 503, 504) and retry_delay is not None and retry_delay <= 2 and deadline - time.monotonic() > retry_delay + 6:
                rejected.close()
                if fast or recoverable_lite:
                    switch_available_model()
                logging.getLogger(__name__).warning('Gemini transient rejection status=%s model=%s fallback=%s fast=%s stream=%s; one bounded retry', rejected.status_code,attempted_model,current,fast,stream)
                time.sleep(retry_delay)
                continue
            recover_model = rejected.status_code == 404
            recover_thinking = rejected.status_code == 400 and 'thinking' in detail and 'thinkingConfig' in body.get('generationConfig', {})
            if attempt == 0 and (recover_model or recover_thinking):
                rejected.close()
                remaining_time()
                if recover_model:
                    discovered = discover_model(key, fast=fast, exclude=current)
                    current = discovered or fallback
                omit_thinking = True
                body.get('generationConfig', {}).pop('thinkingConfig', None)
                continue
            error = provider_error(rejected)
            rejected.close()
            raise error from None
        except requests.Timeout:
            if response is not None:
                response.close()
            # Only generation requests that have returned no response may recover.
            # Stream consumption happens outside send(); partial output is never replayed.
            if (fast or recoverable_lite) and attempt == 0 and response is None and deadline - time.monotonic() > 10 and switch_available_model():
                logging.getLogger(__name__).warning('Gemini startup timeout model=%s fallback=%s fast=%s stream=%s; one bounded alternate-model attempt',attempted_model,current,fast,stream)
                continue
            logging.getLogger(__name__).warning('Gemini startup timeout model=%s fast=%s stream=%s; recovery exhausted',current,fast,stream)
            raise ProviderError('AI_TIMEOUT', 'The AI service took too long to start. Please retry; your message is kept here.') from None
        except requests.RequestException:
            if response is not None:
                response.close()
            raise ProviderError('AI_CONNECTION', 'Saathi cannot reach the AI service right now. Please retry when the connection is ready.') from None
