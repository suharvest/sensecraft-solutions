#!/usr/bin/env python3
"""Bridge Meshtastic packets to MQTT with Home Assistant Discovery for vibration detection."""

import copy
import json
import os
import re
import signal
import sys
import tempfile
import threading
import time

import paho.mqtt.client as mqtt
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/ttyACM0")
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME") or None
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD") or None
HEALTHY_FILE = "/tmp/healthy"
STATE_FILE = "/deps/vibration_bridge_state.json" if os.path.isdir("/deps") else "/tmp/vibration_bridge_state.json"

running = True
serial_connected = False
mqtt_connected = False
interface = None
mqtt_client = None

last_alarm_time = {}
discovered_trackers = set()
discovered_sensors = set()
known_nodes = {}
known_alarms = {}
state_lock = threading.Lock()


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def _save_state_locked() -> None:
    tmp_path = None
    fd = None
    try:
        data = {
            "known_nodes": copy.deepcopy(known_nodes),
            "known_alarms": dict(known_alarms),
            "last_alarm_time": dict(last_alarm_time),
        }
        state_dir = os.path.dirname(STATE_FILE)
        if state_dir and not os.path.exists(state_dir):
            os.makedirs(state_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=state_dir or ".", prefix="state_", suffix=".tmp")
        with open(fd, "w") as f:
            json.dump(data, f)
        fd = None
        os.replace(tmp_path, STATE_FILE)
        tmp_path = None
    except Exception as e:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        log(f"[bridge] failed to save state: {e}")


def save_state() -> None:
    with state_lock:
        _save_state_locked()


def load_state() -> None:
    global known_nodes, known_alarms, last_alarm_time
    with state_lock:
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            saved_nodes = data.get("known_nodes", {})
            if isinstance(saved_nodes, dict):
                known_nodes.update(saved_nodes)

            saved_alarms = data.get("known_alarms", {})
            saved_alarm_time = data.get("last_alarm_time", {})
            now = time.time()

            for nid, ts in saved_alarm_time.items():
                try:
                    ts_val = float(ts)
                except (ValueError, TypeError):
                    continue
                if now - ts_val >= 120:
                    known_alarms[nid] = "OFF"
                else:
                    last_alarm_time[nid] = ts_val
                    known_alarms[nid] = "ON"

            for nid, val in saved_alarms.items():
                if nid not in known_alarms:
                    known_alarms[nid] = val

            for nid in list(known_alarms.keys()):
                if nid not in known_nodes:
                    known_nodes[nid] = {}

            log(f"[bridge] loaded state: {len(known_nodes)} nodes, {len(known_alarms)} alarms from {STATE_FILE}")
        except Exception as e:
            log(f"[bridge] failed to load state: {e}")


def publish_tracker_discovery(client: mqtt.Client, node_id: str) -> bool:
    topic = f"homeassistant/device_tracker/vibration_{node_id}/config"
    payload = json.dumps({
        "name": f"T1000-E Tracker {node_id}",
        "object_id": f"vibration_{node_id}",
        "unique_id": f"vibration_{node_id}_tracker",
        "json_attributes_topic": f"vibration/mesh/{node_id}/position",
        "source_type": "gps",
        "device": {
            "identifiers": [f"t1000e_{node_id}"],
            "name": f"SenseCAP T1000-E ({node_id})",
            "model": "SenseCAP T1000-E Tracker",
            "manufacturer": "Seeed Studio",
        },
    })
    msg_info = client.publish(topic, payload, qos=1, retain=True)
    if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
        discovered_trackers.add(node_id)
        log(f"[ha] published device_tracker discovery for node {node_id}")
        return True
    log(f"[ha] failed to queue device_tracker discovery for node {node_id} (rc={msg_info.rc})")
    return False


def publish_sensor_discovery(client: mqtt.Client, node_id: str) -> bool:
    topic = f"homeassistant/binary_sensor/vibration_{node_id}/config"
    payload = json.dumps({
        "name": f"T1000-E Vibration Alarm {node_id}",
        "object_id": f"vibration_{node_id}",
        "unique_id": f"vibration_{node_id}_alarm",
        "state_topic": f"vibration/mesh/{node_id}/alarm",
        "device_class": "vibration",
        "payload_on": "ON",
        "payload_off": "OFF",
        "off_delay": 120,
        "device": {
            "identifiers": [f"t1000e_{node_id}"],
            "name": f"SenseCAP T1000-E ({node_id})",
            "model": "SenseCAP T1000-E Tracker",
            "manufacturer": "Seeed Studio",
        },
    })
    msg_info = client.publish(topic, payload, qos=1, retain=True)
    if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
        discovered_sensors.add(node_id)
        log(f"[ha] published binary_sensor discovery for node {node_id}")
        return True
    log(f"[ha] failed to queue binary_sensor discovery for node {node_id} (rc={msg_info.rc})")
    return False


def normalize_node_id(packet: dict) -> str:
    from_id = packet.get("fromId")
    if from_id:
        return str(from_id).lstrip("!").lower()
    num_from = packet.get("from")
    if num_from is not None:
        try:
            return f"{int(num_from):08x}".lower()
        except (ValueError, TypeError):
            return str(num_from).lower()
    return "unknown"


def classify_message_intent(text: str) -> tuple[bool, bool]:
    if not text:
        return False, False
    upper = text.upper()
    tokens = set(re.findall(r"\b[A-Z0-9_-]+\b", upper))
    clear_tokens = {"CLEAR", "ALARM_CLEAR", "ALARM-CLEAR", "NORMAL", "HEARTBEAT", "RESOLVED", "OK", "CLEARED"}
    alarm_tokens = {"VIBRATION_ALERT", "ALARM", "SOS", "ABNORMAL", "ALERT", "VIBRATION"}

    # Recovery/clear takes precedence so "ALARM CLEAR" or "ALARM_CLEAR" clears the alarm
    if any(tok in tokens for tok in clear_tokens) or "ALARM CLEAR" in upper:
        return False, True
    if any(tok in tokens for tok in alarm_tokens):
        return True, False
    return False, False


def on_receive(packet, interface):
    try:
        node_id = normalize_node_id(packet)
        if not node_id or node_id == "unknown":
            return

        decoded = packet.get("decoded", {})
        text = decoded.get("text", "")
        is_alarm, is_clear = classify_message_intent(text)

        pos = decoded.get("position")
        if not isinstance(pos, dict) and ("latitude_i" in decoded or "latitude" in decoded):
            pos = decoded

        lat = None
        lon = None
        alt = 0
        if isinstance(pos, dict):
            lat = pos.get("latitude")
            if lat is None and "latitude_i" in pos:
                lat = pos["latitude_i"] / 1e7
            lon = pos.get("longitude")
            if lon is None and "longitude_i" in pos:
                lon = pos["longitude_i"] / 1e7
            alt = pos.get("altitude", 0)

        with state_lock:
            if node_id not in known_nodes:
                known_nodes[node_id] = {}

            state_changed = False
            alarm_to_publish = None

            # First, process text message if present
            if text:
                log(f"[mesh] node {node_id} text: {text}")
                if is_alarm:
                    known_alarms[node_id] = "ON"
                    last_alarm_time[node_id] = time.time()
                    state_changed = True
                    alarm_to_publish = "ON"
                    log(f"[alarm] node {node_id} vibration/SOS alert -> ON")
                elif is_clear:
                    known_alarms[node_id] = "OFF"
                    last_alarm_time.pop(node_id, None)
                    state_changed = True
                    alarm_to_publish = "OFF"
                    log(f"[alarm] node {node_id} normal/heartbeat -> OFF")

            # Next, ensure sensor discovery is registered for this node
            need_sensor_discovery = node_id not in discovered_sensors and mqtt_connected

            if need_sensor_discovery:
                current_alarm = known_alarms.get(node_id, "OFF")
                if current_alarm == "ON":
                    if (time.time() - last_alarm_time.get(node_id, 0)) >= 120:
                        current_alarm = "OFF"
                        known_alarms[node_id] = "OFF"
                        last_alarm_time.pop(node_id, None)
                        state_changed = True
                else:
                    known_alarms[node_id] = "OFF"
                    state_changed = True
                alarm_to_publish = current_alarm

            if need_sensor_discovery:
                publish_sensor_discovery(mqtt_client, node_id)
                if mqtt_connected and alarm_to_publish is not None:
                    mqtt_client.publish(f"vibration/mesh/{node_id}/alarm", alarm_to_publish, qos=1, retain=True)
                    log(f"[alarm] initial state for node {node_id} -> {alarm_to_publish} (retained)")
            elif alarm_to_publish is not None:
                if mqtt_connected:
                    mqtt_client.publish(f"vibration/mesh/{node_id}/alarm", alarm_to_publish, qos=1, retain=True)
                    log(f"[alarm] node {node_id} state changed -> {alarm_to_publish} (retained)")

            # Handle position packet
            if lat is not None and lon is not None:
                pos_changed = (
                    known_nodes[node_id].get("lat") != lat
                    or known_nodes[node_id].get("lon") != lon
                    or known_nodes[node_id].get("alt") != alt
                )
                known_nodes[node_id]["lat"] = lat
                known_nodes[node_id]["lon"] = lon
                known_nodes[node_id]["alt"] = alt
                if pos_changed:
                    state_changed = True

                # Home Assistant Device Tracker Discovery (qos=1, retain=True)
                if node_id not in discovered_trackers and mqtt_connected:
                    publish_tracker_discovery(mqtt_client, node_id)

                if mqtt_connected:
                    pos_topic = f"vibration/mesh/{node_id}/position"
                    pos_payload = json.dumps({
                        "latitude": lat,
                        "longitude": lon,
                        "altitude": alt,
                        "gps_accuracy": 5,
                    })
                    mqtt_client.publish(pos_topic, pos_payload, qos=1, retain=True)
                    log(f"[mesh] node {node_id} position: lat={lat}, lon={lon}, alt={alt}")

            if state_changed:
                _save_state_locked()

    except Exception as e:
        log(f"[bridge] error handling packet: {e}")


def replay_all_states(client: mqtt.Client) -> None:
    now = time.time()
    with state_lock:
        state_changed = False
        for nid, info in list(known_nodes.items()):
            alarm_state = known_alarms.get(nid, "OFF")
            if alarm_state == "ON":
                if (now - last_alarm_time.get(nid, 0)) < 120:
                    pub_alarm = "ON"
                else:
                    known_alarms[nid] = "OFF"
                    last_alarm_time.pop(nid, None)
                    pub_alarm = "OFF"
                    state_changed = True
            else:
                pub_alarm = "OFF"

            publish_sensor_discovery(client, nid)
            client.publish(f"vibration/mesh/{nid}/alarm", pub_alarm, qos=1, retain=True)
            if info.get("lat") is not None and info.get("lon") is not None:
                publish_tracker_discovery(client, nid)
                pos_topic = f"vibration/mesh/{nid}/position"
                pos_payload = json.dumps({
                    "latitude": info["lat"],
                    "longitude": info["lon"],
                    "altitude": info.get("alt", 0),
                    "gps_accuracy": 5,
                })
                client.publish(pos_topic, pos_payload, qos=1, retain=True)

        if state_changed:
            _save_state_locked()


def on_mqtt_connect(client, userdata, flags, reason_code, properties=None):
    global mqtt_connected
    is_success = reason_code == 0 or (hasattr(reason_code, "is_failure") and not reason_code.is_failure)
    if is_success:
        mqtt_connected = True
        log(f"[mqtt] connected to broker {MQTT_HOST}:{MQTT_PORT} (reason_code: {reason_code})")
        # Clear discovered sets on reconnect/connect so discovery is refreshed
        discovered_trackers.clear()
        discovered_sensors.clear()

        # Subscribe to Home Assistant birth message to replay state if HA restarts
        client.subscribe("homeassistant/status")

        # Re-publish discovery and state for all known nodes
        replay_all_states(client)
    else:
        mqtt_connected = False
        log(f"[mqtt] connection failed to {MQTT_HOST}:{MQTT_PORT} (reason_code: {reason_code})")


def on_mqtt_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="ignore").strip()
        log(f"[mqtt] message received on {topic}: {payload}")
        if topic == "homeassistant/status" and payload.lower() == "online":
            log("[ha] Home Assistant birth message received, replaying discovery and states...")
            discovered_trackers.clear()
            discovered_sensors.clear()
            replay_all_states(client)
    except Exception as e:
        log(f"[mqtt] error handling MQTT message: {e}")


def on_mqtt_disconnect(client, userdata, disconnect_flags, reason_code=None, properties=None):
    global mqtt_connected
    mqtt_connected = False
    log(f"[mqtt] disconnected from broker: {reason_code}")


def sig_handler(signum, frame):
    global running
    log(f"[bridge] received signal {signum}, stopping...")
    running = False


def on_connection_lost(interface=None, topic=None):
    global serial_connected
    log("[bridge] meshtastic.connection.lost event received, exiting to let container restart...")
    serial_connected = False
    if os.path.exists(HEALTHY_FILE):
        try:
            os.remove(HEALTHY_FILE)
        except Exception:
            pass
    sys.exit(1)


def main():
    global running, serial_connected, mqtt_connected, interface, mqtt_client

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_connection_lost, "meshtastic.connection.lost")

    load_state()

    # Open Meshtastic serial interface with retry
    while running:
        try:
            log(f"[bridge] opening Meshtastic serial interface on {SERIAL_PORT}")
            interface = SerialInterface(SERIAL_PORT)
            node_info = interface.getMyNodeInfo() or {}
            my_id = node_info.get("user", {}).get("id", "unknown")
            log(f"[bridge] serial connected, local node id: {my_id}")
            serial_connected = True
            break
        except Exception as e:
            serial_connected = False
            log(f"[bridge] serial open failed ({e}), retrying in 5 seconds...")
            time.sleep(5)

    # Connect MQTT with retry
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_disconnect = on_mqtt_disconnect
    mqtt_client.on_message = on_mqtt_message

    log(f"[bridge] connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
    while running:
        try:
            mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
            mqtt_client.loop_start()
            break
        except Exception as e:
            log(f"[bridge] MQTT connect failed ({e}), retrying in 5 seconds...")
            time.sleep(5)

    log("[bridge] meshtastic HA bridge running")

    last_health_touch = 0

    try:
        while running:
            now = time.time()

            # Check readiness: verify serial device is still physically present and connection intact
            if not os.path.exists(SERIAL_PORT) or not serial_connected:
                log(f"[bridge] serial connection lost or {SERIAL_PORT} missing, exiting to let container restart...")
                if os.path.exists(HEALTHY_FILE):
                    try:
                        os.remove(HEALTHY_FILE)
                    except Exception:
                        pass
                sys.exit(1)

            is_serial_ok = serial_connected and os.path.exists(SERIAL_PORT)
            is_healthy = is_serial_ok and mqtt_connected

            if is_healthy:
                if now - last_health_touch >= 5:
                    try:
                        with open(HEALTHY_FILE, "w") as f:
                            f.write(str(int(now)))
                        last_health_touch = now
                    except Exception as e:
                        log(f"[health] failed to update {HEALTHY_FILE}: {e}")
            else:
                if os.path.exists(HEALTHY_FILE):
                    try:
                        os.remove(HEALTHY_FILE)
                        log(f"[health] removed {HEALTHY_FILE} (serial_ok={is_serial_ok}, mqtt_ok={mqtt_connected})")
                    except Exception as e:
                        log(f"[health] failed to remove {HEALTHY_FILE}: {e}")

            # Alarm timeout check (120s)
            with state_lock:
                now = time.time()
                nodes_to_clear = []
                for nid, alarm_time in list(last_alarm_time.items()):
                    if now - alarm_time >= 120:
                        known_alarms[nid] = "OFF"
                        last_alarm_time.pop(nid, None)
                        nodes_to_clear.append(nid)
                        log(f"[bridge] alarm timeout (120s) for node {nid}, resetting to OFF")
                        if mqtt_connected:
                            mqtt_client.publish(f"vibration/mesh/{nid}/alarm", "OFF", qos=1, retain=True)
                if nodes_to_clear:
                    _save_state_locked()

            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        log("[bridge] cleaning up resources")
        save_state()
        if os.path.exists(HEALTHY_FILE):
            try:
                os.remove(HEALTHY_FILE)
            except Exception:
                pass
        try:
            if mqtt_client:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
        except Exception:
            pass
        if interface:
            try:
                interface.close()
            except Exception:
                pass
        log("[bridge] shutdown complete")


if __name__ == "__main__":
    main()
