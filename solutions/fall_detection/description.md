## What it does

A camera watches an indoor area, decides on the device whether someone has fallen, and pushes the event to Home Assistant, a nursing-call system, an NVR or your own service. No video leaves the device; only a JSON message goes over the network.

## What you get

- **Fall event push**: each person is tracked separately, and one fall triggers one event.
- **Home Assistant entities out of the box**: fall sensor, state, event ID and person-present, with no manual YAML.
- **Works with existing cameras**: reComputer presets take standard RTSP cameras.
- **Optional alarm panel**: zones, no-person/no-motion timeouts, operator confirmation and webhook notifications.
- **Live preview**: after deployment, see the skeleton and each person's state to adjust camera placement.

## Where it fits

- **Assisted living and home care**: unattended bathrooms, hallways and bedrooms.
- **Existing cameras**: add fall detection without replacing them.
- **Home Assistant automations**: turn on a light, send a notification or start a call on a fall.

## Measured results

| Metric | Result |
|---|---|
| Fall to alert | **1.61 s** mean |
| Fall recall | **100%** |
| Everyday activity without false alert | **80%** |
| Streams one host carries at 15 FPS | **16** |
| Fall to webhook delivered via the alarm panel | **P50 2.83 s** (confirmation windows shortened to 1 s) |
| Accuracy / mean alert latency across platforms | **74.1%–88.9%** / **1.22–1.75 s** |
| Recall on an independent external set (RealBiomFall) | **52.9%–58.8%** |

Tested on reComputer R2000 (Hailo-8) with the GMDCSA-24 held-out set of 27 clips (12 falls / 15 everyday activities), 15 FPS, indoor close-to-medium range.

## Output Interfaces

| Output | Content |
|---|---|
| MQTT "<device-name>/fall-detection/results" | Per-frame JSON: overall state plus each tracked person's state |
| MQTT "<device-name>/fall-detection/status" | Device online / offline |
| MQTT discovery under "homeassistant/" | Fall sensor, state, event ID, person count |
| RTSP 8554 "/live0" (reCamera) or your IP camera | The scene being analysed |
| HTTP 8080 "/api/alarms" (alarm panel only) | Alarm list; confirm, dismiss, mark handled |
| Webhook POST (alarm panel only) | Alarm id, kind, zone, time and operator, no video |

"<device-name>" is set in the deploy step.

## Deployment Comparison

| Preset | Camera | Streams measured at 15 FPS | Alarm panel |
|---|---|---|---|
| reCamera 2002 | All-in-one | — | Needs a separate host (reComputer R1000 or an existing machine) |
| reCamera Pro | All-in-one | 1 | Needs a separate host (reComputer R1000 or an existing machine) |
| IP camera + reComputer J30 / J40 | Existing RTSP cameras | J30 8 / J40 9 | Same device, port 8080 |
| reComputer RK3576 / RK3588 | Existing RTSP cameras | RK3576 1 / RK3588 5 | Same device, port 8080 |
| reComputer R2000 (Hailo-8) | Existing RTSP cameras | 16 | Same device, port 8080 |

**For one room and the fastest setup**, choose reCamera 2002; **with existing cameras or multiple views**, choose a reComputer preset.

## Alarm panel

- **Site overview**: counts of rooms, cameras and zones with a 24-hour alarm trend; a camera that drops shows "unknown + stream lost".
- **Draw zones on the live picture**, no coordinates to type.
- **Three alarm kinds per zone**: fall, no-person timeout and no-motion timeout, with timeouts set per zone.
- **Operator confirmation**: a 5 s evidence window, then 60 s to confirm or dismiss; with no answer it is treated as real and notified by default.
- **Retried after outages, never duplicated**: in a measured outage, 3 of 3 queued alarms were delivered with no duplicates.
- **Fully local**: notifications carry no video or snapshots; records are kept 90 days.

### Voice check-in (optional)

Off by default. When enabled, an alarm makes the panel ask the room "are you all right? please answer": a call for help, no answer or an unclear answer confirms the alarm immediately; "I'm fine" only flags it for review by default and does not close it. Requires a USB microphone and speaker on the panel host plus an OpenVoiceStream instance. Audio is never written to disk.

## Usage Notes

- **This is not a medical device or a certified emergency-response product**; a person must judge and respond to every alarm.
- **Camera placement decides accuracy**: a side or corner view at 2–3 m with shoulders and hips visible; ceiling-down, long-shot and occluded views perform worse.

  ![Camera placement: a side or corner view at 2–3 m works; straight-down and long-shot or occluded views do not.](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/camera-placement-be3fb598.svg)
- The fall must happen on camera; someone already lying down at startup raises no event.
- The deploy presets configure one camera; stream counts above are separately measured maximum loads, so test with your own cameras before settling on a count.
- MQTT broker: reCamera 2002 runs its own; reComputer presets start one with the detector; reCamera Pro has none, so point it at an external broker or read results on the camera's own page.
- Re-check zones after moving or re-aiming a camera; no error is raised.
- The no-motion timeout fires during sleep unless the zone excludes the bed or the timeout is longer; an occlusion can raise one false "no person" alarm.
- On RK boards, if no-person alarms never fire, confirm the detector still publishes when nobody is in view.
- Telegram and email channels in the panel do not work.
- reCamera runs one vision app at a time; installing takes over from Node-RED and other vision apps.

## Licensing note

The runtime code is Apache-2.0; pose models keep their own terms and require licence acceptance before download. **The reference pose weights are distributed by Ultralytics under AGPL-3.0**; a closed commercial deployment needs a commercial licence from Ultralytics or a compatibly licensed pose model.
