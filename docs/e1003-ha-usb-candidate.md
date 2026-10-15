# E1003 参考设计：0.2.1 plaintext-only（待验收）

正式 technical 候选保持 `enabled:false`、单一 `usb_candidate` 入口和公开 contract 5 可校验的
人工 review stub。目标流程仍是一张表单完成自动检查、按需安装、配置及保存验证。

## 最新设计取代 0.2.0 可选加密

主控报告 0.2.0 在 610 秒免密复查时曾通过，随后设备再次返回
`RequiresEncryptionAPIError`。保留 runtime encryption 能力不能保证参考使用始终免密；
外部客户端可重新配置加密，但此次重新加密的具体来源**尚未确认**，不归因于某个客户端。
一次定时读回通过不能证明持续免密。

最终方向是 **0.2.1 plaintext-only**：彻底移除参考固件 `api.encryption` 的编译能力。
App 移除可选加密 checkbox 和所有 key 复制入口，`encrypt_api` 仅兼容 false 请求，
新契约为 14。开发者入口 `e1003-dashboard.yaml` 独立保留加密，不属于此参考候选。
这些是本轮设计要求；主控正在编译和实机验证，不能声明新固件或新窗口流程已通过。

## 资源与提交状态

- [固件 PR #2](https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/pull/2) 的新 0.2.1
  commit、factory 大小和 SHA 尚待主控提供，不猜值、不读未授权文件。
- [App PR #162](https://github.com/suharvest/app_collaboration/pull/162) 的 contract 14 实现/验收状态
  等待主控补充；此前 `68328f90` / contract 13 仅为可选加密的历史过渡版本。
- [manifest](../solutions/reterminal_e1003_ha/assets/firmware/manifest.json) 暂保留已知的 0.2.0：
  source `a7116ee153158505faeec225d691c0cdef85a6da`，1,377,472 B，
  SHA `45cbf1ec46d5a00e8362e6d920cd9318841c58f2a081cfae809d9e38e64ccebb`。
  它和模板只是旧资源记录，**不是最终 0.2.1 资源**。正式候选不能据此启用。

[`stage_e1003_candidate.py`](../scripts/stage_e1003_candidate.py) 仍是作者侧历史资源审阅工具；
在新清单到位前，打包旧镜像不能证明 plaintext-only 设计成立。见[资源说明](../solutions/reterminal_e1003_ha/assets/firmware/README.md)。
收到真实新构建后，必须一起更新 source/version/size/SHA、模板引用并验证实际打包；
保留 115200、offset 0、不全片擦除和既有 NVS 策略。不同构建不得复用同一 `project.version`。

## 目标交互与执行边界

| 项目 | 0.2.1 / contract 14 方向 |
| --- | --- |
| 用户输入 | USB 端口、`light_entity`、可选 Wi-Fi 名称/密码；无加密或 key 输入/复制控件 |
| API | 参考固件只支持明文 native API（TCP 6053）；`encrypt_api` 仅兼容 false，不将其作为可选功能 |
| 保存网络 | 已有可用网络时复用；首次联网填写 Wi-Fi。最终硬件流程仍待验证 |
| 自动安装 | 按 canonical manifest 核对 project/version/hardware/name；匹配最终 0.2.1 才跳过，安装前校验真实 size/SHA，安装后再查身份 |
| 保存 | 写灯光绑定，通电等待至少 65 秒，再复位免密读回；不以 RAM 读回或 ready 事件当完成 |
| 旧加密设备迁移 | 不套用 0.2.0 的清 key 流程作为已验证结论；等待新固件升级、NVS 与旧记录处理的最终证据 |
| HA | 无 API key 接入；HA 动作权限、真实控灯和屏幕同步独立验收 |

仍只保留一个部署入口，不增加“烧录 / 仅配置”套餐。不在公开 schema 中伪造 contract 14
执行类型或无处理器的表单。未来从 App 真源同步契约并分发兼容 App 后，才接单一原生步骤。

## 触摸、图像与网络

固件只为灯开关及 25/50/75/100 五个触摸区定义动作；其它图形无点击绑定。
触摸坐标不改，仅有 INFO 诊断，触摸/控灯仍待验收，不宣称已修复。
USB Improv、ESPHome native API、同一可达 LAN、无 MQTT/设备 web server 和 USB-only 边界保留。

保留官方实体图和生成架构封面；封面中的 Device key 是旧设计元素，**不代表 0.2.1 能力**，
图注与正文已标明待更新。照片是官方展示界面，不是本固件验收图。
[素材来源](../solutions/reterminal_e1003_ha/gallery/README.md)继续保留，产品族 + `purchase.require`
不变，不绕过 `purchase_profile`。

## 证据与下一步

0.1 的加密结果和 0.2.0 升级/免密过渡结果作为历史保留，610 秒复查后再度要求加密的
新观察已写入[检查报告](e1003-ha-usb-checks.md)。旧 JSON 是当时快照，不改写成新版本通过记录。
待主控提供 0.2.1 实际构建、升级/持续免密、App 控件移除与配置验收证据后再更新结论。
新 Wi-Fi、触摸、真实 HA 控灯和动态屏幕同步也仍待验收。

发行依赖仍包括公开 contract 14、兼容 App、真实固件 size/SHA 与公网下载地址；本任务不发布。
本轮只改内容仓库文案，不操作 App/串口，不读取新固件或私密记录。
