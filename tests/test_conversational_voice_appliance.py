"""Contract checks for the interruptible voice appliance deployment.

These checks deliberately inspect the shipped YAML/Compose contract rather
than starting containers.  They catch the easy-to-miss failure mode where a
new Agent setting exists in one hardware target but not in another.
"""

from pathlib import Path

import yaml


SOLUTION_DIR = Path(__file__).parents[1] / "solutions" / "conversational_voice_ai"
DOCKER_DIR = SOLUTION_DIR / "assets" / "docker"

DEVICE_FILES = (
    "cloud_rk3576.yaml",
    "cloud_rk3588.yaml",
    "cloud_jetson.yaml",
    "local_orin_nx.yaml",
    "local_rk3588_rk1828.yaml",
)

COMPOSE_FILES = (
    "docker-compose.rk3576.yml",
    "docker-compose.rk3588.yml",
    "docker-compose.jetson.yml",
    "docker-compose.orin-nx-local.yml",
)

RUNTIME_ENV = {
    "PIPELINE_MODE",
    "WAKEWORD_BACKEND",
    "WAKEWORD_PHRASE",
    "WAKEWORD_THRESHOLD",
}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _input_map(inputs: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in inputs}


def test_agent_config_keeps_always_on_default_and_ships_kws_assets():
    config = load_yaml(DOCKER_DIR / "agent-config.yaml")

    assert config["pipeline_mode"] == "${PIPELINE_MODE:-always_on}"
    assert config["wake_mic_skip_ms"] == "${WAKEWORD_MIC_SKIP_MS:-120}"
    assert config["wake_phrases"] == ["${WAKEWORD_PHRASE:-你好小智}"]

    tone = config["metadata"]["wake_tone"]
    assert tone == {"hz": 880, "ms": 130, "mic_suppress_tail_ms": 120}

    wake = config["metadata"]["wakeword"]
    assert wake["backend"] == "${WAKEWORD_BACKEND:-sherpa_onnx}"
    assert wake["state_path"] == "/var/lib/ovs-agent/wakeword.json"
    assert wake["model"]["encoder"].endswith(
        "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx"
    )
    assert wake["model"]["decoder"].endswith(
        "decoder-epoch-13-avg-2-chunk-8-left-64.onnx"
    )
    assert wake["model"]["joiner"].endswith(
        "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx"
    )
    assert wake["compiler"]["lexicon"].endswith("/en.phone")


def test_all_agent_composes_expose_runtime_kws_and_persistent_state():
    for filename in COMPOSE_FILES:
        compose = load_yaml(DOCKER_DIR / filename)
        agent = compose["services"]["agent"]
        assert "voiceagent-20260819-4480743-runtimekws" in agent["image"], filename
        environment = agent["environment"]
        assert RUNTIME_ENV <= environment.keys(), filename
        assert environment["PIPELINE_MODE"] == "${PIPELINE_MODE:-always_on}", filename
        assert environment["WAKEWORD_BACKEND"] == "${WAKEWORD_BACKEND:-sherpa_onnx}", filename
        assert environment["WAKEWORD_PHRASE"] == "${WAKEWORD_PHRASE:-你好小智}", filename
        assert environment["WAKEWORD_THRESHOLD"] == "${WAKEWORD_THRESHOLD:-0.25}", filename
        assert any(
            str(volume).split(":", 1)[0] == "agent-state"
            and str(volume).split(":", 1)[1] == "/var/lib/ovs-agent"
            for volume in agent["volumes"]
        ), filename
        assert "agent-state" in compose["volumes"], filename

    # The RK1828 local-LLM target extends RK3588, but its override must keep
    # the runtime fields visible to the deployment engine as well.
    rk1828 = load_yaml(DOCKER_DIR / "docker-compose.rk3588-rk1828.yml")
    assert rk1828["services"]["agent"]["extends"]["file"] == "docker-compose.rk3588.yml"
    assert RUNTIME_ENV <= rk1828["services"]["agent"]["environment"].keys()
    assert "agent-state" in rk1828["volumes"]


def test_device_views_keep_runtime_env_and_user_inputs_in_sync():
    expected_defaults = {
        "PIPELINE_MODE": "always_on",
        "WAKEWORD_PHRASE": "你好小智",
        "WAKEWORD_THRESHOLD": "0.25",
    }

    for filename in DEVICE_FILES:
        device = load_yaml(SOLUTION_DIR / "devices" / filename)
        base_env = device["docker"]["environment"]
        remote = device["remote_overrides"]
        remote_env = remote["environment"]

        assert base_env["WAKEWORD_BACKEND"] == "sherpa_onnx", filename
        assert remote_env["WAKEWORD_BACKEND"] == "sherpa_onnx", filename
        for key in RUNTIME_ENV - {"WAKEWORD_BACKEND"}:
            assert base_env[key] == f"{{{{{key}}}}}", (filename, key)
            assert remote_env[key] == f"{{{{{key}}}}}", (filename, key)

        base_inputs = _input_map(device.get("user_inputs", []))
        remote_inputs = _input_map(remote.get("user_inputs", []))
        assert set(expected_defaults) <= base_inputs.keys(), filename
        assert set(expected_defaults) <= remote_inputs.keys(), filename

        for key, default in expected_defaults.items():
            assert base_inputs[key]["default"] == default, (filename, key)
            assert remote_inputs[key]["default"] == default, (filename, key)

        mode_values = {item["value"] for item in base_inputs["PIPELINE_MODE"]["options"]}
        assert mode_values == {"always_on", "wake_word"}, filename
        threshold_values = {
            str(item["value"])
            for item in base_inputs["WAKEWORD_THRESHOLD"]["options"]
        }
        assert threshold_values == {"0.35", "0.25", "0.15"}, filename
