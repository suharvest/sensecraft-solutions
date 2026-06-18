---
name: integrate-jetson-solution
description: Create a Jetson docker_remote solution package from structured inputs, with optional RTSP preview integration. Use when generating a one-click Jetson deployment solution from a Docker image and start command.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
arguments:
  - name: solution_id
    description: "Lowercase snake_case solution id, for example: depth_anything_v3"
    required: true
  - name: docker_image
    description: "Docker image reference, for example: org/app:tag"
    required: true
  - name: app_start_command
    description: "Main command executed inside the container"
    required: true
  - name: stream_type
    description: "Preview mode: rtsp or none. Default: rtsp"
    required: false
  - name: camera_mode
    description: "Camera mode: required, optional, or none. Default: required"
    required: false
---

# Integrate Jetson Solution Skill

Generate a complete `solutions/<solution_id>/` package for Jetson deployment, based on structured user input.

This skill is intentionally scoped to:
- local file generation only
- no application source changes
- structured input only (free-form command blocks are not the primary input)

The generated files must conform to the public contract in **`spec/CONTRACT.md`**
(device schema, `docker_deploy` derivation, guide.md Step/Target syntax). Validate
the result with the offline `solutionctl` tool (see Execution Workflow).

## Inputs Contract

Use the schema in:
- `references/input-schema.md`

Reject the request if required fields are missing.

## Required Validation Rules

1. `solution_id` must match `^[a-z][a-z0-9_]*$`.
2. `docker_image` must be non-empty and include a repo segment.
3. `app_start_command` must be non-empty.
4. `stream.type` must be `rtsp` or `none` (default `rtsp`).
5. `camera.mode` must be `required`, `optional`, or `none` (default `required`).
6. If `solutions/<solution_id>/` already exists, stop and ask for explicit overwrite permission.

## Fixed Decision Logic

1. `stream.type=rtsp`:
- generate `devices/preview.yaml`
- include Step 2 (preview) in `guide.md` and `guide_zh.md`

2. `stream.type=none`:
- do not generate `devices/preview.yaml`
- do not include Step 2 in guides

3. `camera.mode=required`:
- keep `/dev:/dev` mount and `privileged: true` in compose
- guide text says camera is required

4. `camera.mode=optional`:
- keep `/dev:/dev` mount and `privileged: true` in compose
- guide text says camera is optional

5. `camera.mode=none`:
- remove `/dev:/dev` mount
- set `privileged: false`
- guide text says camera is not used

## Compose Compatibility (Must Keep)

Use compatibility flow from:
- `references/compose-compat.md`

The generated `devices/jetson.yaml` must include a before-action equivalent to:
1. probe `docker compose version`
2. probe `docker-compose --version`
3. package fallback: `docker-compose-plugin` -> `docker-compose-v2` -> `docker-compose`
4. fail with a clear message if unavailable

## Output Files

Always generate:
- `solutions/<solution_id>/solution.yaml`
- `solutions/<solution_id>/guide.md`
- `solutions/<solution_id>/guide_zh.md`
- `solutions/<solution_id>/description.md`
- `solutions/<solution_id>/description_zh.md`
- `solutions/<solution_id>/devices/jetson.yaml`
- `solutions/<solution_id>/assets/jetson/docker-compose.yml`

Conditionally generate:
- `solutions/<solution_id>/devices/preview.yaml` (only when `stream.type=rtsp`)

Use templates from:
- `templates/solution.yaml.tmpl`
- `templates/guide.md.tmpl`
- `templates/guide_zh.md.tmpl`
- `templates/description.md.tmpl`
- `templates/description_zh.md.tmpl`
- `templates/devices/jetson.yaml.tmpl`
- `templates/devices/preview.yaml.tmpl`
- `templates/assets/jetson/docker-compose.yml.tmpl`

The `devices/jetson.yaml` is authored as `type: docker_remote`. For the field
shape and how a `docker_deploy` authoring form derives `docker_local` /
`docker_remote` views, see `spec/CONTRACT.md` ("docker_deploy view 派生规则"
and "Device schema fields").

## Rendering Notes

Use direct string substitution for placeholders in `{{UPPER_CASE_KEY}}` format.

Important substitutions:
- `{{SOLUTION_ID}}`
- `{{SOLUTION_NAME}}`
- `{{SOLUTION_NAME_ZH}}`
- `{{SUMMARY_EN}}`
- `{{SUMMARY_ZH}}`
- `{{DOCKER_IMAGE}}`
- `{{APP_START_COMMAND}}`
- `{{CONTAINER_WORKDIR}}`
- `{{RTSP_PORT}}`
- `{{RTSP_PATH}}`
- `{{RTSP_URL_TEMPLATE}}`
- `{{CAMERA_MODE}}`

For camera-dependent compose and guide sections, follow the fixed decision logic above.

### Guide Placeholder Mapping (Deterministic)

Set these placeholders exactly as follows:

1. `camera.mode=required`
- `CAMERA_GUIDE_ROW_EN = Required camera input for inference`
- `CAMERA_GUIDE_ROW_ZH = Required camera input for inference`
- `CAMERA_WIRING_STEP_EN = Connect a USB camera to Jetson.`
- `CAMERA_WIRING_STEP_ZH = Connect a USB camera to Jetson.`

2. `camera.mode=optional`
- `CAMERA_GUIDE_ROW_EN = Optional camera input for inference`
- `CAMERA_GUIDE_ROW_ZH = Optional camera input for inference`
- `CAMERA_WIRING_STEP_EN = Connect a USB camera if your workload needs live camera inference.`
- `CAMERA_WIRING_STEP_ZH = Connect a USB camera if your workload needs live camera inference.`

3. `camera.mode=none`
- `CAMERA_GUIDE_ROW_EN = Not used in this solution`
- `CAMERA_GUIDE_ROW_ZH = Not used in this solution`
- `CAMERA_WIRING_STEP_EN = Camera is not required for this workload.`
- `CAMERA_WIRING_STEP_ZH = Camera is not required for this workload.`

4. `stream.type=rtsp`
- `STREAM_DEPLOY_COMPLETE_EN = RTSP output is expected at {{RTSP_URL_TEMPLATE}}.`
- `STREAM_DEPLOY_COMPLETE_ZH = RTSP output is expected at {{RTSP_URL_TEMPLATE}}.`
- `VALIDATION_STREAM_EN = RTSP endpoint is reachable from the host machine.`
- `VALIDATION_STREAM_ZH = RTSP endpoint is reachable from the host machine.`
- `PREVIEW_STEP_EN_BLOCK = templates/snippets/preview-step.en.md.tmpl content`
- `PREVIEW_STEP_ZH_BLOCK = templates/snippets/preview-step.zh.md.tmpl content`

5. `stream.type=none`
- `STREAM_DEPLOY_COMPLETE_EN = No preview stream is configured for this solution.`
- `STREAM_DEPLOY_COMPLETE_ZH = No preview stream is configured for this solution.`
- `VALIDATION_STREAM_EN = Preview stream validation is skipped.`
- `VALIDATION_STREAM_ZH = Preview stream validation is skipped.`
- `PREVIEW_STEP_EN_BLOCK = ""`
- `PREVIEW_STEP_ZH_BLOCK = ""`

### Docker Flag Mapping (runtime.docker_run_flags)

Parse known flags if present:
- `-e KEY=VALUE` -> add `KEY=VALUE` to compose `environment`
- `-v SRC:DST[:MODE]` -> add entry to compose `volumes`
- `--privileged` -> `privileged: true` (unless `camera.mode=none`, then force false)
- `--network host` -> `network_mode: host`
- `--ipc host` -> `ipc: host`
- `--gpus all` -> keep `runtime: nvidia` and NVIDIA env defaults

Ignore unsupported flags but list them in the final summary.

## Image References (Mirror-Friendly)

Write **public image names** in compose (`influxdb:2.7`, `ultralytics/...`,
`nvcr.io/nvidia/...`). Do not hardcode a CN mirror prefix — a deployment engine
that supports registry mirroring will rewrite public Docker Hub names at deploy
time, and private-registry images (name contains `/` and the first segment
contains `.` or `:`, e.g. `nvcr.io/...`, `host:5000/...`) are left untouched.
Hardcoding a mirror prefix breaks portability across regions.

For HuggingFace model downloads, do not bake `huggingface_hub` into the image;
download on the host with `curl` and bind-mount the model into the container.
Drive the endpoint via the `HF_ENDPOINT` / `HF_ENDPOINT_HOST` environment
variables instead of hardcoding `huggingface.co`, so restricted networks can use
a mirror.

## Execution Workflow

1. Collect structured input.
2. Validate input fields and defaults.
3. Resolve decisions for preview and camera.
4. Render templates into `solutions/<solution_id>/`.
5. Run the offline validation command:

```bash
uv run --package solutionctl solutionctl validate solutions/<solution_id> --spec-dir spec
```

`solutionctl validate` checks the generated solution.yaml / device YAML against
`spec/*.json`, plus guide.md Step/Target syntax and verify-step presence. It must
pass before delivery.

6. Return:
- generated file list
- key decisions (stream/camera)
- validation result summary
- follow-up actions if validation fails

## Known Platform Limitation (Do Not Fix in This Skill)

The RTSP preview step is rendered by the deployment engine, not by this skill.
If preview start fails at runtime on a given host (for example, a platform whose
async subprocess support is limited), report it as a host/runtime issue and
document it in the troubleshooting output. This skill only generates files; it
does not implement preview playback.
