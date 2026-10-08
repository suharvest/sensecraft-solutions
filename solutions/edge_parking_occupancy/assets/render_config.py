#!/usr/bin/env python3
"""Render the parking config from the deploy-form inputs.

Called by the "Write the parking config" after_upload action in
devices/jetson_occupancy.yaml, devices/rk3588_occupancy.yaml and
devices/rk3576_occupancy.yaml. It reads the board's shipped vb.config/1 preset
(config/slots.json, slots-rk3588.json or slots-rk3576.json),
replaces the site, cameras, MQTT broker and editor port with the form values,
and writes the result to the path the compose file mounts.

Bays are not part of the form: each camera gets one starter bay (P-01) so the
analyzer is active from the first frame; users redraw bays in /slots/editor,
which stores them in <data>/slots.override.json and takes precedence over
this file on every start.

Usage: render_config.py TEMPLATE OUTPUT
Inputs come from the environment: RTSP_URLS, CAMERA_IDS, SITE_ID, MQTT_HOST,
MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, EDITOR_PORT, STREAM_CODEC (optional).
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
STARTER_BAY = [[0.40, 0.55], [0.60, 0.55], [0.60, 0.85], [0.40, 0.85]]


def fail(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
    raise SystemExit(1)


def split_list(raw: str) -> list[str]:
    return [item for item in re.split(r"[\s,;]+", raw.strip()) if item]


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: render_config.py TEMPLATE OUTPUT")
    template_path, output_path = sys.argv[1], sys.argv[2]
    with open(template_path, encoding="utf-8") as handle:
        config = json.load(handle)
    if config.get("schema") != "vb.config/1":
        fail(f"{template_path} is not a vb.config/1 preset")

    urls = split_list(os.environ.get("RTSP_URLS", ""))
    if not urls:
        fail("Camera RTSP address is empty. Enter at least one rtsp:// address.")
    bad = [u for u in urls if not u.lower().startswith(("rtsp://", "rtsps://"))]
    if bad:
        fail(f"Not an RTSP address: {bad[0]} (it must start with rtsp://)")
    if len(urls) > 16:
        fail(f"{len(urls)} cameras entered; one edge box takes at most 16.")

    ids = split_list(os.environ.get("CAMERA_IDS", ""))
    if not ids:
        ids = [f"cam-{i:02d}" for i in range(1, len(urls) + 1)]
    if len(ids) != len(urls):
        fail(f"{len(urls)} camera addresses but {len(ids)} camera IDs; enter one ID per address or leave the IDs empty.")
    for cam in ids:
        if not ID_RE.match(cam):
            fail(f"Camera ID {cam!r} may only use letters, digits, - and _ (up to 32 characters).")
    if len(set(ids)) != len(ids):
        fail("Camera IDs must be different from each other.")

    site_id = os.environ.get("SITE_ID", "").strip()
    if not ID_RE.match(site_id):
        fail(f"Site ID {site_id!r} may only use letters, digits, - and _ (up to 32 characters).")
    mqtt_host = os.environ.get("MQTT_HOST", "").strip()
    if not mqtt_host:
        fail("MQTT server address is empty.")
    try:
        mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
        editor_port = int(os.environ.get("EDITOR_PORT", "8080"))
    except ValueError:
        fail("MQTT port and slot editor port must be numbers.")
    if editor_port == 8099:
        fail("Port 8099 is used by the status check; pick another slot editor port.")
    mqtt_user = os.environ.get("MQTT_USERNAME", "")
    mqtt_pass = os.environ.get("MQTT_PASSWORD", "")
    codec = os.environ.get("STREAM_CODEC", "").strip()

    host = re.sub(r"[^A-Za-z0-9_-]", "-", socket.gethostname()) or "edge"
    device_id = f"occ-{host}"[:32]
    client_id = f"{site_id}-{device_id}"

    config["device_id"] = device_id
    config["health"] = {"host": "0.0.0.0", "port": 8099}
    mqtt = config.setdefault("mqtt", {})
    mqtt.update({
        "host": mqtt_host,
        "port": mqtt_port,
        "client_id": client_id,
        "username": mqtt_user,
        "password": mqtt_pass,
        "topic_root": f"{site_id}/parking/{device_id}",
    })

    template_stream = (config.get("streams") or [{}])[0]
    stream_options = dict(template_stream.get("options") or {})
    stream_options["max_fps"] = 1
    if codec:
        stream_options["codec"] = codec
        config.setdefault("backend", {}).setdefault("options", {})["codec"] = codec
    config["streams"] = [
        {
            "stream_id": cam,
            "url": url,
            "name": "",
            "transport": template_stream.get("transport", "tcp"),
            "score_threshold": None,
            "options": dict(stream_options),
        }
        for cam, url in zip(ids, urls)
    ]

    app = config.setdefault("app", {}).setdefault("options", {})
    app["site_id"] = site_id
    app.setdefault("mqtt", {}).update({
        "host": mqtt_host,
        "port": mqtt_port,
        "username": mqtt_user,
        "password": mqtt_pass,
    })
    app.setdefault("http", {})["port"] = editor_port
    app["slots"] = {cam: [{"id": "P-01", "polygon": STARTER_BAY}] for cam in ids}

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    tmp = output_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, output_path)
    print(f"config      = {output_path}")
    print(f"site        = {site_id}")
    print(f"cameras     = {', '.join(ids)}")
    print(f"mqtt        = {mqtt_host}:{mqtt_port}")
    print(f"slot editor = port {editor_port}")


if __name__ == "__main__":
    main()
