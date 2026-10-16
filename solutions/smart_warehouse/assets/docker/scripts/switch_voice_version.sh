#!/usr/bin/env bash
# Switch between OpenVoiceStream v0.9.1 (production) and v0.11 on Jetson
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-status}"

COMPOSE_V091="${DEPLOY_DIR}/docker-compose-jetson-voice-v091.yml"
COMPOSE_V011="${DEPLOY_DIR}/docker-compose-jetson-voice-v011.yml"

# Source .env from deployment directory if present to share Compose configuration
if [ -f "${DEPLOY_DIR}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "${DEPLOY_DIR}/.env"
    set +a
fi

PROJECT="${COMPOSE_PROJECT_NAME:-smart_warehouse_voice_ai}"

resolve_port() {
    local target_ver="${1:-}"
    local compose_file
    if [ "${target_ver}" = "v011" ]; then
        compose_file="${COMPOSE_V011}"
    else
        compose_file="${COMPOSE_V091}"
    fi

    # Try resolving through running container port mapping if available (take first binding if dual-stack)
    local port
    port=$(docker compose -p "${PROJECT}" -f "${compose_file}" port speech 8000 2>/dev/null | awk -F: '{print $NF}' | head -n 1 || true)
    if [ -n "${port}" ]; then
        echo "${port}"
        return 0
    fi

    if [ "${target_ver}" = "v011" ]; then
        echo "${OVS_V011_PORT:-${OVS_PORT:-8621}}"
    else
        echo "${OVS_PORT:-8621}"
    fi
}

check_health() {
    local port="${1:-8621}"
    # Allow enough time for cold start / initial model download (up to 15 min, polling every 5s)
    local retries=180
    echo "Waiting for speech service on port ${port} to be healthy (cold start may take time to load/download)..."
    for i in $(seq 1 "${retries}"); do
        if curl --connect-timeout 2 --max-time 4 -fsS "http://127.0.0.1:${port}/readyz" >/dev/null 2>&1; then
            echo "Speech service is READY on port ${port} (readyz returned 200) ✓"
            return 0
        fi
        sleep 5
    done
    echo "Speech service did not become ready within 15 minutes on port ${port} (check docker logs for progress)" >&2
    return 1
}

check_external_conflicts() {
    for legacy in seeed-voice-v091 seeed-voice-v011 seeed-voice-v011-candidate; do
        if docker ps -a -q -f name="^/${legacy}$" | grep -q .; then
            local exist_proj
            exist_proj=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "${legacy}" 2>/dev/null || true)
            if [ -n "${exist_proj}" ] && [ "${exist_proj}" != "${PROJECT}" ]; then
                echo "Error: Speech container '${legacy}' already exists and belongs to another project ('${exist_proj}')." >&2
                echo "Switch aborted to protect existing workloads. Please manually stop or remove it:" >&2
                echo "  docker rm -f ${legacy}" >&2
                return 1
            fi
        fi
    done
}

detect_running_version() {
    local cid
    cid=$(docker compose -p "${PROJECT}" -f "${COMPOSE_V011}" ps -q speech 2>/dev/null || true)
    if [ -n "${cid}" ] && [ "$(docker inspect -f '{{.State.Running}}' "${cid}" 2>/dev/null || true)" = "true" ]; then
        local img name
        img=$(docker inspect -f '{{.Config.Image}}' "${cid}" 2>/dev/null || true)
        name=$(docker inspect -f '{{.Name}}' "${cid}" 2>/dev/null || true)
        case "${img}:${name}" in
            *v0.11*|*v011*)
                echo "v011"
                return 0
                ;;
            *v091*|*v0.9*|*vox080*)
                echo "v091"
                return 0
                ;;
        esac
    fi
    echo "none"
}

rollback() {
    local prev="$1"
    if [ "${prev}" = "v011" ]; then
        echo "Attempting rollback to v0.11..." >&2
        docker compose -p "${PROJECT}" -f "${COMPOSE_V011}" up -d speech 2>/dev/null || true
    elif [ "${prev}" = "v091" ]; then
        echo "Attempting rollback to v0.9.1..." >&2
        docker compose -p "${PROJECT}" -f "${COMPOSE_V091}" up -d speech 2>/dev/null || true
    else
        echo "No previously running version detected; stopping failed speech service..." >&2
        docker compose -p "${PROJECT}" -f "${COMPOSE_V011}" stop speech 2>/dev/null || true
        docker compose -p "${PROJECT}" -f "${COMPOSE_V091}" stop speech 2>/dev/null || true
    fi
}

case "${ACTION}" in
    status)
        port="$(resolve_port "status")"
        echo "=== Active Speech Service Containers ==="
        docker ps --filter "name=seeed-voice" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        if curl --connect-timeout 2 --max-time 4 -fsS "http://127.0.0.1:${port}/readyz" >/dev/null 2>&1; then
            echo "Port ${port} /readyz: HEALTHY ✓"
        else
            echo "Port ${port} /readyz: NOT RESPONDING"
        fi
        ;;

    v011)
        check_external_conflicts
        PREV_VER="$(detect_running_version)"
        echo "=== Switching to OpenVoiceStream v0.11 (previous: ${PREV_VER}) ==="
        if ! docker compose -p "${PROJECT}" -f "${COMPOSE_V011}" up -d speech; then
            echo "Switch to v0.11 failed during container startup!" >&2
            rollback "${PREV_VER}"
            exit 1
        fi
        port="$(resolve_port "v011")"
        if ! check_health "${port}"; then
            echo "Health check failed on port ${port}!" >&2
            rollback "${PREV_VER}"
            exit 1
        fi
        ;;

    v091)
        check_external_conflicts
        PREV_VER="$(detect_running_version)"
        echo "=== Switching to OpenVoiceStream v0.9.1 Production (previous: ${PREV_VER}) ==="
        if ! docker compose -p "${PROJECT}" -f "${COMPOSE_V091}" up -d speech; then
            echo "Switch to v0.9.1 failed during container startup!" >&2
            rollback "${PREV_VER}"
            exit 1
        fi
        port="$(resolve_port "v091")"
        if ! check_health "${port}"; then
            echo "Health check failed on port ${port}!" >&2
            rollback "${PREV_VER}"
            exit 1
        fi
        ;;

    *)
        echo "Usage: $0 {status|v011|v091}"
        exit 1
        ;;
esac
