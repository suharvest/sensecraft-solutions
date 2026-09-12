# Retail Voice image release channels — 2026-09-11

This document records the image-reference migration applied to the Retail
Voice solution. The six platform/backend references in the solution now use
stable channel tags that point to the validated 2026-09-10 images. The current
solution files were not deployed to a device in this change; importing the
changed solution does not alter an existing device. An existing deployment
needs one controlled migration of its actual device Compose configuration.

## Stable references

| Full registry image | Stable digest | Source validated on 2026-09-10 |
|---|---|---|
| `sensecraft-missionpack.seeed.cn/solution/sensecraft-voice-service:stable` | `sha256:28283325afdfbe7a698f7b2eaf7a2af6c601d3acc012aa662851a01dfcd92817` | `retail-voice-20260910-speaker-v6` |
| `sensecraft-missionpack.seeed.cn/solution/sensecraft-voice-web:stable` | `sha256:0706c600928f1d2289934f38d09dee888f92f55c54e4ea0d0058cbf70663c01b` | `retail-voice-20260910-speaker-v2` |
| `sensecraft-missionpack.seeed.cn/solution/seeed-local-voice:jetson-stable` | `sha256:4d8470906d2ff3ae494c94b9107c09f42f4849b429d98a2b6a5bc1afcc5e7929` | `retail-voice-jetson-20260910-v014a0` |
| `sensecraft-missionpack.seeed.cn/solution/seeed-local-voice:rk-stable` | `sha256:d9c159849795d71db20ed7220c1cbc8532ffb06c3b2ef02c59126553304c185d` | `retail-voice-rk-20260910-v014a0` |
| `sensecraft-missionpack.seeed.cn/solution/seeed-local-voice:rpi-stable` | `sha256:cc635791a802337054c5d65ad91eec91acc10f2ad58eca8dfb2c181d3b0f46d4` | `retail-voice-rpi-20260910-v014a0` |
| `sensecraft-missionpack.seeed.cn/solution/seeed-local-voice:rpi-hailo-stable` | `sha256:55b8069baa63d6f787ede4e4025699be06830373fe1409dee1c474f64508c9e7` | `retail-voice-rpi-hailo-20260910-v014a0` |

## 2026-09-11 backend candidate

The new ARM64 backend candidate was published as the service `:candidate`
channel and as the versioned tag
`retail-voice-20260911-speaker-fallback`. Registry `imagetools` verification
reported the same manifest digest for both tags:

`sha256:bff65c057a09096d896690eb8f17b63ccf86ae38410e57494dd14a70882b0094`

The additional tag
`retail-voice-20260911-speaker-fallback-candidate` also exists as an alias for
the fallback build with the same content. It is not referenced by the Retail
Voice solution and was not removed.

The stable backend reference remains the validated 2026-09-10 digest. Testing
the new backend candidate requires an explicit candidate configuration and one
update operation. Promoting that same image to the stable registry tag does not
require another solution-configuration change; existing devices still need
their one-time Compose migration if they have not migrated yet.

## Validation boundary

The migration patch was checked with `git apply --check`, then applied without
staging. Against the patch's clean base snapshot, the effective change is 21
image-reference files and 60 added/removed reference lines. Existing staged
and unstaged worktree changes were preserved and nothing was staged by this
operation. `solutionctl validate solutions/retail_voice` passed with two existing
warnings about unreferenced collector device files. `solutionctl steps` and a
PyYAML parse of `solution.yaml` plus all 20 device files completed successfully.

No App package was built in this change. No device deployment was run here.

Validation logs:

- `/tmp/retail-voice-channel-validate-20260911.log`
- `/tmp/retail-voice-channel-steps-20260911.log`
- `/tmp/retail-voice-channel-yaml-parse-20260911.log`
