"""home_assistant_whole_home step 3 (cloud preset): devices/ha_connect_cloud.yaml.

The step configures Home Assistant over its API from the deploying machine
(app_collaboration ``ha_integration`` with ``entries`` / ``pipeline``). These
tests pin the properties the package relies on:

* the API key and the HA password reach only the deployer's HTTP calls to
  Home Assistant: they are never ``{{placeholder}}`` text, never in an action,
  and no voice-host device file mentions the key;
* an empty key skips the LiteLLM entry (the guide's manual step stays valid),
  while the Wyoming entries and the pipeline are still configured;
* the voice-host steps are unchanged by this feature.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "solutions" / "home_assistant_whole_home"
STEP = PKG / "devices" / "ha_connect_cloud.yaml"
SECRET_INPUTS = {"llm_api_key", "ha_password"}


def load():
    return yaml.safe_load(STEP.read_text())


def flow_fields(doc):
    for entry in doc["ha_integration"]["entries"]:
        yield entry, entry.get("data", [])
        for sub in entry.get("subentries", []):
            yield entry, sub.get("data", [])


def test_secrets_are_password_inputs_used_only_as_flow_values():
    doc = load()
    inputs = {i["id"]: i for i in doc["user_inputs"]}
    text = STEP.read_text()
    for name in SECRET_INPUTS:
        assert inputs[name]["type"] == "password"
        # No pattern: any character the provider uses in a key is accepted;
        # the app passes the value as JSON to Home Assistant, not to a shell.
        assert "validation" not in inputs[name]
        assert not re.search(r"\{\{\s*" + name + r"\s*\}\}", text), name
    assert not doc.get("actions") and "docker" not in doc and "ssh" not in doc
    used = {f["value_from"] for _, fields in flow_fields(doc) for f in fields if f.get("value_from")}
    assert "llm_api_key" in used


def test_key_never_reaches_the_voice_host():
    for path in (PKG / "devices").glob("*_voice.yaml"):
        assert "llm_api_key" not in path.read_text(), path.name
        assert "api_key" not in path.read_text(), path.name


def test_empty_key_skips_only_the_llm():
    doc = load()
    entries = {e["id"]: e for e in doc["ha_integration"]["entries"]}
    assert entries["llm"]["skip_if_empty"] == ["llm_api_key"]
    assert not entries["stt"].get("skip_if_empty") and not entries["tts"].get("skip_if_empty")
    pipeline = doc["ha_integration"]["pipeline"]
    assert pipeline["conversation"] == "llm.agent"
    assert pipeline["stt"] == "stt" and pipeline["tts"] == "tts"
    assert pipeline["prefer_local_intents"] is True


def test_agent_does_not_control_home_assistant():
    """The guide's agent leaves "Control Home Assistant" off: device commands go
    to HA's built-in intents (prefer_local_intents) and the LLM prompt tells it
    not to claim it switched a device."""
    doc = load()
    (sub,) = [s for e in doc["ha_integration"]["entries"] for s in e.get("subentries", [])]
    fields = {f["name"]: f for f in sub["data"]}
    assert set(fields) == {"model", "prompt", "llm_hass_api"}
    # Sent as [] so HA's form default does not turn device control on.
    assert fields["llm_hass_api"] == {"name": "llm_hass_api", "value": "", "type": "list"}
    prompt = next(f["value"] for f in sub["data"] if f["name"] == "prompt")
    assert "do not say it is done" in prompt


def test_inputs_reuse_step_ids_so_values_are_prefilled():
    """Same input ids as steps 1 and 2 are prefilled by the app."""
    ids = {i["id"] for i in load()["user_inputs"]}
    step2 = {i["id"] for i in yaml.safe_load((PKG / "devices" / "rk3588_voice.yaml").read_text())["user_inputs"]}
    assert {"wyoming_stt_port", "wyoming_tts_port", "llm_base_url"} <= ids & step2
    assert "ha_port" in {i["id"] for i in yaml.safe_load((PKG / "devices" / "ha_rpi.yaml").read_text())["user_inputs"]}


def test_guides_keep_manual_llm_step_for_empty_key():
    en = (PKG / "guide.md").read_text()
    zh = (PKG / "guide_zh.md").read_text()
    for text in (en, zh):
        assert "{#rk_ha_connect type=ha_integration required=true config=devices/ha_connect_cloud.yaml}" in text
        assert "{#rk_verify type=web_dashboard required=true config=devices/verify_ha.yaml}" in text
    assert "**Only if you left the API key empty in step 3**" in en
    assert "**仅当步骤 3 的服务密钥留空时**" in zh
