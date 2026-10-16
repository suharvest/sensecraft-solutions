#!/usr/bin/env bash
# ==============================================================================
# switch_language.sh - Turnkey language switcher for SenseCraft Xiaozhi Voice
# Supports: en (English) / zh (Chinese) / status (Check current language mode)
# ==============================================================================

set -euo pipefail

TARGET_LANG="${1:-${LANGUAGE:-}}"
TARGET_LANG_LOWER=$(echo "${TARGET_LANG}" | tr '[:upper:]' '[:lower:]')

# --- 1. Locate Workspace and Configuration Path ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${SCRIPT_DIR}/data/.config.yaml" ]]; then
    BASE_DIR="${SCRIPT_DIR}"
elif [[ -f "${SCRIPT_DIR}/xiaozhi_console_deploy/data/.config.yaml" ]]; then
    BASE_DIR="${SCRIPT_DIR}/xiaozhi_console_deploy"
elif [[ -f "${HOME}/xiaozhi_voice/xiaozhi_console_deploy/data/.config.yaml" ]]; then
    BASE_DIR="${HOME}/xiaozhi_voice/xiaozhi_console_deploy"
elif [[ -f "${HOME}/xiaozhi_voice/data/.config.yaml" ]]; then
    BASE_DIR="${HOME}/xiaozhi_voice"
else
    BASE_DIR="${XIAOZHI_DIR:-.}"
fi

CONFIG_FILE="${BASE_DIR}/data/.config.yaml"
MYSQL_PWD="${MYSQL_ROOT_PASSWORD:-123456}"
SPECIFIED_AGENT_ID="${AGENT_ID:-}"

function show_usage() {
    echo "Usage: $0 [en|zh|status] [--agent <id>]"
    echo "  en     - Switch to Pure English mode (English prompt, English TTS, 'Checking...' filler)"
    echo "  zh     - Switch to Chinese mode (Chinese prompt, Chinese TTS, '正在查询。' filler)"
    echo "  status - Show current language configuration"
    exit 1
}

function run_mysql() {
    docker exec xiaozhi-esp32-server-db mysql -uroot -p"${MYSQL_PWD}" --default-character-set=utf8mb4 "$@"
}

# --- 2. Preflight Health Checks ---
function preflight_check() {
    for container in xiaozhi-esp32-server-db xiaozhi-esp32-server-redis xiaozhi-server; do
        if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            echo "Error: Required container '${container}' is not running." >&2
            exit 1
        fi
    done

    if [[ ! -f "${CONFIG_FILE}" ]]; then
        echo "Error: Configuration file not found at: ${CONFIG_FILE}" >&2
        exit 1
    fi
}

# --- 3. Resolve Target Agent ID ---
function resolve_agent_id() {
    if [[ -n "${SPECIFIED_AGENT_ID}" ]]; then
        echo "${SPECIFIED_AGENT_ID}"
        return 0
    fi

    # Strategy 1: Find agent from bound device
    local agent_id
    agent_id=$(run_mysql -sN -e \
        "USE xiaozhi_esp32_server; SELECT agent_id FROM ai_device WHERE agent_id IS NOT NULL AND agent_id != '' LIMIT 1;" 2>/dev/null || true)
    
    # Strategy 2: Find the most recently updated agent
    if [[ -z "${agent_id}" || "${agent_id}" == "NULL" ]]; then
        agent_id=$(run_mysql -sN -e \
            "USE xiaozhi_esp32_server; SELECT id FROM ai_agent ORDER BY updated_at DESC LIMIT 1;" 2>/dev/null || true)
    fi

    if [[ -z "${agent_id}" || "${agent_id}" == "NULL" ]]; then
        echo "Error: Could not resolve a valid agent ID from database. Set AGENT_ID=<id> explicitly." >&2
        exit 1
    fi

    echo "${agent_id}"
}

function show_status() {
    preflight_check
    local agent_id
    agent_id=$(resolve_agent_id)

    echo "=== Current Language Configuration ==="
    echo "Resolved Agent ID: ${agent_id}"
    echo -n "Database TTS language: "
    run_mysql -sN -e \
        "USE xiaozhi_esp32_server; SELECT JSON_UNQUOTE(JSON_EXTRACT(config_json, '$.language')) FROM ai_model_config WHERE id = 'TTS_OpenVoiceStream';" 2>/dev/null || echo "Unknown"
    
    echo -n "Database Agent language: "
    run_mysql -sN -e \
        "USE xiaozhi_esp32_server; SELECT language FROM ai_agent WHERE id = '${agent_id}';" 2>/dev/null || echo "Unknown"
    
    echo -n "Tool call filler: "
    grep -E '^\s*tool_call_filler:' "${CONFIG_FILE}" 2>/dev/null || echo "None"
    echo "======================================"
}

if [[ -z "${TARGET_LANG}" ]]; then
    show_usage
fi

case "${TARGET_LANG_LOWER}" in
    status)
        show_status
        exit 0
        ;;
    en|english)
        MODE="en"
        LANG_NAME="English"
        LANG_CODE="en"
        AGENT_NAME="Warehouse Assistant"
        FILLER="Checking..."
        ;;
    zh|chinese|cn)
        MODE="zh"
        LANG_NAME="中文"
        LANG_CODE="zh"
        AGENT_NAME="仓管助手"
        FILLER="正在查询。"
        ;;
    *)
        echo "Error: Unknown language mode '${TARGET_LANG}'"
        show_usage
        ;;
esac

preflight_check
TARGET_AGENT_ID=$(resolve_agent_id)

echo "[*] Switching Xiaozhi Voice to: ${LANG_NAME} (${MODE}) for Agent [${TARGET_AGENT_ID}]..."

# 1. Update Database (TTS Model Config)
echo "[1/5] Updating TTS model language in database..."
run_mysql -e "
USE xiaozhi_esp32_server;
UPDATE ai_model_config 
SET config_json = JSON_SET(config_json, '$.language', '${LANG_NAME}') 
WHERE id = 'TTS_OpenVoiceStream';
"

# 2. Update Database (Agent Profile and System Prompt)
echo "[2/5] Updating agent profile and system prompt..."
if [[ "${MODE}" == "en" ]]; then
    PROMPT="You are a warehouse smart assistant responsible for checking inventory, locating materials, and managing warehouse stock.
Speak concisely, directly, and in a friendly tone.

## CRITICAL MANDATORY INSTRUCTION: PURE ENGLISH ONLY
You MUST speak, reply, and generate all verbal output ONLY in ENGLISH.
NEVER speak or reply in Chinese under any circumstances.
Even if the user speaks Chinese, or the warehouse tool returns Chinese text (such as \"say\" or product candidate names), you MUST translate all information and answer strictly in English.

## Core Rules & Inventory Actions
1. **Always Call Tools to Query Inventory**:
   When asked about inventory, material location, or stock count, you MUST call the query_stock or search tool.
   Never guess or invent numbers or locations from memory.

2. **ASR Phonetic Correction**:
   Speech recognition often mishears technical terms. You must normalize them to the official material name when calling tools:
   - \"Jetson Orange Annex\", \"Jetson Orange\", \"Jetson Orin the NEX\", \"Justin Oliver Ancel\", \"Jepsen Oriental\", \"Jiacheng Aolin\" -> product_name: \"Jetson Orin NX\"
   - \"CM4\", \"Raspberry Pi\" -> product_name: \"Raspberry Pi CM4\"

3. **Accurate Data Presentation**:
   - Quote exact numbers and locations returned by the tool.
   - Example when found: \"Jetson Orin NX 16G current stock is 4 units, located at E1-02.\"
   - Example when candidates returned: \"I found similar products: Jetson Orin NX 16G (ELC-ORNX16) and Jetson Orin NX 8G. Which one do you mean?\"
   - Example when not found: \"Sorry, could not find any inventory record for this item in the system.\"
4. **No Stock Movement without Tool**:
   Only confirm stock in/out if stock_in/stock_out tool was called and returned executed=true."

    run_mysql -e "
    USE xiaozhi_esp32_server;
    UPDATE ai_agent SET
        agent_name = '${AGENT_NAME}',
        language = '${LANG_NAME}',
        tts_language = '${LANG_NAME}',
        lang_code = '${LANG_CODE}',
        system_prompt = '${PROMPT}'
    WHERE id = '${TARGET_AGENT_ID}';
    "
else
    PROMPT="你是仓管助手，仓库智能助手，负责帮用户查询库存、查找物料位置、处理出入库操作。
说话简短直接，语气轻松友好。

## 核心行为与数据铁律
1. **查库存必调工具**：当用户询问库存、物料位置或批次时，必须调用 query_stock 或 search 工具查询，严禁凭记忆编造。
2. **语音识别同音词纠错**：听到以下及类似谐音词时，转换为正确的物料关键词调用工具：
   - 听到「Jetson Orin the NEX」、「Justin Oliver Ancel」、「Jetson Orange」、「嘉诚奥林」、「嘉诚奥林N叉」等 → product_name 转为 \"Jetson Orin NX\"
   - 听到「CM4」、「四代模组」 → product_name 转为 \"树莓派 CM4\"
3. **数字原样引用**：库存数量、位置、批次等必须与工具返回的真实数值一致，禁止推算或凑整。
   - 查到结果时按工具返回播报，例如：\"Jetson Orin NX 16G 当前库存 4 块，位于 E1-02。\"
   - 多个相似候选时提示确认，例如：\"我找到几个相似产品：Jetson Orin NX 16G（ELC-ORNX16）。请问您具体指的是哪一个？\"
   - 未查到时回复：\"抱歉，系统中未找到该物料的库存记录。\"
4. **没调工具就没有出入库**：宣布「已出库/已入库」的唯一依据是本轮真实调用了 stock_out/stock_in 且响应里 executed=true。"

    run_mysql -e "
    USE xiaozhi_esp32_server;
    UPDATE ai_agent SET
        agent_name = '${AGENT_NAME}',
        language = '${LANG_NAME}',
        tts_language = '${LANG_NAME}',
        lang_code = '${LANG_CODE}',
        system_prompt = '${PROMPT}'
    WHERE id = '${TARGET_AGENT_ID}';
    "
fi

# 3. Update data/.config.yaml tool_call_filler
echo "[3/5] Updating tool_call_filler in .config.yaml..."
if grep -q "tool_call_filler:" "${CONFIG_FILE}"; then
    sed -i "s/tool_call_filler:.*/tool_call_filler: \"${FILLER}\"/" "${CONFIG_FILE}"
else
    echo "tool_call_filler: \"${FILLER}\"" >> "${CONFIG_FILE}"
fi

# 4. Invalidate Redis Model Cache
echo "[4/5] Clearing Redis cache..."
docker exec xiaozhi-esp32-server-redis redis-cli del 'model:data:TTS_OpenVoiceStream' > /dev/null

# 5. Restart xiaozhi-server to apply changes
echo "[5/5] Restarting xiaozhi-server and verifying health..."
docker restart xiaozhi-server > /dev/null

# Quick check that container remains running
sleep 2
if ! docker ps --format '{{.Names}}' | grep -q "^xiaozhi-server$"; then
    echo "Error: xiaozhi-server container failed to restart." >&2
    exit 1
fi

echo "[✓] Successfully switched to ${LANG_NAME} (${MODE}) mode!"
show_status
