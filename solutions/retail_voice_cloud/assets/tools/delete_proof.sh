#!/usr/bin/env bash
# 删除证明：拉起真的 MySQL + MinIO，造数据，取删除前后的 SHA-256 清单，
# 跑一次按主体删除，再核数据库、对象存储、本地文件三处，输出残留数与耗时。
#
# spec §4 要求「删除后同时核文件系统、数据库、对象存储/备份，输出残留数与完成时间」。
# 三处都要真的：用内存假替身证明不了对象存储里没东西。
#
# 用法：
#   tools/delete_proof.sh            # 起依赖 → 跑证明 → 拆依赖
#   KEEP_DEPS=1 tools/delete_proof.sh  # 保留容器便于排查
#
# 只碰本脚本自己创建的容器（前缀 c4-proof-），不动任何既有编排。
set -euo pipefail

# zsh 是本机默认 shell，但本脚本用 bash 的 set -o pipefail 与数组，
# 因此显式走 bash。macOS 自带 bash 3.2 也能跑：没有用 associative array。

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MYSQL_CONTAINER=c4-proof-mysql
MINIO_CONTAINER=c4-proof-minio
NETWORK=c4-proof-net

MYSQL_PORT=${MYSQL_PORT:-13306}
MINIO_PORT=${MINIO_PORT:-19000}
MYSQL_ROOT_PW=proofpw
MYSQL_DB=voice_c4
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_BUCKET=voice-c4

GO_IMAGE=${GO_IMAGE:-golang:1.24}
LOCAL_AUDIO_DIR=$(mktemp -d "${TMPDIR:-/tmp}/c4-proof-audio.XXXXXX")

cleanup() {
  if [ "${KEEP_DEPS:-0}" = "1" ]; then
    echo "KEEP_DEPS=1，保留容器：$MYSQL_CONTAINER $MINIO_CONTAINER"
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
  -p "${MYSQL_PORT}:3306" mysql:8.0 \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci >/dev/null

docker run -d --name "$MINIO_CONTAINER" --network "$NETWORK" \
  -e MINIO_ROOT_USER="$MINIO_ROOT_USER" -e MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD" \
  -p "${MINIO_PORT}:9000" minio/minio:latest server /data >/dev/null

echo "== 2/5 等依赖就绪 =="
for i in $(seq 1 90); do
  if docker exec "$MYSQL_CONTAINER" mysqladmin ping -uroot -p"$MYSQL_ROOT_PW" --silent >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec "$MYSQL_CONTAINER" mysqladmin ping -uroot -p"$MYSQL_ROOT_PW" --silent >/dev/null

for i in $(seq 1 60); do
  if docker run --rm --network "$NETWORK" curlimages/curl:latest \
      -sf "http://${MINIO_CONTAINER}:9000/minio/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "== 3/5 建 bucket =="
docker run --rm --network "$NETWORK" --entrypoint sh minio/mc:latest -c "
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
