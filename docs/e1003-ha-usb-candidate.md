# E1003 统一部署技术演示：默认免 API 密钥

候选位于 [`solutions/reterminal_e1003_ha`](../solutions/reterminal_e1003_ha/solution.yaml)，
分类 `technical`，保持 `enabled: false`。一个部署入口、一张表单、一次提交：自动检查固件、
按需安装，再保存网络与灯光绑定。默认 `encrypt_api=false`，可选启用加密；真实 HA 控灯、
触摸与动态屏幕同步仍待验收。

## 当前版本与资源

- [固件 PR #2](https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/pull/2)：
  `a7116ee153158505faeec225d691c0cdef85a6da`，release `0.2.0`，
  project `love4yzp.e1003-dashboard`，profile `e1003-release.yaml`。
- Factory **1,377,472 bytes**，SHA-256
  `45cbf1ec46d5a00e8362e6d920cd9318841c58f2a081cfae809d9e38e64ccebb`。
  [清单](../solutions/reterminal_e1003_ha/assets/firmware/manifest.json) 与烧录模板同步；无公网下载地址，Git 不含 `.bin`。
- [App 草稿 PR #162](https://github.com/suharvest/app_collaboration/pull/162)：`68328f90`，contract 13。
  公开内容契约仍为 5；保留三个人工 review 阶段和最终 verify，不加入当前 schema 不认识的执行类型。
  人工步骤返回成功不能证明设备 I/O。同步 13 后才替换为单一原生执行入口，不新增套餐。

[`stage_e1003_candidate.py`](../scripts/stage_e1003_candidate.py) 只按白名单和真实 size/SHA
准备禁用的作者审阅副本，不部署设备或配置密钥。用法见[资源说明](../solutions/reterminal_e1003_ha/assets/firmware/README.md)。

## 默认模式与可选加密

| 项目 | 当前行为 |
| --- | --- |
| 默认 | `encrypt_api=false`，ESPHome native API 不使用 API 密钥；无需为默认接入生成/复制 key |
| 保存的 Wi-Fi | 字段留空可复用设备现有网络，不要求本机已保存 key/恢复记录；首次联网仍填 Wi-Fi |
| 加密可选 | 勾选“启用 API 加密（可选）”后生成或复用设备独立 key；仅完成加密验证才显示复制按钮 |
| 已加密设备关闭加密 | 用原私有恢复 key 授权清除；免密重连成功后才从记录删除 `api_key`，不擦 NVS |
| 旧 key 缺失 | 无法授权清除既有加密时停止；不能删记录、降级失败或擦 NVS 来绕过 |
| 持久化 | 最后写入后通电至少 65 秒，再复位、按所选模式读回；RAM 读回不能代替落盘 |

0.2.0 移除初始 10 分钟 API provisioning timer，并关闭等待 API 客户端触发的 reboot。
这是配置和源码结论；**十分钟后免密实机复查尚未完成**。不能把 0.1 的加密初始窗口或
零 key 机制当作当前默认。启用可选加密时仍保留安全生成与恢复约束。

## 自动固件检查与版本约束

前端传 `solution_id`，后端加载方案 canonical manifest；用户不填写镜像路径或选择是否烧录。

| 阶段 | 行为 |
| --- | --- |
| 身份 | Improv project=`love4yzp.e1003-dashboard`、version=`0.2.0`、hardware=`ESP32-S3`、name 匹配 `reterminal-e1003-[0-9a-f]{6}`；全部匹配才跳过 |
| 错误 | 串口不可访问或明确硬件不符时停止，不解释成安装许可 |
| 安装 | 镜像 size/SHA 校验后，通过捆绑 esptool Python API 写 `0x0`、`verify_flash`；再读身份，通过才配置 |
| 配置 | 同一任务设置网络/灯光/所选 API 模式、等待保存、复位读回；串口租约覆盖完整流程 |

115200、`dio`、`80m`、4 MB 布局、`erase=false` 不变；设备实物 32 MB 不能作为改分区依据。
NVS `0x3a0000` 不在这份 merged image 范围内；不全片擦除，不把出厂恢复当更新，无 OTA。
未来不同构建必须更改固件 `project.version` 并同步 manifest 的 version/size/SHA。
跳过分支不读取设备镜像哈希，禁止同一 project/version 对应不同构建；内容版本不能替代固件版本。

## 实际输入到执行路径

| 输入 | 执行与边界 |
| --- | --- |
| USB 端口 | 独占 UART0 115200，WCH 显式 reset/启动等待；不抢其他会话串口 |
| Wi-Fi 名称/密码 | 填写时经 Improv RPC 1；留空时等待设备现有网络；密码不进 argv 或普通导出配置 |
| 按钮控制的灯 | 表单 `light_entity`，`^light\.[a-z0-9_]+$`、≤63 字符；通过 native API 的 `Main light target` 文本实体写入、订阅读回 |
| 可选加密 | 布尔 `encrypt_api`，默认 false；API 凭据不能放入普通表单、zip、历史或日志 |
| HA | 设备接入与动作权限、真实触摸控灯由用户另行验收，不由保存任务替代 |

`target` 是 engine 部署 selector 保留键；表单继续使用 `light_entity`，固件内部
`cfg_target_main_light` / `Main light target` 不改名。`user_inputs` 本身不执行配置，
`serial_wizard` 文本通道不处理二进制 Improv。早期 generic script 适配是历史证明，当前入口
不需要外部网页、本机 venv、脚本路径或用户安装编译器。

原生模块为 `e1003_firmware.py`、`e1003_setup.py`、`e1003_transport.py`、App 路由与
`e1003-config-handler.js`。配置 job ready 只代表表单就绪；成功须等复位读回。
普通任务不返回 key，复制是完成加密后的显式请求，响应 no-store；页面离开不得提前释放串口。

## 传输与恢复

- UART0 混有日志：缓冲分片、校验 Improv header/长度/checksum，请求加 newline；仅接受已验证的内层长度之外单零 footer。
- 免密 API 与可选加密均校验设备 project/name/MAC；网络地址不能代替身份。
- 可选加密生成 CSPRNG 32 bytes/base64；安装 key 前原子保存私有恢复记录。短激活断线有限重试，不能重复生成 key。
- 默认无 key 的记录可存公开身份与地址；旧加密切换过程保留原 key，免密重连验证后才删除。
- Unix 新私有记录 0600、目录 0700；Windows 继承 App 数据目录 ACL。禁止复制恢复记录、备份或私密日志入内容仓库。
- runtime text 默认 60 秒 flush，通电等待 65 秒再复位验证；不同版本迁移只按已有实测范围声明。

## 触摸和图片边界

固件仅绑定灯开关及 25/50/75/100 亮度共五个触摸区，其余图形无点击动作。坐标不改，
只新增 INFO 坐标/命中诊断；没有“按钮已修复”的结论。未确认的用户触摸不能算触摸通过或失败。

现有封面、实体图和[来源说明](../solutions/reterminal_e1003_ha/gallery/README.md)保留。
封面 Device key 只代表可选加密能力，图注与双语正文已说明；官方照片是官方展示界面，
不是本固件验收图。`device_catalog` 仍用产品族 + `purchase.require`，不绕过 `purchase_profile`。

## 当前证据与发行依赖

任务 `56899ea5f4c441aab0bf1ea227c50473` 实际从 0.1.0 升至 0.2.0：镜像/身份校验通过，
Wi-Fi 留空复用、原 key 授权清除、写同一 target、等待 65 秒、复位免密读回；结果
`encrypted=false`，记录无 `api_key`。操作面为打包后端与桌面共享前端，**不是本次原生窗口提交验收**。
原生窗口仅确认加密 checkbox AXValue=0、无 key 复制按钮；桌面/375×812 审查无横溢。
详见[检查报告](e1003-ha-usb-checks.md)；0.1 的原生窗口和加密证据作为历史保留。

剩余依赖：公开 contract 13、兼容 App 分发与固件公网 URL；十分钟后复查、新 Wi-Fi 表单、
触摸、真实 HA 控灯和屏幕同步、出厂空白设备及两面板隔离等仍待验收。
本内容会话只读点名的公开证据/manifest、公开源码/文档，真实固件只用于既有打包检查；
不操作 App/串口，不读其他私密记录，不发布或上传二进制。
