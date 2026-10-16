"""Config writers that take user inputs from an action's env: map.

Each case extracts the Python heredoc from the action's ``run`` script, fills
the remaining ``{{name}}`` placeholders from the package's user_inputs
defaults, runs it with the input in ``os.environ`` and checks that the value
in the written file equals the input -- including non-ASCII text and an
astral-plane emoji, which a YAML file must hold as literal UTF-8 (PyYAML does
not join ``\\ud83d\\udd11`` surrogate escapes back into one character).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1] / "solutions"

URL = 'rtsp://admin:钥匙🔑p$s!#?&"x;y@10.0.0.1:554/s?a=1&b=2'
WEBHOOK = "https://例え.example.com/钥匙🔑?a=1&b=$x!"
PASSWORD = '钥匙🔑p$s!#?&"x;y\\z'


def _action(path, name):
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("name") == name and "run" in node:
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    walk(doc)
    assert len(found) >= 1, f"{path}: no action {name!r}"
    defaults = {}

    def inputs(node):
        if isinstance(node, dict):
            for ui in node.get("user_inputs") or []:
                if isinstance(ui, dict) and ui.get("default") is not None:
                    defaults.setdefault(ui["id"], str(ui["default"]))
            for value in node.values():
                inputs(value)
        elif isinstance(node, list):
            for value in node:
                inputs(value)

    inputs(doc)
    return found[-1], defaults


def _python_body(run):
    # A heredoc may also run to the end of the script (no terminator line).
    match = re.search(r"python3 - [^\n]*<<'(\w+)'\n(.*?)(?:\n\1\n|\n?\Z)", run, re.S)
    assert match, "no python heredoc in the action"
    return match.group(2)


def _run(rel, action_name, args, env, defaults_extra=None):
    action, defaults = _action(ROOT / rel, action_name)
    defaults.update(defaults_extra or {})
    for key, value in env.items():
        assert key in action.get("env", {}), f"{key} is not in the action's env: map"
    body = re.sub(
        r"\{\{(\w+)\}\}", lambda m: defaults.get(m.group(1), "1"), _python_body(action["run"])
    )
    assert "{{" not in body
    subprocess.run(
        [sys.executable, "-", *args],
        input=body,
        text=True,
        encoding="utf-8",
        check=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", **env},
        capture_output=True,
    )


def _same(got, want):
    assert got == want
    got.encode("utf-8")


ALARM_PANELS = [
    "fall_detection/devices/jetson_fall.yaml",
    "fall_detection/devices/rk3576_fall.yaml",
    "fall_detection/devices/rk3588_fall.yaml",
    "fall_detection/devices/rk_auto_fall.yaml",
    "fall_detection/devices/hailo_fall.yaml",
]


@pytest.mark.parametrize("rel", ALARM_PANELS)
def test_alarm_panel_webhook_round_trips(tmp_path, rel):
    out = tmp_path / "alarm-panel.yaml"
    _run(rel, "Write the alarm panel configuration", [str(out)], {"INPUT_WEBHOOK_URL": WEBHOOK})
    conf = yaml.safe_load(out.read_text(encoding="utf-8"))
    _same(conf["notifiers"][0]["options"]["url"], WEBHOOK)


def test_panel_host_password_and_webhook_round_trip(tmp_path):
    out = tmp_path / "alarm-panel.yaml"
    _run(
        "fall_detection/devices/panel_host.yaml",
        "Write the panel configuration",
        [str(out)],
        {"INPUT_WEBHOOK_URL": WEBHOOK, "INPUT_BROKER_PASSWORD": PASSWORD},
    )
    conf = yaml.safe_load(out.read_text(encoding="utf-8"))
    _same(conf["mqtt"]["password"], PASSWORD)
    _same(conf["notifiers"][0]["options"]["url"], WEBHOOK)


def test_go2rtc_stream_urls_round_trip(tmp_path):
    conf = tmp_path / "go2rtc.yaml"
    conf.write_text("api:\n  listen: :1984\nstreams: {}\n", encoding="utf-8")
    manual = f"cam-01={URL}, cam-02=rtsp://192.168.1.51:554/stream"
    _run(
        "recamera_heatmap_grafana/devices/backend_deploy.yaml",
        "Find the cameras",
        [str(conf), manual],
        {"INPUT_CAMERA_URLS": manual},
    )
    streams = yaml.safe_load(conf.read_text(encoding="utf-8"))["streams"]
    _same(streams["cam-01"], URL)
    _same(streams["cam-02"], "rtsp://192.168.1.51:554/stream")


JSON_CONFIGS = [
    ("fall_detection/devices/jetson_fall.yaml", "Write the camera and MQTT configuration",
     {}, lambda c: c["streams"][0]["rtsp_url"], "INPUT_RTSP_URL"),
    ("fall_detection/devices/rk3576_fall.yaml", "Write the camera and MQTT configuration",
     {}, lambda c: c["streams"][0]["rtsp_url"], "INPUT_RTSP_URL"),
    ("fall_detection/devices/rk3588_fall.yaml", "Write the camera and MQTT configuration",
     {}, lambda c: c["streams"][0]["rtsp_url"], "INPUT_RTSP_URL"),
    ("edge_waste_sorting/devices/hailo_waste.yaml", "Write the source, trigger and MQTT configuration",
     {"model": {}, "rules": {}, "trigger": {}, "mqtt": {}}, lambda c: c["sources"][0]["uri"], "INPUT_SOURCE_URI"),
    ("edge_waste_sorting/devices/jetson_waste.yaml", "Write the source, trigger and MQTT configuration",
     {"model": {}, "rules": {}, "trigger": {}, "mqtt": {}}, lambda c: c["sources"][0]["uri"], "INPUT_SOURCE_URI"),
]


@pytest.mark.parametrize("rel,action,seed,pick,var", JSON_CONFIGS)
def test_json_config_camera_url_round_trips(tmp_path, rel, action, seed, pick, var):
    out = tmp_path / "config.json"
    out.write_text(json.dumps(seed), encoding="utf-8")
    _run(rel, action, [str(out)], {var: URL})
    _same(pick(json.loads(out.read_text(encoding="utf-8"))), URL)


@pytest.mark.parametrize("rel", [
    "unmanned_store_access/devices/p2_j20.yaml",
    "unmanned_store_access/devices/p3_mqtt_relay.yaml",
])
def test_door_config_round_trips(tmp_path, rel):
    out = tmp_path / "access-node.json"
    out.write_text(json.dumps({"actuator": {}, "facedb": {}, "mqtt": {}, "policy": {}}), encoding="utf-8")
    env = {"INPUT_RTSP_URL": URL, "INPUT_FACEDB_URL": WEBHOOK, "INPUT_FACEDB_SIGNING_KEY": PASSWORD}
    _run(rel, "Write the door configuration", [str(out)], env, {"do_gpio": "463", "relay_id": "r1"})
    conf = json.loads(out.read_text(encoding="utf-8"))
    _same(conf["camera"]["rtsp_url"], URL)
    _same(conf["facedb"]["url"], WEBHOOK)
    _same(conf["facedb"]["signature_key"], PASSWORD)
