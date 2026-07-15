#!/usr/bin/env python3
"""Bridge Meshtastic packets from USB-connected XIAO to local MQTT broker."""
import json
import os
import sys
import time

import paho.mqtt.client as mqtt
from pubsub import pub
from meshtastic.serial_interface import SerialInterface

SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/ttyACM0")
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_TOPIC = "sheep/meshtastic"
MQTT_SEND_TOPIC = "sheep/meshtastic/send"

def log(msg):
    print(msg, flush=True)

def on_receive(packet, interface):
    try:
        decoded = packet.get("decoded", {})
        text = decoded.get("text", "")
        if not text:
            return
        
        payload = {
            "from": packet.get("fromId", "unknown"),
            "to": packet.get("toId", "unknown"),
            "channel": packet.get("channel", 0),
            "text": text,
            "timestamp": time.time(),
        }
        
        json_payload = json.dumps(payload)
        log(f"[mesh] ch={packet.get('channel', 0)} text={text}")
        mqtt_client.publish(MQTT_TOPIC, json_payload)
    except Exception as e:
        log(f"[bridge] error handling packet: {e}")

pub.subscribe(on_receive, "meshtastic.receive")

log(f"[bridge] opening Meshtastic serial interface on {SERIAL_PORT}")
interface = SerialInterface(SERIAL_PORT)
my_id = interface.getMyNodeInfo().get('user', {}).get('id', 'unknown')
log(f"[bridge] serial opened, my node: {my_id}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, reason_code, properties):
    log(f"[mqtt] connected with reason code {reason_code}")
    client.subscribe(MQTT_SEND_TOPIC)

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    log(f"[mqtt] disconnected: {reason_code}")

def on_mqtt_message(client, userdata, msg):
    if msg.topic == MQTT_SEND_TOPIC:
        try:
            text = msg.payload.decode("utf-8")
            log(f"[bridge] sending over LoRa: {text}")
            interface.sendText(text)
        except Exception as e:
            log(f"[bridge] error sending over LoRa: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_mqtt_message

log(f"[bridge] connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
mqtt_client.loop_start()

log("[bridge] running. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    log("[bridge] shutting down")
finally:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    interface.close()
