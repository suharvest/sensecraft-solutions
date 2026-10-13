"""Nothing this CLI prints may carry a credential — and everything else it
prints must stay readable."""

from __future__ import annotations

import json

import pytest

from solutionctl._redact import redact, redacted_json


@pytest.mark.parametrize(
    "text",
    [
        'connection {"host": "1.2.3.4", "password": "hunter2"}',
        "connection {'username': 'pi', 'password': 'hunter2'}",
        "ssh failed: password=hunter2",
        'api_key: "hunter2"',
        r'{"password": "hun\"ter2"}',
        "https://cdn.example/m.bin?token=hunter2",
        "PRIVATE_KEY=hunter2",
    ],
)
def test_secrets_never_survive(text):
    assert "hunter2" not in redact(text)
    assert "<REDACTED>" in redact(text)


@pytest.mark.parametrize(
    "text,kept",
    [
        ("https://cdn.example/m.bin?token=x&arch=aarch64", "arch=aarch64"),
        ('{"password": "x", "host": "1.2.3.4"}', "1.2.3.4"),
        ("password=x; board=rk3588", "board=rk3588"),
        ("no secrets here", "no secrets here"),
    ],
)
def test_the_rest_of_the_message_survives(text, kept):
    assert kept in redact(text)


def test_json_masks_a_secret_field_whatever_its_shape():
    payload = {
        "password": "hunter2",
        "secret": {"value": "hunter2"},
        "tokens": ["hunter2"],
        "params": {"board": "rk3588"},
        "detail": 'refused {"password": "hunter2"}',
    }
    out = redacted_json(payload)
    assert "hunter2" not in out
    parsed = json.loads(out)  # still machine-readable
    assert parsed["password"] == "<REDACTED>"
    assert parsed["secret"] == "<REDACTED>"  # the whole object, not walked into
    assert parsed["params"] == {"board": "rk3588"}
    assert "<REDACTED>" in parsed["detail"]


def test_empty_values_are_left_alone():
    assert json.loads(redacted_json({"password": "", "token": None})) == {
        "password": "",
        "token": None,
    }
