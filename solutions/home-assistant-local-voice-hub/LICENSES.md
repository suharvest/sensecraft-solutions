# LICENSES.md — home_assistant_whole_home

Maintainer notes on licence status. Not shown on the customer pages.

## Voice runtime (reComputer J40)

| Component | Source | Status |
|---|---|---|
| Voice runtime image `nrd6-ovs-jetson:20261008` (Qwen3-ASR + Matcha TTS, profile `jetson-edgellm-v091-matcha`) | sensecraft-missionpack.seeed.cn registry | Image published 2026-10-08. Models are downloaded on first start into the `jetson-models` volume. No licence-cleared distributable voice artifact is recorded yet; licensed language resources are not released. |
| Wyoming adapter `wyoming-slv-adapter:20261008` | sensecraft-missionpack.seeed.cn registry, pinned by digest | Image published 2026-10-08. |

Commercial redistribution of the voice models and language resources stays blocked until their licences are recorded here.

## Home Assistant side

| Component | Licence | Notes |
|---|---|---|
| Home Assistant 2026.9.3 | Apache-2.0 | Pinned by digest in `devices/ha_rpi.yaml`. |
| ESPHome 2026.9.1 (optional compose profile) | MIT / GPLv3 (per upstream) | Pinned by digest. |
| Xiaomi Home integration | Xiaomi non-commercial licence | Not bundled. The customer page tells users it is non-commercial only and must be installed by the user. |

Gallery screenshot provenance: `gallery/ATTRIBUTION.md`.
