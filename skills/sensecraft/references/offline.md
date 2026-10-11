# Deploy where there is no internet (offline package)

Prepare on a computer that has internet, deploy on site without it. The unit
is **step × target**: you can prepare one step only, or several device models
for the same step. The engine has no separate command for this; use
`sensecraft-engine api` (run `sensecraft-engine api --help` for the same notes).

Ask the user first: preparing downloads container images and files, which can
take several GB of disk space.

## 1. Plan: what is needed, what is already here

Write the request to a file, e.g. `./.sensecraft-work/plan.json`:

```json
{
  "solution_id": "<id>",
  "preset_id": "<preset>",
  "targets": {"<step_id>": "<target_id>"},
  "arch": {"<step_id>": "aarch64"},
  "params": {"username": "<the username the deploy will use>"},
  "lang": "en"
}
```

- `targets`: only the steps listed are prepared; leave it out for every step.
- `arch`: needed when the target names no device type (`aarch64` for
  ARM boards such as Jetson, Raspberry Pi, RK3588).
- `params`: **the same connection values the later deploy will use** (from
  `deploy-info`'s `request_template`, e.g. `username`). The package records
  them; a deploy with different values is refused before anything runs on the
  device (`the offline package was prepared with different values: ...`), and
  you have to plan and prepare again with the right `params`.

```
sensecraft-engine api POST /api/staging/plan --data "$(cat ./.sensecraft-work/plan.json)"
```

The response lists each item and whether it is already here. Items marked
`partial` still need internet on site (for example a model the container
downloads at start); tell the user which.

## 2. Prepare: download it here

```
sensecraft-engine api POST /api/staging/prepare --data "$(cat ./.sensecraft-work/plan.json)"
sensecraft-engine api GET /api/staging/jobs/<id>      # repeat every 5–10 s until status is not "running"
```

`prepare` returns a job with `id` and `status: running`. Cancel it with
`sensecraft-engine api POST /api/staging/jobs/<id>/cancel`.

## 3. Check, carry, clean up

```
sensecraft-engine api GET /api/staging/entries                                   # what is prepared
sensecraft-engine api POST /api/staging/export --data '{"path": "/path/kit.tar"}' # pack it
sensecraft-engine api POST /api/staging/import --data '{"path": "/path/kit.tar"}' # on the deploying computer
```

Deleting prepared entries (`POST /api/staging/entries/delete`) frees disk space;
ask the user first.

## 4. Deploy on site

Deploy as in `deploy.md`, with `"force_offline": true` in the step's
connection:

```json
"device_connections": {
  "<step_id>": {"target": "<target_id>", "target_type": "remote",
                "host": "<ip>", "username": "<same as params>",
                "password": "<password>", "force_offline": true}
}
```

The engine checks the offline package before connecting to the device and
stops with a list of what is missing.
