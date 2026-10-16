## What This Capability Does

Gives any MCP-compatible voice assistant or LLM a live, spoken-language connection to your SenseCAP PaaS device fleet. Ask "how are my devices doing" and get an anomaly-first fleet report, or ask about one device by name for its full current reading — no app, no dashboard, no query language. Device registration and key lookup are also available for setup workflows.

## What You Get After Deploying

- A farm overview tool: ask "how are my devices doing" and get one spoken answer — how many devices, who's offline, whose battery is low, presented anomaly-first so a healthy fleet doesn't waste your time.
- A device reading tool: ask about one device by name and get every channel's current reading spoken in plain language (temperature, humidity, soil moisture, wind, rainfall, and more), not raw numbers.
- A device registry tool: register a new SenseCAP device and get back its EUI, by name.
- A device key lookup tool: get a device's `device_key`/token by name or EUI — used when provisioning firmware.
- A live telemetry tool: ask for the latest reading from any device by name or EUI — returns the newest data point for every channel it reports, not just one value.
- A history tool: pull historical telemetry for a time range, plus a chart-ready aggregation tool for plotting trends.
- A code-template tool: list and read Arduino/PlatformIO templates for reporting sensor data and device status to SenseCAP.
- The farm overview and device reading tools speak a complete, ready-to-hear sentence built from real numbers. The telemetry/history/chart/key tools return a short summary plus the full structured data instead — built for scripting and follow-up processing, not meant to be read aloud verbatim.

## What You Can Connect It To

- **XiaoZhi (小智) voice assistants** — the primary target: point it at your XiaoZhi MCP access point and ask about your devices out loud.
- **Any other MCP-compatible host** — Claude Desktop, Cursor, or a custom LLM agent that speaks the Model Context Protocol.

## Interface for Your Program

| Interface | What it does | How to connect | Data format |
|---|---|---|---|
| MCP over WebSocket | Outbound connection to an MCP access point, exposing 9 tools | Set `MCP_ENDPOINT` to your access point URL | JSON-RPC (MCP) |

> This container only dials **out** — it never listens on a port, so there's nothing to expose or firewall.

## Usage Notes

- You need a SenseCAP PaaS account with an Access ID/Key pair (sensecap.seeed.cc → API keys) and devices already reporting data to it.
- You need a XiaoZhi MCP access point URL (from your XiaoZhi console) if you're connecting it to a XiaoZhi voice assistant.
- Credentials are entered at deploy time only and are never baked into the Docker image — update them any time by redeploying this preset with new values.
