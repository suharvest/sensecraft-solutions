"""Tests for Meshtastic to Home Assistant MQTT bridge state persistence and alarm delivery."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SCRIPT = (
    ROOT
    / "solutions"
    / "industrial_vibration_detection"
    / "assets"
    / "docker"
    / "meshtastic_ha_bridge.py"
)


def load_bridge_module(tmp_path: Path):
    mock_mqtt_client = MagicMock()
    mock_mqtt_client.MQTT_ERR_SUCCESS = 0
    mock_mqtt_client.CallbackAPIVersion.VERSION2 = 2

    mock_paho = MagicMock()
    mock_paho.mqtt = MagicMock()
    mock_paho.mqtt.client = mock_mqtt_client

    mock_meshtastic = MagicMock()
    mock_pubsub = MagicMock()

    sys.modules["paho"] = mock_paho
    sys.modules["paho.mqtt"] = mock_paho.mqtt
    sys.modules["paho.mqtt.client"] = mock_mqtt_client
    sys.modules["meshtastic"] = mock_meshtastic
    sys.modules["meshtastic.serial_interface"] = mock_meshtastic
    sys.modules["pubsub"] = mock_pubsub

    sys.modules.pop("meshtastic_ha_bridge", None)

    spec = importlib.util.spec_from_file_location("meshtastic_ha_bridge", str(BRIDGE_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["meshtastic_ha_bridge"] = mod
    spec.loader.exec_module(mod)

    # Configure custom paths and reset globals
    mod.STATE_FILE = str(tmp_path / "vibration_bridge_state.json")
    mod.HEALTHY_FILE = str(tmp_path / "healthy")
    mod.known_nodes.clear()
    mod.known_alarms.clear()
    mod.last_alarm_time.clear()
    mod.discovered_sensors.clear()
    mod.discovered_trackers.clear()

    mock_res = MagicMock()
    mock_res.rc = 0
    mod.mqtt_client = MagicMock()
    mod.mqtt_client.publish.return_value = mock_res
    mod.mqtt_connected = True

    return mod


def test_first_packet_alarm_publishes_retained_on(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)

    packet = {
        "fromId": "!abcdef12",
        "decoded": {"text": "VIBRATION_ALERT detected on motor bearing"},
    }

    bridge.on_receive(packet, None)

    # Discovery published
    assert "abcdef12" in bridge.discovered_sensors
    assert bridge.known_alarms.get("abcdef12") == "ON"
    assert "abcdef12" in bridge.last_alarm_time

    # Verify MQTT publishes: discovery + retained ON
    pub_calls = bridge.mqtt_client.publish.call_args_list
    assert len(pub_calls) == 2

    # Call 1: discovery config
    disc_topic, disc_payload = pub_calls[0][0][0], pub_calls[0][0][1]
    assert disc_topic == "homeassistant/binary_sensor/vibration_abcdef12/config"
    assert pub_calls[0][1]["retain"] is True
    disc_data = json.loads(disc_payload)
    assert disc_data["object_id"] == "vibration_abcdef12"

    # Call 2: retained ON state
    state_topic, state_payload = pub_calls[1][0][0], pub_calls[1][0][1]
    assert state_topic == "vibration/mesh/abcdef12/alarm"
    assert state_payload == "ON"
    assert pub_calls[1][1]["retain"] is True

    # Verify state persistence
    state_file = Path(bridge.STATE_FILE)
    assert state_file.exists()
    state_data = json.loads(state_file.read_text())
    assert state_data["known_alarms"]["abcdef12"] == "ON"
    assert "abcdef12" in state_data["last_alarm_time"]


def test_first_packet_normal_publishes_retained_off(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)

    packet = {
        "fromId": "!node1234",
        "decoded": {"text": "NORMAL heartbeat"},
    }

    bridge.on_receive(packet, None)

    assert "node1234" in bridge.discovered_sensors
    assert bridge.known_alarms.get("node1234") == "OFF"

    pub_calls = bridge.mqtt_client.publish.call_args_list
    assert len(pub_calls) == 2

    state_topic, state_payload = pub_calls[1][0][0], pub_calls[1][0][1]
    assert state_topic == "vibration/mesh/node1234/alarm"
    assert state_payload == "OFF"
    assert pub_calls[1][1]["retain"] is True


def test_subsequent_packets_on_and_off(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)

    # First packet: position packet (normal)
    pos_packet = {
        "fromId": "!node5555",
        "decoded": {"position": {"latitude": 22.5, "longitude": 113.9, "altitude": 10}},
    }
    bridge.on_receive(pos_packet, None)
    assert bridge.known_alarms.get("node5555") == "OFF"

    bridge.mqtt_client.publish.reset_mock()

    # Second packet: SOS / ALARM text
    alarm_packet = {
        "fromId": "!node5555",
        "decoded": {"text": "SOS emergency trigger"},
    }
    bridge.on_receive(alarm_packet, None)
    assert bridge.known_alarms.get("node5555") == "ON"

    # Should publish retained ON
    bridge.mqtt_client.publish.assert_called_with(
        "vibration/mesh/node5555/alarm", "ON", qos=1, retain=True
    )

    bridge.mqtt_client.publish.reset_mock()

    # Third packet: CLEAR text
    clear_packet = {
        "fromId": "!node5555",
        "decoded": {"text": "CLEAR"},
    }
    bridge.on_receive(clear_packet, None)
    assert bridge.known_alarms.get("node5555") == "OFF"
    assert "node5555" not in bridge.last_alarm_time

    # Should publish retained OFF
    bridge.mqtt_client.publish.assert_called_with(
        "vibration/mesh/node5555/alarm", "OFF", qos=1, retain=True
    )


def test_load_state_restores_active_and_resets_expired_alarms(tmp_path: Path):
    state_file = tmp_path / "vibration_bridge_state.json"
    now = time.time()

    persisted = {
        "known_nodes": {
            "active_node": {"lat": 22.0, "lon": 113.0, "alt": 0},
            "expired_node": {"lat": 23.0, "lon": 114.0, "alt": 0},
        },
        "known_alarms": {
            "active_node": "ON",
            "expired_node": "ON",
        },
        "last_alarm_time": {
            "active_node": now - 30,    # 30s ago (<120s, active)
            "expired_node": now - 200,  # 200s ago (>=120s, expired)
        },
    }
    state_file.write_text(json.dumps(persisted))

    bridge = load_bridge_module(tmp_path)
    bridge.load_state()

    # active_node remains ON and last_alarm_time is kept
    assert bridge.known_alarms.get("active_node") == "ON"
    assert "active_node" in bridge.last_alarm_time

    # expired_node marked as OFF and last_alarm_time is cleared
    assert bridge.known_alarms.get("expired_node") == "OFF"
    assert "expired_node" not in bridge.last_alarm_time

    # Replay all states on connect
    bridge.mqtt_client.publish.reset_mock()
    bridge.replay_all_states(bridge.mqtt_client)

    calls = bridge.mqtt_client.publish.call_args_list
    topics_and_payloads = [(c[0][0], c[0][1], c[1].get("retain")) for c in calls]

    # active_node replayed with retained ON
    assert ("vibration/mesh/active_node/alarm", "ON", True) in topics_and_payloads
    # expired_node replayed with retained OFF to clear any stale broker retention
    assert ("vibration/mesh/expired_node/alarm", "OFF", True) in topics_and_payloads


def test_homeassistant_status_online_replays_discovery_and_states(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)

    # Setup node with active alarm and GPS
    bridge.known_nodes["node8888"] = {"lat": 31.2, "lon": 121.5, "alt": 5}
    bridge.known_alarms["node8888"] = "ON"
    bridge.last_alarm_time["node8888"] = time.time() - 10
    bridge.discovered_sensors.add("node8888")
    bridge.discovered_trackers.add("node8888")

    # Simulate HA restart sending homeassistant/status online
    msg = MagicMock()
    msg.topic = "homeassistant/status"
    msg.payload = b"online"

    bridge.mqtt_client.publish.reset_mock()
    bridge.on_mqtt_message(bridge.mqtt_client, None, msg)

    # Discovered sets re-populated
    assert "node8888" in bridge.discovered_sensors
    assert "node8888" in bridge.discovered_trackers

    calls = bridge.mqtt_client.publish.call_args_list
    topics_and_payloads = [(c[0][0], c[0][1], c[1].get("retain")) for c in calls]

    by_topic = {c[0][0]: (c[0][1], c[1].get("retain")) for c in calls}
    assert by_topic["homeassistant/binary_sensor/vibration_node8888/config"][1] is True
    sensor_disc = json.loads(by_topic["homeassistant/binary_sensor/vibration_node8888/config"][0])
    assert sensor_disc["object_id"] == "vibration_node8888"
    assert by_topic["vibration/mesh/node8888/alarm"] == ("ON", True)
    assert by_topic["homeassistant/device_tracker/vibration_node8888/config"][1] is True
    tracker_disc = json.loads(by_topic["homeassistant/device_tracker/vibration_node8888/config"][0])
    assert tracker_disc["object_id"] == "vibration_node8888"
    pos_data = json.loads(by_topic["vibration/mesh/node8888/position"][0])
    assert pos_data["latitude"] == 31.2
    assert pos_data["longitude"] == 121.5
    assert by_topic["vibration/mesh/node8888/position"][1] is True


def test_clear_message_before_discovery_publishes_off(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)

    # Node has active alarm from prior state, but has not completed discovery yet
    bridge.known_nodes["node9999"] = {}
    bridge.known_alarms["node9999"] = "ON"
    bridge.last_alarm_time["node9999"] = time.time() - 10
    assert "node9999" not in bridge.discovered_sensors

    clear_packet = {
        "fromId": "!node9999",
        "decoded": {"text": "CLEAR bearing vibration normal"},
    }
    bridge.mqtt_client.publish.reset_mock()
    bridge.on_receive(clear_packet, None)

    # Sensor discovery must be completed
    assert "node9999" in bridge.discovered_sensors
    # Alarm state must have transitioned to OFF, and last_alarm_time removed
    assert bridge.known_alarms.get("node9999") == "OFF"
    assert "node9999" not in bridge.last_alarm_time

    # Verify MQTT calls: discovery config followed by retained OFF (not ON!)
    calls = bridge.mqtt_client.publish.call_args_list
    assert len(calls) == 2

    disc_topic, disc_payload = calls[0][0][0], calls[0][0][1]
    assert disc_topic == "homeassistant/binary_sensor/vibration_node9999/config"
    assert calls[0][1]["retain"] is True

    state_topic, state_payload = calls[1][0][0], calls[1][0][1]
    assert state_topic == "vibration/mesh/node9999/alarm"
    assert state_payload == "OFF"
    assert calls[1][1]["retain"] is True

    # Verify saved state file persists OFF
    state_file = Path(bridge.STATE_FILE)
    assert state_file.exists()
    state_data = json.loads(state_file.read_text())
    assert state_data["known_alarms"]["node9999"] == "OFF"
    assert "node9999" not in state_data["last_alarm_time"]


def test_concurrent_save_state_does_not_corrupt_state_file(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)
    errors = []

    def worker(worker_id: int):
        try:
            for i in range(25):
                node_id = f"worker_{worker_id}_{i}"
                with bridge.state_lock:
                    bridge.known_nodes[node_id] = {"lat": float(worker_id), "lon": float(i), "alt": 0}
                    bridge.known_alarms[node_id] = "ON" if i % 2 == 0 else "OFF"
                    if i % 2 == 0:
                        bridge.last_alarm_time[node_id] = time.time()
                bridge.save_state()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(wid,)) for wid in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent save_state threw exceptions: {errors}"
    state_file = Path(bridge.STATE_FILE)
    assert state_file.exists()

    # The final state file must be valid JSON
    state_data = json.loads(state_file.read_text())
    assert isinstance(state_data.get("known_nodes"), dict)
    assert isinstance(state_data.get("known_alarms"), dict)
    assert isinstance(state_data.get("last_alarm_time"), dict)
    assert len(state_data["known_nodes"]) > 0

    # Ensure no leftover temporary files in directory
    state_dir = state_file.parent
    tmp_files = list(state_dir.glob("state_*.tmp"))
    assert tmp_files == []


def test_classify_message_intent(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)

    # Recovery/clear tokens: is_clear=True, is_alarm=False
    clear_messages = [
        "ALARM CLEAR",
        "ALARM_CLEAR",
        "ALARM-CLEAR",
        "CLEAR",
        "NORMAL",
        "HEARTBEAT",
        "RESOLVED",
        "OK",
        "CLEARED",
        "ALARM CLEAR motor recovered",
        "Machine status is NORMAL",
        "HEARTBEAT ping 42",
    ]
    for msg in clear_messages:
        is_alarm, is_clear = bridge.classify_message_intent(msg)
        assert is_clear is True, f"Expected is_clear=True for {msg!r}, got ({is_alarm}, {is_clear})"
        assert is_alarm is False, f"Expected is_alarm=False for {msg!r}, got ({is_alarm}, {is_clear})"

    # Alarm tokens: is_alarm=True, is_clear=False
    # Specifically, verify "ABNORMAL" is classified as alarm and NOT clear (avoiding "NORMAL" substring match)
    alarm_messages = [
        "ABNORMAL",
        "VIBRATION_ALERT",
        "SOS",
        "ALARM",
        "ALERT",
        "VIBRATION",
        "ABNORMAL vibration detected on pump",
        "VIBRATION_ALERT threshold exceeded",
        "SOS emergency stop triggered",
    ]
    for msg in alarm_messages:
        is_alarm, is_clear = bridge.classify_message_intent(msg)
        assert is_alarm is True, f"Expected is_alarm=True for {msg!r}, got ({is_alarm}, {is_clear})"
        assert is_clear is False, f"Expected is_clear=False for {msg!r}, got ({is_alarm}, {is_clear})"

    # Precedence: recovery message containing both alarm and clear tokens clears the alarm
    is_alarm, is_clear = bridge.classify_message_intent("ALARM CLEAR")
    assert (is_alarm, is_clear) == (False, True)

    is_alarm, is_clear = bridge.classify_message_intent("VIBRATION_ALERT RESOLVED")
    assert (is_alarm, is_clear) == (False, True)

    # Empty / neutral messages
    assert bridge.classify_message_intent("") == (False, False)
    assert bridge.classify_message_intent(None) == (False, False)
    assert bridge.classify_message_intent("Ambient temperature 25C humidity 50%") == (False, False)


def test_incoming_alarm_at_timeout_boundary_not_stomped(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)
    node_id = "race_node"
    bridge.known_nodes[node_id] = {}
    bridge.discovered_sensors.add(node_id)

    # Setup expired alarm timestamp (130s ago)
    past_time = time.time() - 130
    with bridge.state_lock:
        bridge.known_alarms[node_id] = "ON"
        bridge.last_alarm_time[node_id] = past_time

    # Step 1: Simulate the atomic timeout sweep under lock when alarm is expired
    with bridge.state_lock:
        now = time.time()
        for nid, alarm_time in list(bridge.last_alarm_time.items()):
            if now - alarm_time >= 120:
                bridge.known_alarms[nid] = "OFF"
                bridge.last_alarm_time.pop(nid, None)
                if bridge.mqtt_connected:
                    bridge.mqtt_client.publish(f"vibration/mesh/{nid}/alarm", "OFF", qos=1, retain=True)

    assert bridge.known_alarms[node_id] == "OFF"
    assert bridge.mqtt_client.publish.call_count == 1
    assert bridge.mqtt_client.publish.call_args_list[-1][0][1] == "OFF"

    # Step 2: New alarm packet arrives
    bridge.mqtt_client.publish.reset_mock()
    packet = {
        "fromId": f"!{node_id}",
        "decoded": {"text": "VIBRATION_ALERT high amplitude spike"},
    }
    bridge.on_receive(packet, None)

    # The incoming packet must have set the alarm to ON and refreshed the timer
    assert bridge.known_alarms[node_id] == "ON"
    assert node_id in bridge.last_alarm_time

    # Step 3: Now the timeout sweep runs again, but alarm is fresh (<120s)
    with bridge.state_lock:
        now = time.time()
        for nid, alarm_time in list(bridge.last_alarm_time.items()):
            if now - alarm_time >= 120:
                bridge.known_alarms[nid] = "OFF"
                bridge.last_alarm_time.pop(nid, None)
                if bridge.mqtt_connected:
                    bridge.mqtt_client.publish(f"vibration/mesh/{nid}/alarm", "OFF", qos=1, retain=True)

    # Alarm must NOT have been stomped to OFF, and last_alarm_time must be preserved
    assert bridge.known_alarms[node_id] == "ON"
    assert node_id in bridge.last_alarm_time

    # Check MQTT publish calls: only the ON state from the incoming packet was published in step 2
    alarm_publishes = [
        c for c in bridge.mqtt_client.publish.call_args_list
        if c[0][0] == f"vibration/mesh/{node_id}/alarm"
    ]
    assert len(alarm_publishes) == 1
    assert alarm_publishes[0][0][1] == "ON"


def test_concurrent_alarm_refresh_and_timeout_sweep(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)
    stop_event = threading.Event()
    errors = []

    # Node starts with an active alarm
    node_id = "concurrent_node"
    bridge.known_nodes[node_id] = {}
    bridge.discovered_sensors.add(node_id)
    with bridge.state_lock:
        bridge.known_alarms[node_id] = "ON"
        bridge.last_alarm_time[node_id] = time.time()

    def timeout_worker():
        try:
            while not stop_event.is_set():
                with bridge.state_lock:
                    now = time.time()
                    nodes_to_clear = []
                    for nid, alarm_time in list(bridge.last_alarm_time.items()):
                        if now - alarm_time >= 120:
                            bridge.known_alarms[nid] = "OFF"
                            bridge.last_alarm_time.pop(nid, None)
                            nodes_to_clear.append(nid)
                            if bridge.mqtt_connected:
                                bridge.mqtt_client.publish(f"vibration/mesh/{nid}/alarm", "OFF", qos=1, retain=True)
                    if nodes_to_clear:
                        bridge._save_state_locked()
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    def receive_worker():
        try:
            for i in range(50):
                packet = {
                    "fromId": f"!{node_id}",
                    "decoded": {"text": f"VIBRATION_ALERT count {i}"},
                }
                bridge.on_receive(packet, None)
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    t_timeout = threading.Thread(target=timeout_worker)
    t_receive = threading.Thread(target=receive_worker)

    t_timeout.start()
    t_receive.start()

    t_receive.join()
    stop_event.set()
    t_timeout.join()

    assert not errors, f"Errors in concurrent workers: {errors}"
    assert bridge.known_alarms[node_id] == "ON"
    assert node_id in bridge.last_alarm_time


def test_no_race_between_replay_all_states_and_on_receive(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)
    node_id = "race_replay_node"

    # Pre-populate known node
    with bridge.state_lock:
        bridge.known_nodes[node_id] = {"lat": 22.5, "lon": 113.9, "alt": 10}
        bridge.discovered_sensors.add(node_id)
        bridge.discovered_trackers.add(node_id)

    packet = {
        "fromId": f"!{node_id}",
        "decoded": {"text": "VIBRATION_ALERT motor bearing spike"},
    }

    # Run multiple trials testing both initially-OFF and initially-expired-ON states
    for initial_state in ("OFF", "EXPIRED_ON"):
        for trial in range(30):
            with bridge.state_lock:
                if initial_state == "OFF":
                    bridge.known_alarms[node_id] = "OFF"
                    bridge.last_alarm_time.pop(node_id, None)
                else:
                    bridge.known_alarms[node_id] = "ON"
                    bridge.last_alarm_time[node_id] = time.time() - 200

            published_payloads = []
            publish_lock = threading.Lock()

            def mock_publish(topic, payload, *args, **kwargs):
                if topic == f"vibration/mesh/{node_id}/alarm":
                    with publish_lock:
                        published_payloads.append(str(payload))
                res = MagicMock()
                res.rc = 0
                return res

            bridge.mqtt_client.publish = mock_publish

            barrier = threading.Barrier(2)

            def run_replay():
                barrier.wait()
                bridge.replay_all_states(bridge.mqtt_client)

            def run_receive():
                barrier.wait()
                bridge.on_receive(packet, None)

            t_replay = threading.Thread(target=run_replay)
            t_receive = threading.Thread(target=run_receive)

            t_replay.start()
            t_receive.start()

            t_replay.join()
            t_receive.join()

            with bridge.state_lock:
                final_alarm = bridge.known_alarms.get(node_id)

            assert final_alarm == "ON", (
                f"[{initial_state} trial {trial}] expected known_alarms to be ON, got {final_alarm}"
            )
            assert len(published_payloads) >= 1, (
                f"[{initial_state} trial {trial}] expected at least one alarm publish call, got none"
            )
            assert published_payloads[-1] == "ON", (
                f"[{initial_state} trial {trial}] final published payload was {published_payloads[-1]!r} instead of 'ON'! "
                f"Full sequence: {published_payloads}"
            )


def test_discovery_payloads_include_object_id_for_entity_id_generation(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)
    client = MagicMock()
    mock_res = MagicMock()
    mock_res.rc = 0
    client.publish.return_value = mock_res

    node_id = "test_node_42"

    # 1. Device Tracker Discovery Payload
    assert bridge.publish_tracker_discovery(client, node_id) is True
    assert node_id in bridge.discovered_trackers
    tracker_call = client.publish.call_args_list[0]
    tracker_topic, tracker_payload = tracker_call[0][0], tracker_call[0][1]
    assert tracker_topic == f"homeassistant/device_tracker/vibration_{node_id}/config"
    assert tracker_call[1]["retain"] is True
    assert tracker_call[1]["qos"] == 1
    tracker_data = json.loads(tracker_payload)
    assert tracker_data["object_id"] == f"vibration_{node_id}"
    assert tracker_data["unique_id"] == f"vibration_{node_id}_tracker"
    assert tracker_data["name"] == f"T1000-E Tracker {node_id}"
    assert tracker_data["json_attributes_topic"] == f"vibration/mesh/{node_id}/position"
    assert tracker_data["source_type"] == "gps"

    # 2. Binary Sensor Discovery Payload
    assert bridge.publish_sensor_discovery(client, node_id) is True
    assert node_id in bridge.discovered_sensors
    sensor_call = client.publish.call_args_list[1]
    sensor_topic, sensor_payload = sensor_call[0][0], sensor_call[0][1]
    assert sensor_topic == f"homeassistant/binary_sensor/vibration_{node_id}/config"
    assert sensor_call[1]["retain"] is True
    assert sensor_call[1]["qos"] == 1
    sensor_data = json.loads(sensor_payload)
    assert sensor_data["object_id"] == f"vibration_{node_id}"
    assert sensor_data["unique_id"] == f"vibration_{node_id}_alarm"
    assert sensor_data["name"] == f"T1000-E Vibration Alarm {node_id}"
    assert sensor_data["state_topic"] == f"vibration/mesh/{node_id}/alarm"
    assert sensor_data["device_class"] == "vibration"


def test_position_packet_publishes_tracker_discovery_with_object_id(tmp_path: Path):
    bridge = load_bridge_module(tmp_path)

    packet = {
        "fromId": "!posnode1",
        "decoded": {
            "position": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "altitude": 10,
            }
        },
    }

    bridge.on_receive(packet, None)

    assert "posnode1" in bridge.discovered_trackers
    pub_calls = bridge.mqtt_client.publish.call_args_list
    topics = [c[0][0] for c in pub_calls]
    assert "homeassistant/device_tracker/vibration_posnode1/config" in topics

    call = next(c for c in pub_calls if c[0][0] == "homeassistant/device_tracker/vibration_posnode1/config")
    payload = json.loads(call[0][1])
    assert payload["object_id"] == "vibration_posnode1"
    assert payload["unique_id"] == "vibration_posnode1_tracker"




