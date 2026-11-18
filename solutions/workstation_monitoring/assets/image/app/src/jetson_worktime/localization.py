"""Stable message metadata, sharing the browser's Chinese/English catalog."""
import json
from pathlib import Path

LANGUAGES = ('zh-CN', 'en')
MESSAGES = json.loads((Path(__file__).resolve().parents[2]/'frontend/public/locales.json').read_text())


def translate(key, params=None, locale='zh-CN'):
    return MESSAGES[key][locale].format(**(params or {}))


class LocalizedText(str):
    """Remains a JSON-compatible string for existing logs and API consumers."""
    def __new__(cls, value, *, message_key=None, params=None):
        instance = super().__new__(cls, value)
        instance.message_key = message_key
        instance.message_params = params or {}
        return instance


def reason(key, **params):
    return LocalizedText(translate(key, params), message_key=key, params=params)


def reason_fields(value):
    return dict(reason_code=getattr(value, 'message_key', None) or 'reason.unknown',
                reason_params=getattr(value, 'message_params', {}))


class LocalizedError(ValueError):
    def __init__(self, key, **params):
        self.message_key = key
        self.message_params = params
        super().__init__(translate(key, params))
