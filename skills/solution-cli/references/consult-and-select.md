# 方案咨询与场景匹配手册 (Consult & Select Guide)

> **定位**：供 AI Agent 在用户处于 **场景探索（DISCOVERY）** 或 **方案咨询（CONSULT）** 时查阅。当用户询问“我想做某某事情”、“有什么物联网方案”、“如何解决 XX 问题”时，使用本手册定位场景、推荐参考设计并对齐硬件族。

---

## 1. 意图识别与场景路由规则

当用户的自然语言输入包含以下关键词时，直接调用 CLI 工具查询相关场景：

| 行业领域 | 触发关键词（中英文） | 对应场景 Slug | 核心参考设计 |
|---|---|---|---|
| **智慧养老 / 监护** | 养老、跌倒检测、防摔、老人、呼叫、fall detection, elderly | `elderly-care-monitoring` | `fall_detection` |
| **智慧农业 / 环境** | 农田、大棚、温湿度、气象、土壤、agriculture, soil, greenhouse | `environment-monitoring` | `agri_env_monitor` |
| **工业质检 / 缺陷** | 缺陷检测、工业视觉、表面划痕、流水线装配、visual inspection, defect | `industrial-visual-inspection` | `edge_inspection_surface`, `edge_inspection_assembly` |
| **智慧交通 / 园区** | 车牌识别、停车场、车辆计数、停车位、anpr, license plate, parking | `parking-traffic-vision` | `edge-anpr-plate-recognition` |
| **边缘语音 / 助手** | 离线语音、大模型音箱、呼救感知、voice ai, audio assistant, respeaker | `conversational-voice-ai` | `home-assistant-local-voice-hub`, `conversational_voice_ai` |
| **建筑能耗 / 暖通** | 楼宇能耗、电表、水表、空调节能、HVAC, energy retrofit | `building-energy-retrofit` | `building_energy_management` |
| **室内外定位 / 资产** | 蓝牙信标、资产定位、人员卡片、防丢、GNSS, tracker, beacon, T1000 | `indoor-outdoor-positioning` | `indoor_positioning_ble_lorawan` |

客户询盘、客户需求分析、方案选型、如何回复客户或“我们能提供什么”也属于咨询路由；涉及楼宇温控、恒温器、温度/湿度/空气质量传感器等需求时，先用客户原话和关键技术词搜索方案库。若搜不到匹配结果，明确说明官方方案库缺少现成能力，再给出需定制验证的边界；不要把通用 IoT 能力编造成已有的 thermostat 硬件或现成方案。

---

## 2. 工具调用标准动作

### 动作一：搜索场景与参考设计
使用命令：
```bash
solution-cli hub search "<用户关键词>" --limit 5 --json
solution-cli hub get <chosen-id> --locale <en|zh|ja> --section overview --json
solution-cli hub get <chosen-id> --locale <en|zh|ja> --section links --json
```
- **咨询顺序**：先用用户原话和同义技术词查询，再对选中的 Scenario、Tech 或 RD 调用 `hub get`；只有需要回答架构、产品或部署问题时，才追加 `--section architecture|products|deployment`。根据返回的 `diagnostic_playbook` 拆解需求；向用户确认点位、协议、供电、通信、控制闭环和预算等关键参数后，给出可提供的方案、硬件方向和缺口说明。
- **内容核验**：链接或 metadata 只用于定位，不代表已经阅读内容。用户问方案能力、架构或产品时，必须读取选中记录对应的 `description`、`architecture` 或 `products` section；确切生产页或架构图影响答案时，再打开 CLI 返回的确切 URL/图片并说明核验范围。相对资源路径只有在签名本地内容实际存在时才可读取，否则标为 source asset 未就绪。
- **交付边界**：咨询阶段只做检索、需求澄清和方案建议，不自动执行 `deploy`；用户确认硬件和部署目标后，再转入硬件校验或部署流程。
- **输出结果说明**：
  - `Scenario`：业务场景、痛点、所属 Tech/RD 关系、生产落地页链接；
  - `Tech`：独立技术/归属页及其明确关联的 Scenario/RD；不要把 Tech 当作 Wiki 或 RD；
  - `Reference Design`：具体架构、产品说明、部署文档/预设、生产落地页和已声明的 Wiki/源码链接；只有存在部署映射时才称为可部署；
  - `family_ids`：推荐的主板/相机/网关产品族。

### 动作二：识别页面归属与可部署映射

页面关系按 `Scenario → Tech / Reference Design` 的显式关系读取。落地页
是业务入口，技术页是独立内容归属，RD 是具体设计；不要根据标题、slug
或同名关系补出边。每个 RD 的一键部署入口都对应一个部署文档和 preset
映射。先读取：

```bash
solution-cli hub get <rd-id> --locale <en|zh|ja> --section architecture --json
solution-cli hub get <rd-id> --locale <en|zh|ja> --section products --json
solution-cli hub get <rd-id> --locale <en|zh|ja> --section deployment --json
```

架构内容只把明确标注为 architecture 的图或 tab 称为架构图；其他图片
保留为 gallery。产品说明、BOM、架构图和部署文档要标明内容语言与来源。
`deployment` 返回的是目录中的部署映射，不等于本机已经安装；实际执行
前必须用 Engine 查询该映射的真实 `solution_id`：

```bash
sensecraft-engine deploy-info <solution-id> --lang <en|zh>
```

生产落地页按请求语言直接使用 CLI 返回的 URL。当前生产域名是英文
`www.seeed.cc`、中文 `www.seeedstudio.com.cn`、日文 `www.seeed.co.jp`；
不要把三者统一替换成另一个域名，也不要自行拼接 `/wiki` 或资产 CDN
路径。Wiki 只有在返回的已发布/授权元数据中存在时才展示。

### 动作三：呈现官方架构图与可编辑拓扑 (Architecture Presentation & Mermaid)

当方案检索或通过 `hub get <id> --section architecture` 匹配到方案包含官方架构图时（数据中包含 `architecture_preview` 或 `architecture.image_url`/`architecture.intro`）：
1. **推荐并呈现官方参考架构图**：在向用户回复方案介绍时，直接嵌入官方高清参考架构图的 Markdown 引用：
   ```markdown
   ![<方案名称>架构图](<image_url>)
   ```
   向用户说明这是经过官方实测验证的标准拓扑结构与设备选型。
2. **生成可二次编辑的通用 Mermaid 拓扑**：基于架构图返回的拓扑摘要（`summary`）与连接关系，紧随其后生成一份结构清晰的 Mermaid 流程图（`flowchart LR`）：
   - 按分层划分子图（`subgraph`）：采集现场（Sensor/Camera/Mic）、边缘算力与主机（Edge Host/Gateway）、平台管理与应用（Cloud/Platform/Web Console）；
   - 在连线上准确标注通信介质与协议（如 USB、RTSP、MQTT、HTTP、BLE、LoRaWAN、Modbus）；
3. **主动提示可修改定制**：说明“此拓扑为官方基准设计；若现场有特殊工况（如由云端改为纯局域网离线、更换通信总线、接入已有摄像头/传感器），可直接基于该 Mermaid 流程图调整修改”，方便用户或方案人员快速二次编辑。

---

## 3. 现场工况诊断与场景提问知识库 (Domain Diagnostic Playbook)

> [!IMPORTANT]
> **拒绝自说自话！真正的方案专家不仅回答问题，更主动诊断现场工况。**
> 当用户提出场景诉求时，先调用 `solution-cli hub search "<关键词>" --json`。如果选中的返回记录带有 `diagnostic_playbook`，可以使用其中的问题；当前 CLI 的 compact search 结果可能不带该字段，此时使用本节矩阵，并明确这是通用工程核查。
> Agent **必须结合可用的工况诊断信息，主动提出 2~3 个决定物理架构、通信链路与商务成本的关键问题**，并解释“为什么问这个问题”（如利旧省钱、避免停机、规避环境干扰）。

### 3.1 四大底层工程决断杠杆 (The 4 Engineering Levers)

无论面对何种行业场景，所有诊断追问均围绕以下 4 个决定硬件选型与系统拓扑的核心杠杆展开：

| 工程决断杠杆 | 核心影响与决断依据 | 典型追问切入点 |
|---|---|---|
| **1. 物理拓扑分布**<br>(集中式 vs 分布式) | 决定是采用“1 台计算主机集中拉流/汇聚”（极度摊薄单点算力成本），还是“分布式独立一体化终端”（免拉长线、点位隔离）。 | “点位是在同一栋楼/同一车间集中分布，还是分散在多处？” |
| **2. 存量资产利旧**<br>(绿地新建 vs 棕地利旧) | 决定能否在协议、带宽、供电和性能满足时复用客户现有的监控摄像头（RTSP/ONVIF）、传感器（RS485/Modbus）或 PLC；具体节省量必须基于现场清单核算。 | “现场是否已经有现成的摄像头/传感器？支持什么协议？” |
| **3. 供电与通信边界**<br>(市电 vs 电池 / 有线 vs 无线) | 决定供电配件（220V 电源适配器 vs 太阳能/电池休眠机制）以及网络介质（PoE 网线、Wi-Fi、4G 插卡、LoRaWAN 远距离低功耗）。 | “安装点是否有 220V 市电？是否方便布设网线（PoE）？” |
| **4. 业务执行与闭环联动**<br>(被动看板 vs 主动控制) | 决定硬件接口规格（是否需要工业隔离数字量 I/O、继电器触点、CAN 总线）以及告警延迟容忍度。 | “判定异常后，是仅在大屏/手机告警，还是需直接联动 PLC/气缸/道闸执行控制？” |

---

### 3.2 各大行业场景工况诊断速查表 (Scenario Diagnostic Matrix)

当用户询问特定领域时，Agent 查阅下表或提取 CLI 返回的 `diagnostic_playbook` 发起专业诊断：

| 行业领域与场景 ID | 核心工况关注点 | 推荐诊断追问 (2~3 问) | 追问背后的技术与商务决断理由 (Rationale) |
|---|---|---|---|
| **智慧养老 / 监护**<br>`elderly-care-monitoring` | • 空间集中还是分散<br>• 存量摄像头利旧<br>• 卫生间/卧室隐私顾虑 | 1. 房间是在同一栋楼集中分布，还是分散在各栋楼？<br>2. 现场公共区域是否已有海康/大华等 RTSP 监控摄像头？<br>3. 卫生间、卧房等私密区域是否介意纯光学镜头，是否需毫米波雷达？ | 集中可用 1 台 reComputer 拉多路流摊薄成本；已有摄像头直接利旧节省采购预算；私密空间用 60GHz 毫米波雷达替代相机彻底规避隐私风险。 |
| **智慧农业 / 微气象**<br>`environment-monitoring` | • 连栋温室 vs 广域农田<br>• 220V 市电 vs 太阳能/电池<br>• 空气微气象 vs 土壤剖面水肥 | 1. 监测区域是集中式温室大棚（百米级），还是大面积大田/果园（数公里级）？<br>2. 测点安装位置是否有市电，还是需野外太阳能/电池长续航？<br>3. 核心监测指标是什么（仅空气温湿度/光照，还是需土壤剖面水肥水分/EC/pH）？ | 大棚百米级可用 RS485 总线；广域农田必须用 LoRaWAN 远距低功耗网关（SenseCAP M2）；野外无电需选配超低功耗休眠传感器节点；水肥指标需搭配工业级土壤传感器。 |
| **工业视觉质检 / 缺陷**<br>`industrial-visual-inspection` | • 流水线节拍与飞拍<br>• 工件表面反光与材质<br>• PLC 剔除信号闭环 | 1. 流水线节拍如何（每分钟过检多少件，工件是静止还是运动中飞拍）？<br>2. 工件表面是反光金属/镜面塑料还是漫反射纸盒？缺陷精度在什么毫米级？<br>3. 检测出不良品后，边缘设备是否需直接向 PLC/气缸发送数字量剔除信号？ | 运动飞拍必须选用全局快门相机与高 TOPS Jetson（Orin NX）；反光金属表面需定制偏光/同轴光源消除眩光；剔除联动需配置带工业隔离 I/O 的工控机型。 |
| **智慧交通 / 园区道闸**<br>`parking-traffic-vision` | • 出入道闸 vs 主干道行驶<br>• 夜间强光抑制与补光<br>• 本地继电器开闸联动 | 1. 抓拍点是低速出入口道闸（1~2车道），还是园区主干道（中高速行驶中抓拍）？<br>2. 夜间或出入口逆光环境如何？是否有充足照明或需强光抑制补光？<br>3. 车牌识别后，是边缘主机直接短接继电器起杆，还是上报停车计费软件？ | 道闸场景普通高帧率相机即可，干道需全局快门与高速跟踪模型；大灯直射需强光抑制爆闪补光；本地开闸需硬件隔离继电器配件并支持离线脱机白名单。 |
| **现场语音控制 / 助手**<br>`conversational-voice-ai` | • 声学噪声与拾音距离<br>• 100% 离线脱网 vs 云端大模型<br>• 下位机受控设备协议 | 1. 现场使用环境噪音如何（安静室内还是背景嘈杂机器轰鸣）？拾音距离多远？<br>2. 对网络和隐私是否有硬性要求？必须 100% 离线断网还是可以联网调用大模型？<br>3. 语音识别或大模型理解后，主要用来控制什么设备（Home Assistant、MQTT 还是串口继电器）？ | 嘈杂远场（3~5米）必须配置带硬件 DSP/AEC/波束成形的 ReSpeaker XVF3800；纯离线需 Orin NX 跑端到端小模型（Whisper+LLM+TTS），混合模式可用轻量机做拾音。 |
| **旧建筑节能改造 / 暖通**<br>`building-energy-retrofit` | • 存量表计通信接口<br>• 配电室集中 vs 跨楼层分布<br>• 纯能耗抄表 vs 空调闭环控制 | 1. 现场电表/水表/空调是否自带 RS485（Modbus/DLT645）通信接口，还是老旧机械表？<br>2. 表计集中在配电机房，还是分散在各楼层强电井？楼层间有无预埋网线？<br>3. 仅做能耗数据上报与统计，还是需根据用电策略反向控制空调启停回路？ | 带 485 接口可直接低成本总线抄表；跨楼层分散无布线推荐 SenseCAP LoRaWAN 采集器无线回传免穿墙打洞；闭环控制需配置带工业继电器与模拟量输出的网关。 |
| **室内外定位 / 资产人员**<br>`indoor-outdoor-positioning` | • 纯室内 vs 室内外混合<br>• 米级具体坐标 vs 区域货架级<br>• 佩戴工牌卡片 vs 货物免维护长续航 | 1. 定位场景是纯室内（厂房/展厅），还是室内外混合（仓库到室外堆场/物流转运）？<br>2. 对定位精度的期望是精确到米级的坐标，还是只需知道在哪个房间/货架区域？<br>3. 被追踪对象是人员佩戴工牌，还是贴在货物托盘上？期望续航时间是多久？ | 纯室内基于 BLE 信标定位；室内外混合推荐 SenseCAP T1000 追踪器（室内切蓝牙/Wi-Fi，室外切 GPS/北斗）；区域级可大幅精简基站数量，极节约成本。 |
| **现场控制与自动化**<br>`industrial-control-automation` | • 工控总线协议种类<br>• 电控柜 DIN 导轨与直流供电<br>• 实时控制毫秒级 vs 数据采集分析 | 1. 现场下位机主要采用什么总线协议（Modbus TCP/RTU、CANopen、PROFINET、EtherNet/IP）？<br>2. 是否安装在标准工业电控柜导轨上？现场供电是 DC 24V 还是 AC 220V？<br>3. 是需毫秒级实时控制闭环，还是做秒级/分级的数据采集与边缘分析诊断？ | 决定网关物理接口（隔离 RS485、双网口、CAN）与中间件；导轨安装与宽压输入匹配电控柜标准；实时控制需带 PREEMPT_RT 补丁控制器，采集可用常规工控机。 |

---

## 4. 推荐应答呈现规范（自然专家与诊断对话风格）

向用户作答时，采用流利、专业的对话口吻，涵盖以下要素：
1. **方案业务价值与实现逻辑**（直接讲透）：解释返回内容能证实的端侧处理、响应和隐私边界；没有实测或来源的性能数字不得补充；
2. **两类硬件架构对比**：说明一体机与工控机/Jetson 的各自适用场景；
3. **参数可调性预告**：只有在部署内容或管理接口返回 `reconfigurable` 字段时，才说明 MQTT 地址、检测灵敏度等参数支持在线修改；
4. **自然延伸出口**：随口附上“了解更多”落地页与技术 Wiki；若涉及二次开发提供 GitHub 源码；
5. **主动诊断追问（结合理由）**：提出针对该领域的 2~3 个工况诊断关键问题，并简明说明“为什么这样问能帮您优化方案或降低成本”。

#### 范例 1：智慧农业 / 环境监测咨询
> 做农业温室大棚和农田监测，推荐采用 **`agri_env_monitor`（农业环境监测方案）**。
>
> 当前目录中的 `agri_env_monitor` 可通过 `hub get --section deployment` 查看部署映射；实测返回 `cloud`、`tts_local`、`chirpstack_local` 三个 preset 和 `guide.md`/`guide_zh.md`，但其 RD 注册状态为 review，生产落地页链接为空。这表示可以继续读取目录中的部署内容进行诊断，不能把它当作已发布生产页面。架构和产品说明应分别读取 `--section architecture` 与 `--section products`。
>
> - **硬件组合**：大棚内部通常采用 **SenseCAP S2100 采集器 + 工业级土壤三参数探头（水分/EC/温度）**；如果需要户外微气象，可搭配 **S700 七合一气象站**。
> - **参数灵活性**：是否可在线修改要以实际部署内容返回的 `reconfigurable` 字段和管理接口为准。
>
> 💡 *如果想了解更多具体参数与传感器配件，先对选中的 RD 执行 `solution-cli hub get <rd-id> --locale <en|zh|ja> --section links --json`，使用返回的对应语言生产落地页和已声明的源码链接。不要从方案 ID 拼接网址。*
>
> ---
> **为了帮您设计最合理、施工最方便的硬件选型与网络拓扑，我想先了解几个现场工况：**
> 1. **空间覆盖范围**：监测区域是集中在几座相连的温室大棚内（百米级），还是大面积分布在户外大田或果园（数公里级）？（*集中大棚可用 RS485 有线总线节约成本；广域大田必须采用 LoRaWAN 远距离低功耗无线网关*）
> 2. **现场供电条件**：各个监测点是否有 220V 市电接口，还是在野外需要依赖太阳能电池板或自带大容量锂电池长续航运行？
> 3. **核心监测深度**：主要关注空气微气象（温湿度/光照/CO2），还是需要深入监测土壤剖面水肥墒情（如深层土壤水分/EC盐分/pH）？

#### 范例 2：工业流水线视觉质检咨询
> 做产线表面缺陷或装配防错质检，通常推荐采用 **`edge_inspection_surface`（工业表面缺陷边缘质检方案）**。
>
> 具体架构和推理链路必须读取选中 RD 的 `architecture` section；实测 `acoustic-audio-ai` Tech 记录返回 4 个架构模块，并带有明确的 architecture 图片 URL。当前 CLI 只把来源明确标注的模块或架构图作为架构内容，不从方案名称推断响应时间或输出闭环。
>
> - **硬件算力**：单工位常规线速可采用 **reComputer J3011 (Orin Nano 8GB)**；如果是高节拍复杂缺陷或多工位合并，推荐 **reComputer J4012 (Orin NX 16GB)**。
> - **接口与参数**：实测 `conversational_voice_ai` RD 的 `products` section 返回 6 个产品条目；是否支持热配置要以部署内容和管理接口的实际字段为准，不从示例文案推断。
>
> 💡 *更多机械安装与光学镜头打光指导，先对选中的 RD 执行 `solution-cli hub get <rd-id> --locale <en|zh|ja> --section links --json` 和 `--section architecture --json`，只使用返回的生产落地页、已发布 Wiki 和源码链接。*
>
> ---
> **为了确定相机快门、打光方案与工控机选型，我先跟您确认三个关键细节：**
> 1. **生产节拍与速度**：流水线每分钟过检多少件产品？工件经过工位时是短暂静止停顿拍照，还是在传送带上高速连续运动？（*运动中飞拍必须选用工业全局快门相机以避免拖影*）
> 2. **工件材质与反光**：工件表面是什么材质（例如反光金属、高光塑料还是吸光纸盒）？想要检出的最小划痕/缺陷尺寸大概是多少毫米？（*反光工件需要配合特定偏光或同轴光源，否则会产生强烈眩光影响检测*）
> 3. **下位机联动**：判定出 NG 不良品后，边缘机是只需声光报警/屏幕标记，还是需要直接向现场 PLC 发送数字量 IO 信号联动气缸剔除？

---

## 5. 防幻觉与守则

1. **禁止编造方案**：如果 `solution-cli hub search` 返回为空，诚实告知用户官方方案库暂无现成参考设计，并基于通用 Jetson / 树莓派 Docker 能力提供定制建议。
2. **严禁在咨询期直接执行部署**：用户此时通常未采购或未连接硬件。应引导用户确认现场工况并进入【硬件选型与配件推荐】（查阅 `references/hardware-bom.md`）。
