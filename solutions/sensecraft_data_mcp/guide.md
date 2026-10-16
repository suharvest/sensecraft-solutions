## Preset: SenseCAP PaaS MCP Bridge {#default}

Deploy a small always-on bridge that connects your SenseCAP PaaS account to a XiaoZhi voice assistant (or any other MCP-compatible host) via the Model Context Protocol.

| Device | Purpose |
|--------|---------|
| Any Docker host (e.g. reComputer R1100) | Runs the MCP bridge container |

**What you'll get:**
- 9 MCP tools exposed to your voice assistant: get a spoken fleet overview, get a full-channel spoken reading for one device, register a device, look up a device key, read the latest telemetry, list historical telemetry, aggregate chart points, and browse/read Arduino code templates
- An outbound WebSocket connection to your XiaoZhi MCP access point — no inbound ports, no public exposure
- Credentials passed in at deploy time only, never baked into the image — update them any time by redeploying

**Requirements:** Docker installed · A SenseCAP PaaS Access ID/Key (sensecap.seeed.cc → API keys) · A XiaoZhi MCP access point URL from your XiaoZhi console

## Step 1: Deploy MCP Bridge {#deploy type=docker_deploy required=true config=devices/mcp_bridge.yaml}

Deploy the bridge container with your SenseCAP PaaS credentials and XiaoZhi MCP endpoint.

### Deployment Complete

The bridge is now running and connected to your XiaoZhi MCP endpoint.

#### Try It

1. Open your XiaoZhi app or device and start a conversation
2. Ask something like "我的设备现在怎么样" (or in English, "how are my devices doing")
3. XiaoZhi should call the bridge's `get_farm_overview` tool and read back how many devices you have and whether any need attention
4. Then try asking about one device by name, e.g. "大棚气象站现在怎么样" — XiaoZhi should call `get_device_reading` and read back that device's current readings across every channel

#### Next Steps

- [Project README](https://github.com/Love4yzp/sensecraft-data-mcp) — full tool list and manual/stdio usage
- To rotate credentials, just redeploy this step with the new Access ID/Key or endpoint — no rebuild needed

### Target {#local type=local config=devices/mcp_bridge.yaml default=true}

Deploy on the machine you're currently using.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not found | Install Docker Desktop and ensure it is running |
| Container keeps restarting | Check logs: `docker logs sensecraft-data-mcp` — usually a wrong Access ID/Key or endpoint URL |
| XiaoZhi never calls the tools | Confirm the MCP endpoint URL (including the `?token=` part) was copied exactly from the XiaoZhi console |
| Reported times are off by several hours | Set the "Device Timezone" field to your devices' IANA timezone (e.g. `Asia/Shanghai`) and redeploy. Left blank, the China site defaults to Beijing time and other sites default to UTC — it never guesses. |

### Target {#remote type=remote device_name="reComputer R1100" config=devices/mcp_bridge.yaml}

Deploy to a reComputer (or any Docker host) over SSH.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify the device IP, username, and password, and that SSH is enabled |
| Docker Compose unavailable | Install it: `sudo apt-get install -y docker-compose-plugin` |
| Container keeps restarting | Check logs on the device: `docker logs sensecraft-data-mcp` — usually a wrong Access ID/Key or endpoint URL |
| Reported times are off by several hours | Set the "Device Timezone" field to your devices' IANA timezone (e.g. `Asia/Shanghai`) and redeploy. Left blank, the China site defaults to Beijing time and other sites default to UTC — it never guesses. |
