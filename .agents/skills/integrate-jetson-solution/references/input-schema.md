# Structured Input Schema

This skill accepts structured input only.

## Top-Level Object

```yaml
meta:
  solution_id: "<required>"
  name: "<required>"
  name_zh: "<required>"
  summary: "<required>"
  summary_zh: "<required>"

runtime:
  docker_image: "<required>"
  docker_run_flags:
    - "--gpus all"
    - "--network host"
    - "--ipc host"
    - "--privileged"
    - "-e DISPLAY=$DISPLAY"
    - "-v /tmp/.X11-unix:/tmp/.X11-unix"
    - "-v /dev:/dev"
  container_workdir: "<optional, default empty>"
  app_start_command: "<required>"

stream:
  type: "rtsp"        # rtsp | none, default rtsp
  rtsp_port: 8554     # default 8554
  rtsp_path: "depth"  # default <solution_id>

camera:
  mode: "required"    # required | optional | none, default required
```

## Required Keys

- `meta.solution_id`
- `meta.name`
- `meta.name_zh`
- `meta.summary`
- `meta.summary_zh`
- `runtime.docker_image`
- `runtime.app_start_command`

## Validation Constraints

1. `meta.solution_id` matches: `^[a-z][a-z0-9_]*$`
2. `runtime.docker_image` is non-empty and looks like an image reference
3. `runtime.app_start_command` is non-empty
4. `stream.type` in `{rtsp, none}`
5. `camera.mode` in `{required, optional, none}`

## Defaults

- `stream.type = rtsp`
- `stream.rtsp_port = 8554`
- `stream.rtsp_path = meta.solution_id`
- `camera.mode = required`
- `runtime.container_workdir = ""`
- `runtime.docker_run_flags = []`

## Derived Values

- `rtsp_url_template = "rtsp://{{host}}:<rtsp_port>/<rtsp_path>"` when `stream.type=rtsp`
- if `camera.mode=none`, remove camera-specific compose mounts and disable privileged mode

## Rejection Rules

Reject and stop generation if:
- required keys are missing
- format validation fails
- `solutions/<solution_id>/` already exists and no explicit overwrite confirmation is provided

