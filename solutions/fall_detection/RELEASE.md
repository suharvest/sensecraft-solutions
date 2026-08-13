# fall_detection — release runbook

Maintainer-facing. Not referenced by `solution.yaml`, so it does not render on the
solution page.

All artifacts for the `0.1.0-rc1` release are published and the compose files
reference the real registry refs. This file records what was shipped and the
procedure for shipping the next tag.

What is **not** done: no preset has been deployed end to end through the app yet,
so no preset claims `verified: hardware`, and RK/Hailo have no fall-accuracy
figure. See sections 5 and 6.

## 1. Current state

| Artifact | Where | State |
|---|---|---|
| reCamera deb `fall-detection_0.2.0_riscv64.deb` | `sensecraft-statics` | **live**, sha256 `a7e3347a…` verified |
| reCamera model `yolo11n_pose_cv181x_int8.cvimodel` | `sensecraft-statics` | **live**, sha256 `44db2898…` verified |
| Console deb `supervisor_0.5.5_riscv64.deb` | `sensecraft-statics` | **live**, sha256 `a2c877f1…` |
| Jetson ONNX `yolo11s-pose.onnx` | `sensecraft-statics` | **live**, 40,551,348 B, sha256 `8918cfc1…` |
| Jetson ONNX `yolo11m-pose.onnx` | `sensecraft-statics` | **live**, 84,062,930 B, sha256 `7fe87620…` |
| RK model `…fp16.rk3576.rknn` | `sensecraft-statics` | **live**, 10,532,939 B, sha256 `659519ae…` |
| RK model `…fp16.rk3588.rknn` | `sensecraft-statics` | **live**, 7,647,051 B, sha256 `22f00270…` |
| RK temporal `temporal-rk3588.npz` | `sensecraft-statics` | **live**, 65,854 B, sha256 `b7213580…` |
| RK temporal `temporal-rk3576.npz` | `sensecraft-statics` | **live**, 65,921 B, sha256 `dadcb916…` |
| Hailo HEF `yolov8s_pose.hef` | Hailo Model Zoo | **no hosting needed** — fetched at deploy time, digest `e1985669…` |
| Jetson image `solution/fall-detection-jetson:0.1.0-rc1` | registry | **live** |
| RK image `solution/fall-detection-rknn:0.1.0-rc2` | registry | **live** |
| Hailo image `solution/fall-detection-rpi-hailo:0.1.0-rc1` | registry | **live** |

Note the layout: **one repository per platform**, not one repository with per-platform
tags. `solution/fall-detection` does not exist and a request for it returns
`NOT_FOUND`. All three carry the same release tag `0.1.0-rc1`.

**No image bakes a model.** Verified by running each image with `ls -l /models`:
both RK and Hailo report no such directory. Every preset therefore fetches its
model at deploy time — RK from the CDN per board, Hailo from the Hailo Model Zoo,
Jetson downloads the ONNX and builds the engine on the device. Keep it that way:
an RKNN artifact is board-specific, so baking one in would make the image
non-portable between RK3576 and RK3588, and a TensorRT engine is tied to the exact
GPU and TensorRT version.

All CDN paths are under
`https://sensecraft-statics.seeed.cc/solution-app/fall_detection/models/`.

## 2. Authenticate (only needed to publish a new tag)

Each image exists only on the device that built it — they are arm64 and were built
natively — so each push runs from its own device. As of the `0.1.0-rc1` release only
`radxa` still holds a Docker credential; `orin-nano` and `harvest-pi` have no
`~/.docker/config.json`, so publishing a new tag from them needs a fresh login.

Run once per device, interactively:

```bash
~/.rpty/bin/fleet ssh orin-nano     # then: docker login sensecraft-missionpack.seeed.cn
~/.rpty/bin/fleet ssh radxa         # then: docker login sensecraft-missionpack.seeed.cn
~/.rpty/bin/fleet ssh harvest-pi    # then: docker login sensecraft-missionpack.seeed.cn
```

Confirm it took, without printing the credential:

```bash
~/.rpty/bin/fleet exec orin-nano -- 'python3 -c "import json;print(list(json.load(open(\"/root/.docker/config.json\" if False else \"$HOME/.docker/config.json\"))[\"auths\"])"'
```

## 3. Push the images

Docker on all three devices is in the `docker` group — no `--sudo`. Each image is
arm64 and exists only on the device that built it, so each push runs from there.

**Repository layout: one repo per platform.** There is no `solution/fall-detection`
repo — asking for it returns `NOT_FOUND`. The release tag is shared across the three.

| Platform | Device | Source image | Published as |
|---|---|---|---|
| Jetson | `orin-nano` | `fall-detection:jetson-slim` | `solution/fall-detection-jetson:0.1.0-rc1` |
| RK | `radxa` | `fall-detection-rknn:2.4.0` | `solution/fall-detection-rknn:0.1.0-rc2` |
| Hailo | `harvest-pi` | `fall-detection-rpi-hailo:4.21` | `solution/fall-detection-rpi-hailo:0.1.0-rc1` |

Upstream publishes a release manifest at `release/0.1.0-rc2.json` naming each
image reference and digest — treat it as the source of truth when bumping tags
here. As of rc2 only the RK image moved; Jetson and Hailo stay at rc1.

Push RK from `radxa`, not `cat-remote` — the latter's device-side rebuild failed
with a Docker base-layer `unexpected EOF`. One RK push serves both boards: the
image is board-agnostic and only the `.rknn` differs, which is downloaded per board
at deploy time.

To publish the next tag, substituting `<TAG>`:

```bash
F=~/.rpty/bin/fleet
REG=sensecraft-missionpack.seeed.cn/solution

$F exec --timeout 1800 orin-nano -- \
  "docker tag fall-detection:jetson-slim $REG/fall-detection-jetson:<TAG> && \
   docker push $REG/fall-detection-jetson:<TAG>"

$F exec --timeout 1800 radxa -- \
  "docker tag fall-detection-rknn:2.3.0 $REG/fall-detection-rknn:<TAG> && \
   docker push $REG/fall-detection-rknn:<TAG>"

$F exec --timeout 1800 harvest-pi -- \
  "docker tag fall-detection-rpi-hailo:4.21 $REG/fall-detection-rpi-hailo:<TAG> && \
   docker push $REG/fall-detection-rpi-hailo:<TAG>"
```

Then update the three `image:` lines in `assets/{jetson,rk,hailo}/docker-compose.yml`
in the same change — a pushed tag nothing references is not a release.

## 4. Verify

The registry answers `401` to anonymous reads, so verify while authenticated. Tag
listing is the quickest check that a push landed in the repo you meant:

```bash
$F exec --timeout 180 radxa -- 'CRED=$(python3 -c "
import json,base64
a=json.load(open(\"$HOME/.docker/config.json\"))[\"auths\"]
k=[x for x in a if \"missionpack\" in x][0]
print(base64.b64decode(a[k][\"auth\"]).decode())
")
for R in fall-detection-jetson fall-detection-rknn fall-detection-rpi-hailo; do
  printf "%-30s " "$R"
  curl -s --max-time 30 -u "$CRED" \
    https://sensecraft-missionpack.seeed.cn/v2/solution/$R/tags/list; echo
done'
```

Confirmed for `0.1.0-rc1`: all three repos list the tag.

Also confirm no model got baked in, since that is the difference between a
portable image and one pinned to a single board:

```bash
$F exec --timeout 240 radxa -- \
  "docker run --rm --entrypoint sh $REG/fall-detection-rknn:<TAG> -c 'ls -l /models || echo NO_MODELS_DIR'"
```

Expect `NO_MODELS_DIR`.

## 5. End-to-end deploy test, per preset

Only after the pushes. Deploy through the app (or `solutionctl`) rather than by
hand — the point is to exercise the authored device YAML, not the containers.

What each run must prove:

1. The image pulls on a device that never built it.
2. `after_upload` completes — Jetson builds the TensorRT engine (~461 s for
   YOLO11s; budget 900 s+), RK downloads the board-matched `.rknn` and passes its
   sha256, Hailo fetches the HEF and passes its digest.
3. The container publishes to `recamera/fall-detection/results/<stream-id>`.
4. The preview step renders video **with the overlay aligned to the person**.
   For RK and Hailo specifically, confirm the skeleton is not squashed toward the
   vertical centre — that is the signature of the letterbox inversion failing, and
   it is the one thing that cannot be checked without a real stream.

## 6. Only then, claim verification

`verified:` is a promise to the user. Add it per preset in `solution.yaml` **after**
that preset has actually run on hardware, not before:

```yaml
      verified:
        - hardware
```

Current honest state, do not pre-fill:

| Preset | Claim today | Unblocks when |
|---|---|---|
| `recamera` | none | someone runs it on a reCamera 2002 |
| `jetson` | none | the pushed image is deployed through the app end to end |
| `rk` | none | same, on RK3576 **and** RK3588 — one does not imply the other, and each now loads its own temporal profile |
| `hailo` | none | same, and with a person actually in frame |

Accuracy is a separate claim and is **not** unblocked by any of this. RK and Hailo
now carry platform-native frozen profiles (88.9% on the held-out Subject 4 test),
but those measure the **temporal gate**, not the deployed state machine that
produces the MQTT alert. Keep the two labelled apart in `description.md`: the gate
fires earlier and reads higher, so presenting it beside the reCamera and Jetson
deployed figures would overstate the boards.

## 7. Re-push and rollback

Tags are immutable by convention here — to ship a fix, push a new tag and update
the `image:` line in the matching compose file. Do not overwrite a tag that a user
may already have pulled.

If a bad image did ship under a tag in use, the fastest correct fix is a new tag
plus a compose bump, published together.

## 8. Known non-blockers, recorded so they are not re-investigated

- The three devices **cannot reach Docker Hub** (`registry-1.docker.io` times out).
  Mirrors work and `sensecraft-missionpack.seeed.cn` is reachable. The composes use
  `eclipse-mosquitto:2` unqualified on purpose — the deployment engine rewrites
  public Docker Hub names through its mirror, and private-registry names are left
  untouched.
- Jetson `trtexec --version` exits 1 on TensorRT 10.3. Any script that gates on it
  under `set -e` aborts before doing any work.
- Upstream source: <https://github.com/suharvest/edgefallkit> (Apache-2.0), which
  carries all seven platform directories. The three fixes made during this work
  are in it — verified against `main`: `global RUNNING` in `app.py` and the
  `trtexec --version` guard are present. The `/dev:/dev` mount is still in the
  upstream `platforms/jetson/docker-compose.yml`; that is fine, because this
  solution ships its own compose without it (runc rejects recreating `/dev/pts`
  inodes, and the nvidia runtime injects the GPU nodes anyway).
