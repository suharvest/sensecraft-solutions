# 硬件选型与配件推荐准则 (Hardware & BOM Guide)

> **定位**：供 AI Agent 在用户处于 **采购选型（PROCUREMENT）** 或 **BOM 验证（VERIFY_BOM）** 阶段查阅。当用户询问“需要买什么硬件”、“XX 主板需要配什么配件”、“电源/天线怎么选”时使用本手册。

---

## 0. 前置合规与目录核验（查 BOM 前必做）

1. **区域、AC 插头与射频频段（Region, AC Plug & RF Band）**：
   - 查配件或组装 BOM 前，**先锁定客户所在国家/地区**，并在查询配件/BOM 时传入 `--region <ISO>`（如 `US`、`DE`、`VN`、`CN`）。
   - 核对 AC 电源插头制式与 LoRaWAN 频段（如欧洲 `EU868`、北美 `US915`、越南 `VN` 等亚洲地区 `AS923`），**严禁发货插头或频段不匹配的地区版本**。
2. **海外客户语言参数（Overseas Locale）**：
   - 面向海外客户查询方案与产品时，命令传入 `--locale en`，确保 `landing_url` 使用 `.com` 国际站域名且 L2 架构图为英文版。
3. **目录时效性核验（Catalog Staleness）**：
   - 检查 CLI 返回中的 `freshness` 与 `warnings` 字段；若出现 `STALE`，先执行 `solution-cli catalog pull` 刷新本地目录（或明确标注快照滞后），再下结论，**不得在未刷新前断定产品不存在**。
4. **同族收敛与调试工具隔离（Same-Family Consolidation & Debug-Tool Separation）**：
   - 优先检查目标产品族的 `axes`（配置维度）与 `common_options`（通用选配件），在**同一产品族内收敛选型**，再考虑其他产品族或外部第三方件。
   - **调试/烧录工具**（如 `USB-CAN Analyzer`）必须与**运行态 BOM（Runtime BOM）**分列，避免混入量产单机清单。

---

## 1. 核心流程：主板 ➔ 必选配件 ➔ 选配传感器/增强件

为用户提供硬件采购清单时，必须严格区分：
1. **主运算单元（Host Platform）**：如 `recomputer_j40`、`recamera_pro`、`sensecap_m2_gateway`。
2. **必选配件（REQUIRED Accessories）**：**若缺少则系统物理上无法工作**（如：Super 款未配电源线、网关未配天线、工控机无输入电源端子）。
3. **选配配件（OPTIONAL Accessories）**：根据具体功能选配（如：存储 SSD、4G 蜂窝网卡、降噪麦克风阵列、云台支架）。

---

## 2. 工具调用标准命令

### 动作一：查询主设备规格与默认 SKU
```bash
solution-cli product query <family_id> [--locale en|zh|ja] --json
```
- 获取产品族名称、官方默认主 SKU、物理电气规格（电压、电流接口、M.2 槽位等）以及内置的 UTM 商城购买直达链接。
- 优先核对返回中的 `axes`、`common_options` 以及 `freshness` / `warnings`；海外客户传 `--locale en`。

### 动作二：查询经过验证的配件清单与批量加购链接
```bash
solution-cli product accessories <family_id> [--region <ISO>] [--locale en|zh|ja] --compact --json
```
- 锁定客户国家后传 `--region <ISO>`，确保返回匹配当地标准的 AC 电源插头与射频版本。
- 输出严格由确定性代码计算物理兼容性的配件清单：
  - `bundle_cart_url`：已自动将主机与必需配件打包的 Seeed 官方商城合并加购直达链接；
  - `REQUIRED` 列表：带必买技术原因（`reason`）、购买 SKU 与静默带 UTM 的直达链接；
  - `OPTIONAL` 列表：带周边传感器、通信模块、固态硬盘与购买链接；
  - **建议务必加 `--compact`**：去除底层冗余兼容性树，Token 消耗降低 70%。

### 动作三：验证物理配件兼容性
当用户提到已有某个第三方配件或自制电源/天线时：
```bash
solution-cli product verify-compatibility --host <family_id> --accessory "<用户配件描述>" --json
```

---

## 3. 六大物理兼容性硬红线（严禁大模型自行脑补）

Agent 严禁凭“常识”告知配件通用，必须遵循 CLI 评估结果并向用户讲透技术原因：

1. **供电 (Power Supply)**：
   - `recomputer_j40` / `j30` 必须满足 **19V 4.74A (90W)**，DC Jack 规格为 **5.5x2.5mm**（与普通 5.5x2.1mm 路由器插头不兼容，插不进或接触不良）；
   - USB-C 供电的设备（如 `recamera_2002`、`sensecap_watcher`），必须核对 PD 协议档位与最低电流。
2. **射频与天线 (RF Antenna)**：
   - 必须严格区分 **N 型（N-Type）** 与 **SMA**；
   - 室外网关多为 **N-Type Female（母头）**，天线必须选 **N-Type Male（公头，带针）**，若为 SMA 天线必须提醒用户加购 **N转SMA转接线（Pigtail Cable）**；
   - 频段必须对齐：欧洲选 `EU868`，北美选 `US915`，亚洲（如越南 `VN`）选 `AS923`；严禁发错地区频段与 AC 插头制式。
3. **M.2 扩展卡 (M.2 Key)**：
   - **Key-M**：仅用于 NVMe SSD（尺寸通常为 2280）；
   - **Key-E**：仅用于 WiFi / 蓝牙 / AI 加速卡（尺寸通常为 2230）；
   - 严禁建议用户把 Key-M SSD 插到 Key-E 槽位。
4. **以太网供电 (PoE)**：
   - 区分 `802.3af`（15.4W）与 `802.3at`（30W PoE+）。`reCamera Pro` 需保证交换机端口支持 802.3at。

---

## 4. 推荐呈现模板（自然专业风格）

向用户输出采购清单时，Agent 先讲清技术理由，链接自然附在 SKU 之后（自带 UTM 归因），不喧宾夺主：

```markdown
### 🛒 硬件采购清单建议（BOM）

#### 1. 主计算单元
- **产品型号**：reComputer J4012（NVIDIA Jetson Orin NX 16GB）
- **推荐 SKU**：`110110145` [Seeed 官方商城直达](https://www.seeedstudio.com/reComputer-J4012-p-5586.html?utm_source=sensecraft_agent&utm_medium=bom_recommendation&utm_campaign=recomputer_j40&utm_content=host_sku_110110145)

#### 2. 必需配件 (REQUIRED - 缺少系统无法物理通电开机)
- ⚠️ **19V 4.74A 电源适配器 (5.5x2.5mm)** (SKU: `313080684`)
  - 技术原因：本工控主机出厂裸机不带电源适配器，且接口为 5.5x2.5mm 大功率圆口，必须专门选配。
  - [购买电源适配器](https://www.seeedstudio.com/...utm_params...)
- ⚠️ **国标/美标 AC 三脚电源输入线** (SKU: `106990470`)

#### 3. 推荐选配 (OPTIONAL - 按需选购)
- **M.2 NVMe SSD 256GB** (SKU: `112990246`)：用于拉取 Docker 镜像与长期本地数据持久化。
- **reSpeaker 4 麦克风阵列** (SKU: `107990193`)：若需补充语音呼叫或声音事件感知。

#### 4. 🛒 一键批量合并采购 (Bundle Cart)
- **官方商城直达**：`[点击此处将主机与必需配件一键加购结算](${bundle_cart_url})`
  *(调用 `solution-cli product accessories <family> --json` 时直接提取 `bundle_cart_url` 输出给用户，点击即可一次性将主机及必需配件加入购物车，大幅缩短采购转化链路。国内用户提示通过天猫/淘宝 Seeed 官方店或代理商采购。)*

---
> 📦 硬件采购并收到后，只要通电并插上网线，随时对我说“设备已连接，开始部署”，我将直接为您全自动化完成环境配置与方案运行！
```

### 涉外与双语客户方案交付提示（Bilingual Customer Proposal）
- **双语交叉排版**：面向海外客户输出提案与 BOM 时，使用**客户语言 + 英文双语穿插格式**（Interleaved Bilingual Format），并搭配 `--locale en` 获取的**英文版 L2 架构图**。
- **交付前独立只读 QA**：发送给客户前，执行一轮**独立只读 QA 核验**（Independent Read-Only QA Pass），复核 `--region` 国家代码、AC 插头、LoRaWAN 频段、调试工具（如 `USB-CAN Analyzer`）与运行态 BOM 隔离、`landing_url` `.com` 域名及目录 `freshness`。
