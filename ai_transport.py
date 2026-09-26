"""Small reusable HTTPS sessions; provider errors never expose credentials."""
import os
import threading
import copy
import logging
import secrets
import time
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
        value = getattr(response, 'headers', {}).get('Retry-After', '')
        retry_after = min(int(value), 3600) if str(value).isdigit() else None
        error = ProviderError('AI_QUOTA', 'The AI service has reached its usage limit. Please try later. Your message is kept here.', status, retry_after)
    elif status == 404:
        error = ProviderError('AI_MODEL', 'The selected AI model is unavailable. Please contact support so the connection can be updated.', status)
    elif status == 400 and ('billing' in text or 'region' in text or 'location' in text):
        error = ProviderError('AI_CONFIGURATION', 'The AI service is not available with the current server setup. Please contact support.', status)
    elif status in (408, 500, 502, 503, 504):
        error = ProviderError('AI_BUSY', 'The AI service is temporarily busy. Please retry in a moment; your message is kept here.', status)
    else:
        error = ProviderError('AI_REQUEST', 'The AI service could not accept this message. Try a shorter message or remove the attachment.', status)
    # Never log provider bodies, prompts, response text or credentials.
    logging.getLogger(__name__).warning('Gemini rejected request code=%s status=%s reference=%s', error.code, status, error.reference)
    return error


_choices = {}
_choice_lock = threading.Lock()


def send(post_request, key, model, payload, *, fast=False, stream=False):
    """Recover one invalid model/configuration before output; never retry quota/access failures."""
    fallback = os.environ.get('GEMINI_FALLBACK_MODEL', 'gemini-1.5-flash' if fast else 'gemini-1.5-pro')
    with _choice_lock:
        cached = _choices.get((model, fast))
    if cached and cached[2] <= time.monotonic():
        cached = None
    current = cached[0] if cached else model
    omit_thinking = cached[1] if cached else False
    body = copy.deepcopy(payload)
    if current != model or omit_thinking:
        body.get('generationConfig', {}).pop('thinkingConfig', None)
    for attempt in range(2):
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + current
        url += ':streamGenerateContent?alt=sse' if stream else ':generateContent'
        response = None
        try:
            options = dict(headers={'x-goog-api-key': key}, json=body, timeout=(5, 25 if fast else 45))
            if stream:
                options['stream'] = True
            response = post_request(url, **options)
            response.raise_for_status()
            if current != model or omit_thinking:
                with _choice_lock:
                    _choices[(model, fast)] = (current, omit_thinking, time.monotonic() + 600)
            return response
        except requests.HTTPError as exc:
            rejected = response if response is not None else exc.response
            if rejected is None:
                raise ProviderError('AI_CONNECTION', 'Saathi could not connect to the AI service. Please retry.') from None
            try:
                detail = str(rejected.json().get('error', {}).get('message', '')).lower()
            except (ValueError, AttributeError, TypeError):
                detail = ''
            recover_model = rejected.status_code == 404 and current != fallback
            recover_thinking = rejected.status_code == 400 and 'thinking' in detail and 'thinkingConfig' in body.get('generationConfig', {})
            if attempt == 0 and (recover_model or recover_thinking):
                rejected.close()
                if recover_model:
                    current = fallback
                omit_thinking = True
                body.get('generationConfig', {}).pop('thinkingConfig', None)
                continue
            error = provider_error(rejected)
            rejected.close()
            raise error from None
        except requests.Timeout:
            if response is not None:
                response.close()
            raise ProviderError('AI_TIMEOUT', 'The AI service took too long to start. Please retry; your message is kept here.') from None
        except requests.RequestException:
            if response is not None:
                response.close()
            raise ProviderError('AI_CONNECTION', 'Saathi cannot reach the AI service right now. Please retry when the connection is ready.') from None
