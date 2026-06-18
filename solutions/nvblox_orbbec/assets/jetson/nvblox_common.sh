#!/usr/bin/env bash

if [[ "${NVBLOX_ORBBEC_COMMON_SH:-0}" == "1" ]]; then
  return 0
fi
readonly NVBLOX_ORBBEC_COMMON_SH=1

resolve_setup_user_name() {
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    printf '%s\n' "${SUDO_USER}"
    return 0
  fi
  id -un
}

lookup_user_passwd_entry() {
  local user_name="$1"
  getent passwd "${user_name}" 2>/dev/null | head -n 1
}

resolve_user_home() {
  local user_name="$1"
  local passwd_entry=""

  passwd_entry="$(lookup_user_passwd_entry "${user_name}")"
  [[ -n "${passwd_entry}" ]] || {
    printf '[nvblox-orbbec][ERROR] Cannot resolve passwd entry for user %s.\n' "${user_name}" >&2
    exit 1
  }
  printf '%s\n' "$(cut -d: -f6 <<<"${passwd_entry}")"
}

readonly SETUP_USER_NAME="$(resolve_setup_user_name)"
readonly SETUP_USER_HOME="$(resolve_user_home "${SETUP_USER_NAME}")"
readonly SETUP_USER_UID="$(id -u "${SETUP_USER_NAME}")"
readonly SETUP_USER_GID="$(id -g "${SETUP_USER_NAME}")"
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly MANAGED_ROOT_DEFAULT="${SETUP_USER_HOME}/nvblox_demo"
readonly MANAGED_SENTINEL_NAME=".managed-by-nvblox-orbbec"
readonly ROS_DISTRO_DEFAULT="humble"
readonly ORBBEC_VERSION="v2.3.4"
readonly ORBBEC_REPO_URL="https://github.com/orbbec/OrbbecSDK_ROS2.git"
readonly BASE_IMAGE_PREFERRED="isaac_ros_dev-aarch64:latest"
readonly DERIVED_IMAGE_TAG="local/isaac_ros_nvblox_orbbec:jp6-humble"
readonly CONTAINER_NAME_DEFAULT="isaac_ros_nvblox_orbbec"
readonly CONTAINER_WORKSPACE_SPEC_VERSION="nvblox-orbbec-v1"
readonly FASTDDS_RUNTIME_DIR_RELATIVE=".runtime/fastdds"
readonly FASTDDS_UDP_ONLY_PROFILE_FILENAME="udp_only.xml"

export PATH="${SETUP_USER_HOME}/.local/bin:${PATH}"

DOCKER_PREFIX=()

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  local level="$1"
  shift
  printf '[%s] [%s] %s\n' "$(timestamp)" "${level}" "$*"
}

info() {
  log INFO "$@"
}

warn() {
  log WARN "$@"
}

error() {
  log ERROR "$@" >&2
}

die() {
  error "$@"
  exit 1
}

ensure_supported_user_context() {
  if [[ "${EUID}" -eq 0 && -z "${SUDO_USER:-}" ]]; then
    die "Running from a root login shell is not supported. Use a normal user account."
  fi
}

run_sudo() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

apt_lock_paths() {
  printf '%s\n' \
    /var/lib/apt/lists/lock \
    /var/cache/apt/archives/lock \
    /var/lib/dpkg/lock-frontend \
    /var/lib/dpkg/lock
}

apt_lock_error_in_file() {
  local file_path="$1"
  [[ -f "${file_path}" ]] || return 1
  grep -Eq \
    'Could not get lock|Unable to lock directory|Could not open lock file|Waiting for cache lock' \
    "${file_path}"
}

print_apt_lock_owner_details() {
  local lock_path="$1"
  local pids=""
  local pid=""
  local ps_line=""

  if ! command -v fuser >/dev/null 2>&1; then
    warn "fuser is not available; cannot resolve the lock owner for ${lock_path}."
    return 0
  fi

  pids="$(fuser "${lock_path}" 2>/dev/null || true)"
  if [[ -z "${pids}" ]]; then
    warn "No active process currently owns ${lock_path}."
    return 0
  fi

  for pid in ${pids}; do
    ps_line="$(ps -o pid=,comm=,args= -p "${pid}" 2>/dev/null | sed 's/^ *//' || true)"
    if [[ -n "${ps_line}" ]]; then
      warn "Lock owner on ${lock_path}: ${ps_line}"
    else
      warn "Lock owner on ${lock_path}: pid=${pid}"
    fi
  done
}

print_apt_lock_state() {
  local lock_path=""

  for lock_path in $(apt_lock_paths); do
    if [[ -e "${lock_path}" ]]; then
      warn "Observed apt lock path: ${lock_path}"
      print_apt_lock_owner_details "${lock_path}"
    fi
  done
}

wait_for_apt_lock_owner() {
  local deadline="$1"
  local attempt="$2"
  local poll_seconds="${APT_LOCK_POLL_SECONDS:-5}"
  local remaining_seconds=0

  remaining_seconds=$((deadline - SECONDS))
  if ((remaining_seconds < 0)); then
    remaining_seconds=0
  fi

  warn "APT is locked by another process. Waiting up to ${remaining_seconds}s for the lock to clear (attempt ${attempt})."
  print_apt_lock_state
  sleep "${poll_seconds}"
}

run_apt_with_lock_retry() {
  local max_wait_seconds="${APT_LOCK_MAX_WAIT_SECONDS:-300}"
  local deadline=$((SECONDS + max_wait_seconds))
  local attempt=1
  local stdout_log=""
  local stderr_log=""
  local exit_code=0
  local line=""

  while true; do
    stdout_log="$(mktemp)"
    stderr_log="$(mktemp)"

    if run_sudo "$@" >"${stdout_log}" 2>"${stderr_log}"; then
      cat "${stdout_log}"
      if [[ -s "${stderr_log}" ]]; then
        cat "${stderr_log}" >&2
      fi
      rm -f "${stdout_log}" "${stderr_log}"
      return 0
    fi

    exit_code=$?
    cat "${stdout_log}"

    if ! apt_lock_error_in_file "${stderr_log}"; then
      cat "${stderr_log}" >&2
      rm -f "${stdout_log}" "${stderr_log}"
      return "${exit_code}"
    fi

    while IFS= read -r line; do
      [[ -n "${line}" ]] || continue
      warn "apt stderr: ${line}"
    done < "${stderr_log}"

    if ((SECONDS >= deadline)); then
      error "Timed out waiting for apt lock after ${max_wait_seconds}s."
      print_apt_lock_state
      cat "${stderr_log}" >&2
      rm -f "${stdout_log}" "${stderr_log}"
      return "${exit_code}"
    fi

    wait_for_apt_lock_owner "${deadline}" "${attempt}"
    rm -f "${stdout_log}" "${stderr_log}"
    attempt=$((attempt + 1))
  done
}

guard_managed_root_path() {
  local root="$1"
  local sentinel="${root}/${MANAGED_SENTINEL_NAME}"

  if [[ -e "${root}" && ! -e "${sentinel}" ]]; then
    if managed_root_can_be_adopted "${root}"; then
      warn "Managed root ${root} exists without a sentinel but matches this solution layout. Adopting it."
      return 0
    fi
    die "Managed root ${root} exists but is not owned by this solution."
  fi
}

managed_root_can_be_adopted() {
  local root="$1"
  local entry=""
  local entry_name=""
  local restore_dotglob=""
  local restore_nullglob=""

  [[ -d "${root}" ]] || return 1

  restore_nullglob="$(shopt -p nullglob || true)"
  restore_dotglob="$(shopt -p dotglob || true)"
  shopt -s nullglob dotglob

  for entry in "${root}"/* "${root}"/.*; do
    entry_name="$(basename "${entry}")"
    case "${entry_name}" in
      .|..)
        continue
        ;;
      downloads|logs|.stamps|ros2_ws|isaac_ros-dev|.runtime)
        ;;
      *)
        eval "${restore_nullglob}"
        eval "${restore_dotglob}"
        return 1
        ;;
    esac
  done

  eval "${restore_nullglob}"
  eval "${restore_dotglob}"
  return 0
}

bootstrap_managed_root() {
  local root="$1"
  local sentinel="${root}/${MANAGED_SENTINEL_NAME}"

  guard_managed_root_path "${root}"
  mkdir -p "${root}/logs" "${root}/.stamps"
  if [[ ! -f "${sentinel}" ]]; then
    {
      printf 'managed_root=%s\n' "${root}"
      printf 'created_at=%s\n' "$(date -Is 2>/dev/null || date)"
      printf 'project_root=%s\n' "${PROJECT_ROOT}"
    } > "${sentinel}"
  fi
}

repair_managed_root_ownership() {
  local root="$1"
  local sentinel="${root}/${MANAGED_SENTINEL_NAME}"

  [[ -d "${root}" && -f "${sentinel}" ]] || return 0
  if find "${root}" \( ! -uid "${SETUP_USER_UID}" -o ! -gid "${SETUP_USER_GID}" \) -print -quit 2>/dev/null | grep -q .; then
    info "Repairing managed root ownership under ${root}."
    run_sudo chown -R "${SETUP_USER_UID}:${SETUP_USER_GID}" "${root}"
  fi
}

require_bootstrapped_managed_root() {
  local root="$1"
  local sentinel="${root}/${MANAGED_SENTINEL_NAME}"
  [[ -f "${sentinel}" ]] || die "Managed root ${root} is not prepared yet."
}

package_installed() {
  local package_name="$1"
  dpkg-query -W -f='${Status}' "${package_name}" 2>/dev/null | grep -q 'install ok installed'
}

install_packages_if_missing() {
  local missing=()
  local package_name=""

  for package_name in "$@"; do
    if ! package_installed "${package_name}"; then
      missing+=("${package_name}")
    fi
  done

  if ((${#missing[@]} == 0)); then
    return 0
  fi

  info "Installing apt packages: ${missing[*]}"
  run_apt_with_lock_retry apt-get update
  run_apt_with_lock_retry apt-get install -y --no-install-recommends "${missing[@]}"
}

apt_package_available() {
  local package_name="$1"
  apt-cache show "${package_name}" >/dev/null 2>&1
}

install_first_available_package_if_missing() {
  local package_name=""

  for package_name in "$@"; do
    if package_installed "${package_name}"; then
      return 0
    fi
  done

  run_apt_with_lock_retry apt-get update
  for package_name in "$@"; do
    if apt_package_available "${package_name}"; then
      info "Installing apt package: ${package_name}"
      run_apt_with_lock_retry apt-get install -y --no-install-recommends "${package_name}"
      return 0
    fi
  done

  return 1
}

ensure_python_cli_tools() {
  local pip_packages=()

  install_packages_if_missing python3 python3-pip python3-setuptools python3-wheel build-essential git curl

  if ! command -v rosdep >/dev/null 2>&1; then
    install_first_available_package_if_missing python3-rosdep python3-rosdep2 || pip_packages+=(rosdep)
  fi

  if ! command -v vcs >/dev/null 2>&1; then
    install_first_available_package_if_missing python3-vcstool vcstool || pip_packages+=(vcstool)
  fi

  if ! command -v colcon >/dev/null 2>&1; then
    install_first_available_package_if_missing python3-colcon-common-extensions || pip_packages+=(colcon-common-extensions)
  fi

  if ((${#pip_packages[@]} > 0)); then
    info "Installing Python CLI tools with pip: ${pip_packages[*]}"
    python3 -m pip install --user --upgrade "${pip_packages[@]}"
    hash -r
  fi

  command -v rosdep >/dev/null 2>&1 || die "Required command not found after setup: rosdep"
  command -v vcs >/dev/null 2>&1 || die "Required command not found after setup: vcs"
  command -v colcon >/dev/null 2>&1 || die "Required command not found after setup: colcon"
}

assert_command() {
  local command_name="$1"
  command -v "${command_name}" >/dev/null 2>&1 || die "Required command not found: ${command_name}"
}

source_ros_setup() {
  local workspace_root="${1:-}"
  local restore_nounset=0

  if [[ $- == *u* ]]; then
    restore_nounset=1
    set +u
  fi

  # shellcheck disable=SC1091
  source "/opt/ros/${ROS_DISTRO_DEFAULT}/setup.bash"
  if [[ -n "${workspace_root}" && -f "${workspace_root}/install/setup.bash" ]]; then
    # shellcheck disable=SC1090
    source "${workspace_root}/install/setup.bash"
  fi

  if (( restore_nounset )); then
    set -u
  fi
}

ensure_docker_access() {
  if docker info >/dev/null 2>&1; then
    DOCKER_PREFIX=()
    return 0
  fi
  if sudo docker info >/dev/null 2>&1; then
    DOCKER_PREFIX=(sudo)
    return 0
  fi
  die "Cannot access the Docker daemon with docker or sudo docker."
}

package_version_prefix() {
  local package_name="$1"
  local raw_version=""

  raw_version="$(dpkg-query -W -f='${Version}' "${package_name}" 2>/dev/null || true)"
  [[ -n "${raw_version}" ]] || return 1

  printf '%s\n' "${raw_version}" | grep -oE '[0-9]+([.][0-9]+)*' | head -n 1
}

detect_l4t_version() {
  local version=""
  local release_major=""
  local revision=""

  version="$(package_version_prefix nvidia-l4t-core || true)"
  if [[ -n "${version}" ]]; then
    printf '%s\n' "${version}"
    return 0
  fi

  [[ -f /etc/nv_tegra_release ]] || return 1

  release_major="$(sed -nE 's/^# R([0-9]+).*/\1/p' /etc/nv_tegra_release | head -n 1)"
  revision="$(sed -nE 's/^# R[0-9]+.*REVISION: *([0-9.]+).*/\1/p' /etc/nv_tegra_release | head -n 1)"

  [[ -n "${release_major}" ]] || return 1
  if [[ -n "${revision}" ]]; then
    printf '%s.%s\n' "${release_major}" "${revision}"
  else
    printf '%s\n' "${release_major}"
  fi
}

detect_jetpack_major_version() {
  local jetpack_version=""
  local l4t_version=""
  local l4t_major=""

  jetpack_version="$(package_version_prefix nvidia-jetpack || true)"
  if [[ -n "${jetpack_version}" ]]; then
    printf '%s\n' "${jetpack_version%%.*}"
    return 0
  fi

  l4t_version="$(detect_l4t_version || true)"
  [[ -n "${l4t_version}" ]] || return 1

  l4t_major="${l4t_version%%.*}"
  case "${l4t_major}" in
    36)
      printf '6\n'
      return 0
      ;;
    35|34)
      printf '5\n'
      return 0
      ;;
  esac

  return 1
}

describe_jetpack_runtime() {
  local jetpack_version=""
  local l4t_version=""
  local jetpack_major=""

  jetpack_version="$(package_version_prefix nvidia-jetpack || true)"
  if [[ -n "${jetpack_version}" ]]; then
    printf 'JetPack %s (nvidia-jetpack)\n' "${jetpack_version}"
    return 0
  fi

  l4t_version="$(detect_l4t_version || true)"
  if [[ -n "${l4t_version}" ]]; then
    jetpack_major="$(detect_jetpack_major_version || true)"
    if [[ -n "${jetpack_major}" ]]; then
      printf 'L4T %s (derived JetPack %s.x)\n' "${l4t_version}" "${jetpack_major}"
    else
      printf 'L4T %s\n' "${l4t_version}"
    fi
    return 0
  fi

  return 1
}

assert_supported_jetpack_major() {
  local required_major="$1"
  local detected_major=""
  local description=""

  detected_major="$(detect_jetpack_major_version || true)"
  description="$(describe_jetpack_runtime || true)"

  [[ -n "${detected_major}" ]] || die "Unable to detect JetPack/L4T version. JetPack ${required_major}.x is required."
  [[ "${detected_major}" == "${required_major}" ]] || die "Unsupported JetPack runtime: ${description:-unknown}. JetPack ${required_major}.x is required."
}

docker_cmd() {
  if ((${#DOCKER_PREFIX[@]})); then
    "${DOCKER_PREFIX[@]}" docker "$@"
  else
    docker "$@"
  fi
}

append_jetson_container_args() {
  local -n jetson_args_ref="$1"

  jetson_args_ref+=(
    --runtime=nvidia
    --privileged
    --network host
    --ipc host
    --pid host
    --ulimit memlock=-1
    --ulimit stack=67108864
    -e "NVIDIA_VISIBLE_DEVICES=nvidia.com/gpu=all,nvidia.com/pva=all"
    -e "NVIDIA_DRIVER_CAPABILITIES=all"
    -e "ISAAC_ROS_WS=/workspaces/isaac_ros-dev"
    -v /etc/localtime:/etc/localtime:ro
    -v /tmp:/tmp
  )

  if [[ -f /usr/bin/tegrastats ]]; then
    jetson_args_ref+=(-v /usr/bin/tegrastats:/usr/bin/tegrastats)
  fi
  if [[ -d /usr/lib/aarch64-linux-gnu/tegra ]]; then
    jetson_args_ref+=(-v /usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra)
  fi
  if [[ -d /usr/src/jetson_multimedia_api ]]; then
    jetson_args_ref+=(-v /usr/src/jetson_multimedia_api:/usr/src/jetson_multimedia_api)
  fi
  if [[ -d /usr/share/vpi3 ]]; then
    jetson_args_ref+=(-v /usr/share/vpi3:/usr/share/vpi3)
  fi
}

select_base_image() {
  local candidate=""

  if docker_cmd image inspect "${BASE_IMAGE_PREFERRED}" >/dev/null 2>&1; then
    printf '%s\n' "${BASE_IMAGE_PREFERRED}"
    return 0
  fi

  candidate="$(docker_cmd image ls --format '{{.Repository}}:{{.Tag}}' | grep -E '^nvcr\.io/nvidia/isaac/ros:.*aarch64-ros2_humble' | head -n 1 || true)"
  if [[ -n "${candidate}" ]]; then
    printf '%s\n' "${candidate}"
    return 0
  fi
  return 1
}

acceptable_base_image_hint() {
  printf '%s\n' "${BASE_IMAGE_PREFERRED} or nvcr.io/nvidia/isaac/ros:*aarch64-ros2_humble*"
}

docker_image_id() {
  local image_ref="$1"
  docker_cmd image inspect --format '{{.Id}}' "${image_ref}"
}

managed_root_base_image_tar_path() {
  local managed_root="$1"
  printf '%s/downloads/nvblox_images.tar\n' "${managed_root}"
}

cleanup_cached_base_image_downloads_if_image_present() {
  local managed_root="$1"
  local target_image="${2:-${BASE_IMAGE_PREFERRED}}"
  local tar_path=""
  local removed_any=0
  local candidate=""

  tar_path="$(managed_root_base_image_tar_path "${managed_root}")"
  docker_cmd image inspect "${target_image}" >/dev/null 2>&1 || return 1

  for candidate in \
    "${tar_path}" \
    "${tar_path}.part" \
    "${tar_path}.part.aria2"
  do
    if [[ -e "${candidate}" ]]; then
      info "Base image ${target_image} already exists; removing cached download ${candidate}."
      rm -f "${candidate}"
      removed_any=1
    fi
  done

  if (( removed_any )) && [[ -d "${managed_root}/downloads" ]]; then
    rmdir "${managed_root}/downloads" 2>/dev/null || true
  fi

  return 0
}

compute_tree_hash() {
  local combined=""
  local file_path=""

  assert_command sha256sum
  for file_path in "$@"; do
    [[ -f "${file_path}" ]] || die "Cannot hash missing file: ${file_path}"
    combined+=$(sha256sum "${file_path}")
  done

  printf '%s' "${combined}" | sha256sum | awk '{print $1}'
}

container_image_context_hash() {
  compute_tree_hash \
    "${PROJECT_ROOT}/Dockerfile.nvblox_orbbec" \
    "${PROJECT_ROOT}/prepare_container_workspace.sh" \
    "${PROJECT_ROOT}/launch_nvblox.sh"
}

managed_fastdds_profile_path() {
  local managed_root="$1"
  printf '%s/%s/%s\n' "${managed_root}" "${FASTDDS_RUNTIME_DIR_RELATIVE}" "${FASTDDS_UDP_ONLY_PROFILE_FILENAME}"
}

enable_managed_fastdds_udp_runtime() {
  local managed_root="$1"
  local profile_path=""
  local profile_dir=""

  profile_path="$(managed_fastdds_profile_path "${managed_root}")"
  profile_dir="$(dirname "${profile_path}")"
  mkdir -p "${profile_dir}"

  cat > "${profile_path}" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<dds xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <profiles>
    <transport_descriptors>
      <transport_descriptor>
        <transport_id>udp_transport</transport_id>
        <type>UDPv4</type>
      </transport_descriptor>
    </transport_descriptors>
    <participant profile_name="udp_only_participant" is_default_profile="true">
      <rtps>
        <useBuiltinTransports>false</useBuiltinTransports>
        <userTransports>
          <transport_id>udp_transport</transport_id>
        </userTransports>
      </rtps>
    </participant>
  </profiles>
</dds>
EOF

  export FASTDDS_DEFAULT_PROFILES_FILE="${profile_path}"
  export FASTRTPS_DEFAULT_PROFILES_FILE="${profile_path}"
  export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
  info "Managed Fast DDS UDP-only profile: ${profile_path}"
}

log_ros_discovery_env() {
  info "ROS discovery env: RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset>} FASTDDS_DEFAULT_PROFILES_FILE=${FASTDDS_DEFAULT_PROFILES_FILE:-<unset>} FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE:-<unset>}"
}

assert_supported_platform() {
  local arch=""
  local model=""
  local runtime_description=""

  arch="$(dpkg --print-architecture 2>/dev/null || uname -m)"
  [[ "${arch}" == "arm64" || "${arch}" == "aarch64" ]] || die "Unsupported architecture: ${arch}. Jetson arm64 is required."

  [[ -f /etc/os-release ]] || die "Cannot detect OS version because /etc/os-release is missing."
  # shellcheck disable=SC1091
  source /etc/os-release
  [[ "${ID:-}" == "ubuntu" ]] || die "Unsupported OS: ${ID:-unknown}. Ubuntu 22.04 is required."
  [[ "${VERSION_ID:-}" == "22.04" ]] || die "Unsupported Ubuntu version: ${VERSION_ID:-unknown}. Ubuntu 22.04 is required."

  [[ -f /proc/device-tree/model ]] || die "Cannot detect Jetson model from /proc/device-tree/model."
  model="$(tr -d '\0' < /proc/device-tree/model)"
  [[ "${model}" == *"Jetson"* && "${model}" == *"Orin"* ]] || die "Unsupported device model: ${model}. Jetson Orin is required."

  assert_supported_jetpack_major 6
  runtime_description="$(describe_jetpack_runtime || true)"

  info "Platform OK: ${model}, Ubuntu ${VERSION_ID}, ${runtime_description:-JetPack 6.x}"
}

check_apt_locks() {
  local lock_path=""
  local pids=""

  if ! command -v fuser >/dev/null 2>&1; then
    warn "fuser is not available; skipping apt lock inspection."
    return 0
  fi

  for lock_path in /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock; do
    pids="$(fuser "${lock_path}" 2>/dev/null || true)"
    [[ -z "${pids}" ]] || die "apt/dpkg lock detected on ${lock_path} (pids: ${pids}). Resolve it before continuing."
  done
}
