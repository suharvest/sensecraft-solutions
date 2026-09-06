#!/usr/bin/env bash
# 删除证明：拉起真的 MySQL + MinIO，造数据，取删除前后的 SHA-256 清单，
# 跑一次按主体删除，再核数据库、对象存储、本地文件三处，输出残留数与耗时。
#
# spec §4 要求「删除后同时核文件系统、数据库、对象存储/备份，输出残留数与完成时间」。
# 三处都要真的：用内存假替身证明不了对象存储里没东西。
#
# 用法：
#   tools/delete_proof.sh            # 起依赖 → 跑证明 → 拆依赖
#   KEEP_DEPS=1 tools/delete_proof.sh  # 保留容器便于排查（端口仍只绑 127.0.0.1）
#
# 数据库与对象存储的口令每次运行随机生成，脚本里没有固定凭据；容器端口只绑
# 回环，同网段的机器连不上这两个容器。
#
# 只碰本脚本自己创建的容器（前缀 c4-proof-），不动任何既有编排。
set -euo pipefail

# zsh 是本机默认 shell，但本脚本用 bash 的 set -o pipefail 与数组，
# 因此显式走 bash。macOS 自带 bash 3.2 也能跑：没有用 associative array。

# 仓库根 = 往上找到第一个带 go.mod 的目录。
#
# 不能写死跳几级：这个脚本有两份位置不同的副本——仓库内的 tools/delete_proof.sh
# （一级）和方案包里的 assets/tools/delete_proof.sh（两级）。原来固定 "/.."，
# 从 assets/tools/ 运行时 REPO_ROOT 会停在 assets/，go test 报
# "go.mod file not found in current directory or any parent directory"。
# REPO_ROOT 也可以从环境变量显式指定，脚本被拷到别处时用。
if [ -n "${REPO_ROOT:-}" ]; then
  REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
else
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [ ! -f "$REPO_ROOT/go.mod" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
  done
fi

if [ ! -f "$REPO_ROOT/go.mod" ]; then
  echo "❌ 找不到 go.mod：从 $(dirname "${BASH_SOURCE[0]}") 一路往上都没有。" >&2
  echo "   这个脚本要在 sensecraft-voice-service 仓库内运行。方案包里的副本请先拷进仓库，" >&2
  echo "   或显式指定：REPO_ROOT=/path/to/sensecraft-voice-service $0" >&2
  exit 1
fi
if [ ! -d "$REPO_ROOT/pkg/controller/privacy" ]; then
  echo "❌ $REPO_ROOT 下没有 pkg/controller/privacy，删除证明的测试不在这个仓库里。" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ 找不到 docker：本脚本要拉起真的 MySQL + MinIO。" >&2
  exit 1
fi

echo "REPO_ROOT=$REPO_ROOT"
cd "$REPO_ROOT"

MYSQL_CONTAINER=c4-proof-mysql
MINIO_CONTAINER=c4-proof-minio
NETWORK=c4-proof-net

# 端口只绑回环。这两个容器持有一次性证明数据的读写权限，绑 0.0.0.0 会把
# MySQL 与 MinIO 暴露给同网段的任何人；证明流程里的所有访问都走 Docker 网络
# ($NETWORK) 的容器名，宿主端口只为人工排查保留，回环足够。
BIND_ADDR=127.0.0.1
MYSQL_PORT=${MYSQL_PORT:-13306}
MINIO_PORT=${MINIO_PORT:-19000}
MYSQL_DB=voice_c4
MINIO_BUCKET=voice-c4

# 凭据每次运行现生成，不写进仓库：这个脚本会被拷到开发机、CI、客户现场跑，
# 固定口令一旦提交就等于公开。openssl 在 macOS 与主流 Linux 上都自带；
# 没有它就回退到 /dev/urandom（zsh 与 macOS 自带 bash 3.2 都能跑，不用
# associative array 之外的现代特性）。
if command -v openssl >/dev/null 2>&1; then
  rand_hex() { openssl rand -hex "$1"; }
else
  echo "⚠️ 找不到 openssl，回退用 /dev/urandom 生成一次性口令。" >&2
  rand_hex() { head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'; }
fi
MYSQL_ROOT_PW=$(rand_hex 24)
MINIO_ROOT_USER=proof$(rand_hex 8)
MINIO_ROOT_PASSWORD=$(rand_hex 24)

# 公共镜像一律按 digest 固定，和方案包里的 compose 同一条规矩：tag 会漂，digest 不会。
# 取值方式：docker buildx imagetools inspect <repo>:<tag>（2026-09-06 取）
#   minio/minio      RELEASE.2025-09-07T16-13-09Z -> sha256:14cea493…
#   minio/mc         RELEASE.2025-08-13T08-35-41Z -> sha256:a7fe349e…
#   curlimages/curl  8.22.0                       -> sha256:58adaa4e…
#   mysql            8.0                          -> sha256:7dcddc01…（与本方案 compose 同一枚）
#   golang           1.24                         -> sha256:d2d2bc1c…
GO_IMAGE=${GO_IMAGE:-golang:1.24@sha256:d2d2bc1c84f7e60d7d2438a3836ae7d0c847f4888464e7ec9ba3a1339a1ee804}
LOCAL_AUDIO_DIR=$(mktemp -d "${TMPDIR:-/tmp}/c4-proof-audio.XXXXXX")

cleanup() {
  if [ "${KEEP_DEPS:-0}" = "1" ]; then
    echo "KEEP_DEPS=1，保留容器：$MYSQL_CONTAINER $MINIO_CONTAINER"
    echo "   端口只绑在 ${BIND_ADDR}（${BIND_ADDR}:${MYSQL_PORT} / ${BIND_ADDR}:${MINIO_PORT}），同网段访问不到。"
    echo "   口令是本次运行随机生成的，容器删掉即失效；排查完请手动清理："
    echo "     docker rm -f $MYSQL_CONTAINER $MINIO_CONTAINER && docker network rm $NETWORK"
    echo "     rm -rf $LOCAL_AUDIO_DIR"
    return
  fi
  docker rm -f "$MYSQL_CONTAINER" "$MINIO_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$LOCAL_AUDIO_DIR"
}
trap cleanup EXIT

echo "== 1/5 起依赖 =="
docker rm -f "$MYSQL_CONTAINER" "$MINIO_CONTAINER" >/dev/null 2>&1 || true
docker network rm "$NETWORK" >/dev/null 2>&1 || true
docker network create "$NETWORK" >/dev/null

docker run -d --name "$MYSQL_CONTAINER" --network "$NETWORK" \
  -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PW" -e MYSQL_DATABASE="$MYSQL_DB" \
  -p "${BIND_ADDR}:${MYSQL_PORT}:3306" \
  mysql:8.0@sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci >/dev/null

docker run -d --name "$MINIO_CONTAINER" --network "$NETWORK" \
  -e MINIO_ROOT_USER="$MINIO_ROOT_USER" -e MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD" \
  -p "${BIND_ADDR}:${MINIO_PORT}:9000" \
  minio/minio:RELEASE.2025-09-07T16-13-09Z@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e \
  server /data >/dev/null

echo "== 2/5 等依赖就绪 =="
for i in $(seq 1 90); do
  if docker exec "$MYSQL_CONTAINER" mysqladmin ping -uroot -p"$MYSQL_ROOT_PW" --silent >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec "$MYSQL_CONTAINER" mysqladmin ping -uroot -p"$MYSQL_ROOT_PW" --silent >/dev/null

for i in $(seq 1 60); do
  if docker run --rm --network "$NETWORK" \
      curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777 \
      -sf "http://${MINIO_CONTAINER}:9000/minio/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "== 3/5 建 bucket =="
docker run --rm --network "$NETWORK" --entrypoint sh \
  minio/mc:RELEASE.2025-08-13T08-35-41Z@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727 -c "
  mc alias set proof http://${MINIO_CONTAINER}:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} >/dev/null &&
  mc mb --ignore-existing proof/${MINIO_BUCKET} >/dev/null && echo bucket ready"

echo "== 4/5 跑删除证明 =="
mkdir -p "$LOCAL_AUDIO_DIR"
docker run --rm --network "$NETWORK" \
  -v "$REPO_ROOT":/src \
  -v "${HOME}/.cache/gomod-c4":/go/pkg/mod \
  -v "$LOCAL_AUDIO_DIR":/audio \
  -w /src \
  -e GOFLAGS=-mod=mod \
  -e GOPROXY="${GOPROXY:-https://goproxy.cn,direct}" \
  -e MYSQL_DSN="root:${MYSQL_ROOT_PW}@tcp(${MYSQL_CONTAINER}:3306)/${MYSQL_DB}?charset=utf8mb4&parseTime=True&loc=Local" \
  -e MINIO_ENDPOINT="${MINIO_CONTAINER}:9000" \
  -e MINIO_ACCESS_KEY="$MINIO_ROOT_USER" \
  -e MINIO_SECRET_KEY="$MINIO_ROOT_PASSWORD" \
  -e MINIO_BUCKET="$MINIO_BUCKET" \
  -e LOCAL_AUDIO_DIR=/audio \
  "$GO_IMAGE" \
  go test -tags integration -count=1 -v ./pkg/controller/privacy/ -run TestDeleteProof

echo "== 5/5 完成 =="
