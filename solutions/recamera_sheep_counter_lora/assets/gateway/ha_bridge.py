#!/usr/bin/env python3
"""Bridge Meshtastic sheep counter MQTT topics into HA-friendly retained sensors.

Subscribes to  sheep/meshtastic  (published by meshtastic_mqtt_bridge.py),
parses EVT/HB lines from the text field, and publishes individual retained
MQTT topics that Home Assistant MQTT sensors can subscribe to:

    sheep/ha/in       →  total IN count       (retained)
    sheep/ha/out      →  total OUT count      (retained)
    sheep/ha/inside   →  current inside count (retained)
    sheep/ha/event    →  JSON payload for HA event sensor
"""

import json
import os
import re
import signal
import sys
import time

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
INPUT_TOPIC = "sheep/meshtastic"
HA_TOPIC_IN = "sheep/ha/in"
HA_TOPIC_OUT = "sheep/ha/out"
HA_TOPIC_INSIDE = "sheep/ha/inside"
HA_TOPIC_EVENT = "sheep/ha/event"
HA_TOPIC_SET_LINE = "sheep/ha/line_config/set"
HA_TOPIC_LINE_STATUS = "sheep/ha/line_config/status"
HA_TOPIC_RESET = "sheep/ha/reset_counts/set"
MESHTASTIC_SEND_TOPIC = "sheep/meshtastic/send"

running = True

DISCOVERY_PREFIX = "homeassistant/sensor/sheep_counter"
DISCOVERY_DEVICE = {
    "identifiers": ["sheep_counter_lora"],
    "name": "Sheep Counter",
    "manufacturer": "Seeed Studio",
    "model": "reCamera LoRa Sheep Counter",
}

# Soft-reset offset: allows the dashboard to show counts relative to the last
# reset, even if the camera's internal counters were not cleared (e.g. the
# gate-side XIAO is not relaying RESET_COUNTS over LoRa).
# We use the camera uptime field to ignore stale/out-of-order LoRa messages
# that arrive after the reset, preventing negative counts.
reset_offset = {"in": 0, "out": 0, "uptime": -1}
reset_pending = False

def log(msg):
    print(msg, flush=True)

def parse_count_line(text):
    # EVT,dir,in,out,inside,uptime
    # HB,in,out,inside,uptime
    m = re.match(r"^(EVT|HB),(\w+),(\d+),(\d+),(\d+),(\d+)", text)
    if m and m.group(1) == "EVT":
        return {
            "type": "event",
            "direction": m.group(2),
            "in": int(m.group(3)),
            "out": int(m.group(4)),
            "inside": int(m.group(5)),
            "uptime": int(m.group(6)),
        }
    m = re.match(r"^(HB),(\d+),(\d+),(\d+),(\d+)", text)
    if m:
        return {
            "type": "heartbeat",
            "in": int(m.group(2)),
            "out": int(m.group(3)),
            "inside": int(m.group(4)),
            "uptime": int(m.group(5)),
        }
    return None

def parse_line_ok(text):
    m = re.match(r"^LINE_OK,(\d+),(\d+),(\d+),(\d+),(-?\d+)", text)
    if not m:
        return None
    return {
        "type": "line_ok",
        "x1": int(m.group(1)),
        "y1": int(m.group(2)),
        "x2": int(m.group(3)),
        "y2": int(m.group(4)),
        "in_sign": int(m.group(5)),
    }

def publish_discovery(client):
    """Create the MQTT sensor entities consumed by the bundled dashboard."""
    sensors = {
        "in": {
            "name": "Sheep IN",
            "unique_id": "sheep_in",
            "state_topic": HA_TOPIC_IN,
            "icon": "mdi:door-open",
        },
        "out": {
            "name": "Sheep OUT",
            "unique_id": "sheep_out",
            "state_topic": HA_TOPIC_OUT,
            "icon": "mdi:door-closed",
        },
        "inside": {
            "name": "Sheep Inside",
            "unique_id": "sheep_inside",
            "state_topic": HA_TOPIC_INSIDE,
            "icon": "mdi:sheep",
        },
        "last_event": {
            "name": "Sheep Last Event",
            "unique_id": "sheep_last_event",
            "state_topic": HA_TOPIC_EVENT,
            "value_template": "{{ value_json.direction | default('waiting') }}",
            "json_attributes_topic": HA_TOPIC_EVENT,
            "icon": "mdi:timeline-clock",
        },
    }
    for object_id, config in sensors.items():
        config["device"] = DISCOVERY_DEVICE
        client.publish(
            f"{DISCOVERY_PREFIX}/{object_id}/config",
            json.dumps(config),
            retain=True,
        )
    log("[ha-bridge] Home Assistant MQTT discovery published")

def on_connect(client, userdata, flags, reason_code, properties):
    log(f"[ha-bridge] connected to MQTT (rc={reason_code})")
    client.subscribe(INPUT_TOPIC)
    client.subscribe(HA_TOPIC_SET_LINE)
    client.subscribe(HA_TOPIC_RESET)
    publish_discovery(client)

def on_message(client, userdata, msg):
    global reset_pending, reset_offset
    if msg.topic == HA_TOPIC_RESET:
        client.publish(MESHTASTIC_SEND_TOPIC, "RESET_COUNTS")
        # Arm the soft reset. The next camera message will set the offset so
        # the dashboard shows 0 at that moment, even if the camera itself did
        # not reset (e.g. custom XIAO firmware not relaying the command).
        reset_pending = True
        client.publish(HA_TOPIC_IN, "0", retain=True)
        client.publish(HA_TOPIC_OUT, "0", retain=True)
        client.publish(HA_TOPIC_INSIDE, "0", retain=True)
        client.publish(HA_TOPIC_EVENT, "{}", retain=True)
        log("[ha-bridge] RESET_COUNTS forwarded to LoRa; HA topics cleared, soft reset armed")
        return

    if msg.topic == HA_TOPIC_SET_LINE:
        try:
            payload = json.loads(msg.payload)
            x1, y1 = payload.get("x1", 0), payload.get("y1", 0)
            x2, y2 = payload.get("x2", 1280), payload.get("y2", 720)
            in_sign = payload.get("in_sign", -1)
            cmd = f"SET_LINE,{x1},{y1},{x2},{y2},{in_sign}"
            client.publish(MESHTASTIC_SEND_TOPIC, cmd)
            log(f"[ha-bridge] Forwarding config to LoRa: {cmd}")
        except Exception as e:
            log(f"[ha-bridge] config error: {e}")
        return

    # Handle incoming meshtastic payload
    try:
        payload = json.loads(msg.payload)
        text = payload.get("text", "")
        if not text:
            return

        # Camera-originated reset acknowledgment
        if text.startswith("RESET_OK,"):
            reset_offset = {"in": 0, "out": 0, "uptime": -1}
            reset_pending = False
            client.publish(HA_TOPIC_IN, "0", retain=True)
            client.publish(HA_TOPIC_OUT, "0", retain=True)
            client.publish(HA_TOPIC_INSIDE, "0", retain=True)
            client.publish(HA_TOPIC_EVENT, "{}", retain=True)
            log("[ha-bridge] RESET_OK: camera counters cleared")
            return

        # Check for LINE_OK acknowledgment first
        line_ok = parse_line_ok(text)
        if line_ok:
            status_payload = json.dumps({
                "status": "applied",
                "x1": line_ok["x1"],
                "y1": line_ok["y1"],
                "x2": line_ok["x2"],
                "y2": line_ok["y2"],
                "in_sign": line_ok["in_sign"],
                "timestamp": int(time.time()),
            })
            client.publish(HA_TOPIC_LINE_STATUS, status_payload, retain=True)
            log(f"[ha-bridge] LINE_OK: camera confirmed config ({line_ok['x1']},{line_ok['y1']})-({line_ok['x2']},{line_ok['y2']}) sign={line_ok['in_sign']}")
            return

        parsed = parse_count_line(text)
        if not parsed:
            return
        t = int(time.time())

        # Apply soft-reset offset if armed or already active.
        raw_i, raw_o, raw_uptime = parsed["in"], parsed["out"], parsed["uptime"]
        if reset_pending:
            reset_offset["in"] = raw_i
            reset_offset["out"] = raw_o
            reset_offset["uptime"] = raw_uptime
            reset_pending = False
            log(f"[ha-bridge] soft reset applied at in={raw_i} out={raw_o} uptime={raw_uptime}")
        elif raw_uptime < reset_offset["uptime"]:
            # Stale/out-of-order message arrived after reset; ignore it so the
            # dashboard doesn't show negative or confusing counts.
            log(f"[ha-bridge] ignoring stale message (uptime={raw_uptime} < offset_uptime={reset_offset['uptime']})")
            return
        i = raw_i - reset_offset["in"]
        o = raw_o - reset_offset["out"]
        ins = i - o

        if parsed["type"] == "event":
            d = parsed["direction"]
            client.publish(HA_TOPIC_IN, str(i), retain=True)
            client.publish(HA_TOPIC_OUT, str(o), retain=True)
            client.publish(HA_TOPIC_INSIDE, str(ins), retain=True)
            event_payload = json.dumps({
                "direction": d,
                "in": i,
                "out": o,
                "inside": ins,
                "timestamp": t,
            })
            client.publish(HA_TOPIC_EVENT, event_payload, retain=True)
            log(f"[ha-bridge] EVT {d}  in={i} out={o} inside={ins}  (raw in={raw_i} out={raw_o})")
        else:
            client.publish(HA_TOPIC_IN, str(i), retain=True)
            client.publish(HA_TOPIC_OUT, str(o), retain=True)
            client.publish(HA_TOPIC_INSIDE, str(ins), retain=True)
            log(f"[ha-bridge] HB  in={i} out={o} inside={ins}  (raw in={raw_i} out={raw_o})")
    except Exception as e:
        log(f"[ha-bridge] error: {e}")

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    log(f"[ha-bridge] disconnected (rc={reason_code})")

def sigterm(*_):
    global running
    running = False

signal.signal(signal.SIGTERM, sigterm)
signal.signal(signal.SIGINT, sigterm)

log("[ha-bridge] starting")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

try:
    while running:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    log("[ha-bridge] shutting down")
    client.loop_stop()
    client.disconnect()
