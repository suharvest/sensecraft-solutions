# Docker Compose Compatibility Rules

`docker compose` and `docker-compose` are not the same command name.
Do not assume both exist.

## Rule

Treat compose as available if either probe succeeds:

1. `docker compose version`
2. `docker-compose --version`

## Installation Fallback Order

If compose is unavailable and apt is present, install in this order:

1. `docker-compose-plugin`
2. `docker-compose-v2`
3. `docker-compose`

## Suggested Before-Action Pattern

Use a before-action in `devices/jetson.yaml`:

```bash
compose_ready() {
  docker compose version >/dev/null 2>&1 || docker-compose --version >/dev/null 2>&1
}

if compose_ready; then
  exit 0
fi

if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  for pkg in docker-compose-plugin docker-compose-v2 docker-compose; do
    if apt-get install -y "$pkg"; then
      break
    fi
  done
fi

compose_ready || {
  echo "Docker Compose is unavailable. Need either 'docker compose' or 'docker-compose'."
  exit 1
}
```

## Runtime Command Resolution

At deployment time, runtime should:
- prefer `docker compose` if available
- fallback to `docker-compose` if available

This matches existing robust behavior in this repository.

