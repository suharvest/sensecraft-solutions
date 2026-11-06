"""Unit tests for ESPHome RS485 configuration generator."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# Add tools/rs485-esphome-kit directory to sys.path so generate_config can be imported directly
TOOL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL_DIR))

from generate_config import CHIP_PINOUTS, generate_config, generate_config_yaml


class TestPinoutBindings:
    """Validate pinout bindings, boards, and frameworks for C3, S3, and C6."""

    def test_c3_pinout(self):
        cfg = generate_config(chip="c3")
        assert cfg["esp32"]["board"] == "esp32-c3-devkitm-1"
        assert cfg["esp32"]["framework"]["type"] == "arduino"

        uart = cfg["uart"][0]
        assert uart["tx_pin"] in (6, "GPIO6", "6")
        assert uart["rx_pin"] in (7, "GPIO7", "7")
        assert cfg["modbus"]["flow_control_pin"] in (4, "GPIO4", "4")

    def test_s3_pinout(self):
        cfg = generate_config(chip="s3")
        assert cfg["esp32"]["board"] == "seeed_xiao_esp32s3"
        assert cfg["esp32"]["framework"]["type"] == "arduino"

        uart = cfg["uart"][0]
        assert uart["tx_pin"] in (5, "GPIO5", "5")
        assert uart["rx_pin"] in (6, "GPIO6", "6")
        assert cfg["modbus"]["flow_control_pin"] in (3, "GPIO3", "3")

    def test_c6_pinout(self):
        cfg = generate_config(chip="c6")
        assert cfg["esp32"]["board"] == "esp32-c6-devkitc-1"
        assert cfg["esp32"]["framework"]["type"] == "esp-idf"

        uart = cfg["uart"][0]
        assert uart["tx_pin"] in (22, "GPIO22", "22")
        assert uart["rx_pin"] in (23, "GPIO23", "23")
        assert cfg["modbus"]["flow_control_pin"] in (2, "GPIO2", "2")


class TestSensorPresets:
    """Validate XY-MD02, light, and custom sensor configuration generation."""

    def test_xy_md02_registers_and_filters(self):
        cfg = generate_config(sensor="xy_md02")
        sensors = cfg.get("sensor", [])
        assert len(sensors) == 2

        # Temperature sensor checks
        temp = sensors[0]
        assert temp["platform"] == "modbus_controller"
        assert temp["register_type"] == "read"
        assert temp["address"] in (1, 0x0001)
        assert temp["unit_of_measurement"] == "°C"
        assert temp["device_class"] == "temperature"
        assert temp["state_class"] == "measurement"
        assert temp["value_type"] == "S_WORD"
        assert temp["filters"] == [{"multiply": 0.1}]

        # Humidity sensor checks
        hum = sensors[1]
        assert hum["platform"] == "modbus_controller"
        assert hum["register_type"] == "read"
        assert hum["address"] in (2, 0x0002)
        assert hum["unit_of_measurement"] == "%"
        assert hum["device_class"] == "humidity"
        assert hum["state_class"] == "measurement"
        assert hum["value_type"] == "U_WORD"
        assert hum["filters"] == [{"multiply": 0.1}]

    def test_light_preset(self):
        cfg = generate_config(sensor="light")
        switches = cfg.get("switch", [])
        assert len(switches) == 3

        names = [s["name"] for s in switches]
        assert any("Red" in n for n in names)
        assert any("Yellow" in n for n in names)
        assert any("Green" in n for n in names)

        addresses = [s["address"] for s in switches]
        assert addresses == [0, 1, 2]
        for s in switches:
            assert s["platform"] == "modbus_controller"
            assert s["register_type"] == "coil"

    def test_custom_preset(self):
        cfg = generate_config(sensor="custom")
        sensors = cfg.get("sensor", [])
        assert len(sensors) == 1
        assert sensors[0]["platform"] == "modbus_controller"
        assert sensors[0]["register_type"] == "holding"
        assert sensors[0]["address"] == 0


class TestNetworkAndSystemConfig:
    """Validate WiFi, API, OTA, and captive portal setup."""

    def test_wifi_and_api_settings(self):
        cfg = generate_config(
            name="test-gateway",
            wifi_ssid="OfficeNet",
            wifi_password="SecretPassword99",
        )
        assert cfg["esphome"]["name"] == "test-gateway"
        assert cfg["wifi"]["ssid"] == "OfficeNet"
        assert cfg["wifi"]["password"] == "SecretPassword99"
        assert "ap" in cfg["wifi"]
        assert "api" in cfg
        assert "ota" in cfg
        assert "captive_portal" in cfg

    def test_custom_modbus_and_uart_params(self):
        cfg = generate_config(
            chip="c3",
            baud_rate=19200,
            modbus_address=7,
            tx_pin=10,
            rx_pin=11,
            flow_control_pin=12,
        )
        assert cfg["uart"][0]["baud_rate"] == 19200
        assert cfg["uart"][0]["tx_pin"] == 10
        assert cfg["uart"][0]["rx_pin"] == 11
        assert cfg["modbus"]["flow_control_pin"] == 12
        assert cfg["modbus_controller"][0]["address"] == 7


class TestCliAndYamlOutput:
    """Validate YAML serialization and CLI invocation."""

    def test_yaml_serialization(self):
        yaml_str = generate_config_yaml(chip="s3", sensor="xy_md02", name="xiao-s3")
        parsed = yaml.safe_load(yaml_str)
        assert parsed["esphome"]["name"] == "xiao-s3"
        assert parsed["esp32"]["board"] == "seeed_xiao_esp32s3"

    def test_cli_execution(self, tmp_path: Path):
        output_file = tmp_path / "test_out.yaml"
        script_path = TOOL_DIR / "generate_config.py"

        cmd = [
            sys.executable,
            str(script_path),
            "--chip", "c6",
            "--sensor", "xy_md02",
            "--name", "c6-node",
            "--output", str(output_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        assert output_file.exists()

        content = yaml.safe_load(output_file.read_text(encoding="utf-8"))
        assert content["esphome"]["name"] == "c6-node"
        assert content["esp32"]["board"] == "esp32-c6-devkitc-1"
        assert content["esp32"]["framework"]["type"] == "esp-idf"

    def test_invalid_chip_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported chip"):
            generate_config(chip="esp8266")

    def test_invalid_sensor_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported sensor"):
            generate_config(sensor="unknown_device")
