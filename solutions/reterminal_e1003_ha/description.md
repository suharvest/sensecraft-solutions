# Control Home Assistant Lighting with E1003

This solution is designed for homes or offices already running Home Assistant.
Its goal is to let you control a dimmable light directly from the fixed touch
screen on reTerminal E1003.

> This is a candidate release and cannot be deployed through the App yet.
> USB firmware distribution and device setup are still being integrated,
> and state and brightness synchronization for arbitrary light targets is not yet complete.

## What you can use it for

Once configured, the panel should let you switch the target light on or off and
adjust its brightness. The planned App setup uses precompiled firmware so users
will not need to edit configuration files or compile code.

| Setting | Purpose |
| --- | --- |
| Wi-Fi | Connects the panel to your home or office local network |
| Unique encryption key per device | Secures the connection between Home Assistant and the panel |
| Light entity `light.xxx` | Specifies the light you want to control |

## Where to use it

- On a bedside table: turn bedroom lights on/off or dim them before sleeping.
- By your desk: quickly adjust workspace lighting without opening an app.

## Before you start

- Only works with reTerminal E1003 using the current fixed screen layout.
- Requires an existing Home Assistant setup with at least one dimmable light.
- The setup computer, E1003 panel, and Home Assistant must be on the same reachable local network.
- Connects directly to Home Assistant via the ESPHome native API—no MQTT broker or web server required.
- Updates are USB-only; wireless updates (OTA) are not supported.
- Changing the light target only sets up the control binding; it does not automatically synchronize the panel display's state and brightness (requires a HA Blueprint or adapter).
