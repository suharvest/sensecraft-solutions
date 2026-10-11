## 这个方案能帮你做什么

边缘设备命令工作台在本地浏览器中提供一个专注的操作界面：用户输入简短请求，应用从允许的候选命令中给出排序结果。模型和 tokenizer 运行在 RK3576 上，请求可以留在本地网络内。

![RK3576 上运行的边缘设备命令工作台](gallery/workbench.jpg)

![命令选择步骤](gallery/demo/command-selection.gif)

## 核心价值

| 好处 | 具体说明 |
|------|----------|
| 保持请求本地处理 | 候选命令选择在 RK3576 上完成，不需要把请求发送到云端。 |
| 接入已有控制系统 | `POST /api/decide` 返回 JSON 选择结果和排序，可接入设备控制程序或网页应用。 |
| 限定可执行范围 | 由你的应用提供允许的候选命令，工作台只对这些选项排序，不生成不受控的任意命令。 |
| 保持边缘路径简洁 | 在已验证的 RK3576 环境中，对同一条 43-token 输入重复执行 120 次，total 延迟 p50 为 335.43 ms。这是延迟观察值，不是准确率结论。 |
| 按需连接语音 | 已有兼容的本地语音服务时可通过 `VOICE_SERVICE_URL` 连接；本方案不会自动安装语音服务。 |

## 适用场景

| 场景 | 怎么用 |
|------|--------|
| 输送带控制 | 提供“设置速度”“停止”“读取状态”等候选项，再为“把 3 号输送带降到 60%”排序。 |
| 工厂状态面板 | 让操作员用中文或英文短句选择“读取状态”动作。 |
| 机器人或网关接入 | 由已有控制系统发送候选列表，并读取 JSON 中的选中项。 |

## 使用须知

### 核心硬件设备

| 设备 | 说明 | 必需 |
|------|------|------|
| RK3576 Linux 设备，例如 LubanCat3 | 运行单容器 Web 工作台和 RKNN 模型 | ✓ 必选 |

现有已验证包面向 RK3576/RKNN。RKLLM Kev 已在 cat-remote RK3576 和 Radxa RK3588 完成设备验证：RK3576 部署请求限制为 2048 tokens，engine 导出容量为 8192；RK3588 部署上下文为 8192。应用 Docker 源中保留现有 Jetson TensorRT 部署；本方案介绍页不宣称 Jetson 原生 Kev 支持。

### 网络和存储要求

- 部署需要 SSH 访问目标设备。
- 目标文件系统至少保留 4GB 可用空间。
- 目标设备需要已有 Docker 和 `/usr/lib/librknnrt.so`。
- 容器不使用 `privileged` 模式，通过 RK3576 NPU DRM 节点、只读设备树路径和只读 RKNN 运行库挂载访问运行时。
- 首次部署会从配置的 HF endpoint 下载固定版本的归档、模型和 tokenizer，默认地址为 `https://hf-mirror.com`。

### Kev RKLLM 产物

- RK3576 和 RK3588 engine、FP32 Q/K head、tokenizer、metadata、RKLLM 1.3.1 runtime 与许可证说明均作为固定版本独立产物。
- 容器一次只加载一个本地模型系列。`MODEL_SERVICES_JSON` 可将另一模型系列指向已有 HTTP 服务，不会同时把两套模型加载到内存。
- Kev 套餐的已测设备与上下文限制见支持矩阵；这不代表同 SoC 的其他设备具有相同内存余量或无限上下文能力。

### 可选语音

只有提供已有兼容的本地语音服务时才可使用语音输入。本方案不会自动安装语音服务。浏览器麦克风访问需要 HTTPS 或 localhost。

## Kev QA 素材与支持矩阵

`gallery/kev-final/` 保存了 2026-10-11 Radxa RK3588 候选版本的中英文页面截图、pending 状态和截图剪辑。素材 SHA、服务地址、健康响应和请求元数据见 `gallery/kev-final/README.md` 与 `kev-final-evidence-20261011.json`。截图剪辑只表示页面步骤，不表示模型耗时、实时录屏或准确率。截图中的语音配置仅为可选项，未进行语音测试。

| 硬件/后端 | 当前状态 |
|---|---|
| RK3576 / RKNN Laya | 既有已验证路径 |
| RK3588 / RKLLM Kev | Radxa 已验证 8192 context、5 条 golden、超长输入错误和双模型 HTTP 切换；发布清单仍为 draft |
| RK3576 / RKLLM Kev | cat-remote 已验证；部署限制 2048 tokens，engine 容量 8192 |
| Jetson / TensorRT | 保留既有 TensorRT 路径；不宣称 Jetson 原生 Kev 支持 |

双模型切换的真实浏览器素材位于 `gallery/kev-final-switch/`：Laya 页面 chip/result 均显示 `rknn / 90 tokens`，Kev 页面 chip/result 均显示 `rkllm / 8192 tokens`。同一条英文指令分别通过下拉选择两个 profile；`Test and connect` 的真实 `GET /api/models` 返回 HTTP 200。素材说明了最终 UI 的可读性取整（score 三位小数、毫秒一位小数），raw API 数值保存在 evidence JSON 中。
