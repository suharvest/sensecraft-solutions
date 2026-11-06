#!/usr/bin/env python3
"""ESPHome YAML configuration generator for XIAO RS485 Modbus nodes.

Supports Seeed Studio XIAO ESP32-C3, S3, and C6 boards with pre-defined pinouts,
Modbus-RTU controller configurations, and sensor presets (XY-MD02, 3-color tower light, custom).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

CHIP_PINOUTS: dict[str, dict[str, Any]] = {
    "c3": {
        "board": "esp32-c3-devkitm-1",
        "framework": "arduino",
        "tx": 6,
        "rx": 7,
        "flow_control": 4,
        "tx_pin": "GPIO6",
        "rx_pin": "GPIO7",
        "flow_control_pin": "GPIO4",
    },
    "s3": {
        "board": "seeed_xiao_esp32s3",
        "framework": "arduino",
        "tx": 5,
        "rx": 6,
        "flow_control": 3,
        "tx_pin": "GPIO5",
        "rx_pin": "GPIO6",
        "flow_control_pin": "GPIO3",
    },
    "c6": {
        "board": "esp32-c6-devkitc-1",
        "framework": "esp-idf",
        "tx": 22,
        "rx": 23,
        "flow_control": 2,
        "tx_pin": "GPIO22",
        "rx_pin": "GPIO23",
        "flow_control_pin": "GPIO2",
    },
}

SUPPORTED_SENSORS = ("xy_md02", "light", "custom")


def generate_config(
    chip: str = "c3",
    sensor: str = "xy_md02",
    name: str = "xiao-rs485-node",
    friendly_name: str | None = None,
    wifi_ssid: str = "HomeNetwork",
    wifi_password: str = "SecretPassword",
    modbus_address: int = 1,
    baud_rate: int = 9600,
    tx_pin: int | str | None = None,
    rx_pin: int | str | None = None,
    flow_control_pin: int | str | None = None,
    framework: str | None = None,
) -> dict[str, Any]:
    """Generate an ESPHome configuration dictionary based on chip, sensor, and network settings."""
    chip_lower = chip.lower()
    if chip_lower not in CHIP_PINOUTS:
        raise ValueError(
            f"Unsupported chip: {chip}. Supported chips are {list(CHIP_PINOUTS.keys())}"
        )

    sensor_lower = sensor.lower()
    if sensor_lower not in SUPPORTED_SENSORS:
        raise ValueError(
            f"Unsupported sensor preset: {sensor}. Supported presets are {SUPPORTED_SENSORS}"
        )

    hw_info = CHIP_PINOUTS[chip_lower]
    board = hw_info["board"]
    selected_framework = framework or hw_info["framework"]
    final_tx = tx_pin if tx_pin is not None else hw_info["tx"]
    final_rx = rx_pin if rx_pin is not None else hw_info["rx"]
    final_fc = flow_control_pin if flow_control_pin is not None else hw_info["flow_control"]

    safe_name = name.strip().lower().replace("_", "-")
    display_name = friendly_name or name.replace("-", " ").title()

    config: dict[str, Any] = {
        "esphome": {
            "name": safe_name,
            "friendly_name": display_name,
        },
        "esp32": {
            "board": board,
            "framework": {
                "type": selected_framework,
            },
        },
        "logger": {
            "level": "DEBUG",
        },
        "api": {},
        "ota": [
            {"platform": "esphome"}
        ],
        "wifi": {
            "ssid": wifi_ssid,
            "password": wifi_password,
            "ap": {
                "ssid": f"{safe_name}-fallback",
                "password": "",
            },
        },
        "captive_portal": {},
        "uart": [
            {
                "id": "uart_bus",
                "tx_pin": final_tx,
                "rx_pin": final_rx,
                "baud_rate": baud_rate,
                "stop_bits": 1,
            }
        ],
        "modbus": {
            "id": "modbus_bus",
            "uart_id": "uart_bus",
            "flow_control_pin": final_fc,
        },
        "modbus_controller": [
            {
                "id": "modbus_device",
                "address": modbus_address,
                "modbus_id": "modbus_bus",
                "setup_priority": -10,
            }
        ],
    }

    if sensor_lower == "xy_md02":
        config["sensor"] = [
            {
                "platform": "modbus_controller",
                "modbus_controller_id": "modbus_device",
                "name": f"{display_name} Temperature",
                "id": f"{safe_name.replace('-', '_')}_temperature",
                "register_type": "read",
                "address": 1,
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
                "value_type": "S_WORD",
                "accuracy_decimals": 1,
                "filters": [
                    {"multiply": 0.1}
                ],
            },
            {
                "platform": "modbus_controller",
                "modbus_controller_id": "modbus_device",
                "name": f"{display_name} Humidity",
                "id": f"{safe_name.replace('-', '_')}_humidity",
                "register_type": "read",
                "address": 2,
                "unit_of_measurement": "%",
                "device_class": "humidity",
                "state_class": "measurement",
                "value_type": "U_WORD",
                "accuracy_decimals": 1,
                "filters": [
                    {"multiply": 0.1}
                ],
            },
        ]
    elif sensor_lower == "light":
        config["switch"] = [
            {
                "platform": "modbus_controller",
                "modbus_controller_id": "modbus_device",
                "name": f"{display_name} Red Light",
                "id": f"{safe_name.replace('-', '_')}_red_light",
                "register_type": "coil",
                "address": 0,
            },
            {
                "platform": "modbus_controller",
                "modbus_controller_id": "modbus_device",
                "name": f"{display_name} Yellow Light",
                "id": f"{safe_name.replace('-', '_')}_yellow_light",
                "register_type": "coil",
                "address": 1,
            },
            {
                "platform": "modbus_controller",
                "modbus_controller_id": "modbus_device",
                "name": f"{display_name} Green Light",
                "id": f"{safe_name.replace('-', '_')}_green_light",
                "register_type": "coil",
                "address": 2,
            },
        ]
    elif sensor_lower == "custom":
        config["sensor"] = [
            {
                "platform": "modbus_controller",
                "modbus_controller_id": "modbus_device",
                "name": f"{display_name} Modbus Value",
                "id": f"{safe_name.replace('-', '_')}_modbus_value",
                "register_type": "holding",
                "address": 0,
                "value_type": "U_WORD",
            }
        ]

    return config


def generate_config_yaml(
    chip: str = "c3",
    sensor: str = "xy_md02",
    name: str = "xiao-rs485-node",
    friendly_name: str | None = None,
    wifi_ssid: str = "HomeNetwork",
    wifi_password: str = "SecretPassword",
    modbus_address: int = 1,
    baud_rate: int = 9600,
    tx_pin: int | str | None = None,
    rx_pin: int | str | None = None,
    flow_control_pin: int | str | None = None,
    framework: str | None = None,
) -> str:
    """Generate ESPHome configuration formatted as a clean YAML string."""
    data = generate_config(
        chip=chip,
        sensor=sensor,
        name=name,
        friendly_name=friendly_name,
        wifi_ssid=wifi_ssid,
        wifi_password=wifi_password,
        modbus_address=modbus_address,
        baud_rate=baud_rate,
        tx_pin=tx_pin,
        rx_pin=rx_pin,
        flow_control_pin=flow_control_pin,
        framework=framework,
    )
    return yaml.dump(data, sort_keys=False, allow_unicode=True)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate standard ESPHome YAML configuration for Seeed Studio XIAO RS485 nodes."
    )
    parser.add_argument(
        "--chip",
        choices=["c3", "s3", "c6"],
        default="c3",
        help="Target chip architecture (c3, s3, or c6). Default: c3",
    )
    parser.add_argument(
        "--sensor",
        choices=["xy_md02", "light", "custom"],
        default="xy_md02",
        help="Device sensor / actuator preset. Default: xy_md02",
    )
    parser.add_argument(
        "--name",
        default="xiao-rs485-node",
        help="Device hostname / node identifier. Default: xiao-rs485-node",
    )
    parser.add_argument(
        "--friendly-name",
        default=None,
        help="Human-friendly name shown in Home Assistant UI.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Path to write the generated YAML file. Defaults to stdout if omitted.",
    )
    parser.add_argument(
        "--wifi-ssid",
        default="HomeNetwork",
        help="Wi-Fi network SSID. Default: HomeNetwork",
    )
    parser.add_argument(
        "--wifi-password",
        default="SecretPassword",
        help="Wi-Fi network password. Default: SecretPassword",
    )
    parser.add_argument(
        "--modbus-address",
        type=int,
        default=1,
        help="Modbus slave address (1-247). Default: 1",
    )
    parser.add_argument(
        "--baud-rate",
        type=int,
        default=9600,
        help="Modbus UART baud rate. Default: 9600",
    )
    parser.add_argument(
        "--tx-pin",
        default=None,
        help="Override UART TX pin.",
    )
    parser.add_argument(
        "--rx-pin",
        default=None,
        help="Override UART RX pin.",
    )
    parser.add_argument(
        "--flow-control-pin",
        default=None,
        help="Override RS485 DE/RE flow control pin.",
    )
    parser.add_argument(
        "--framework",
        choices=["arduino", "esp-idf"],
        default=None,
        help="Override ESP32 compilation framework (arduino or esp-idf).",
    )
    return parser.parse_args(args)


def main() -> None:
    args = parse_args()
    yaml_content = generate_config_yaml(
        chip=args.chip,
        sensor=args.sensor,
        name=args.name,
        friendly_name=args.friendly_name,
        wifi_ssid=args.wifi_ssid,
        wifi_password=args.wifi_password,
        modbus_address=args.modbus_address,
        baud_rate=args.baud_rate,
        tx_pin=args.tx_pin,
        rx_pin=args.rx_pin,
        flow_control_pin=args.flow_control_pin,
        framework=args.framework,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(yaml_content, encoding="utf-8")
        print(f"Generated ESPHome configuration saved to: {args.output}")
    else:
        sys.stdout.write(yaml_content)


if __name__ == "__main__":
    main()
