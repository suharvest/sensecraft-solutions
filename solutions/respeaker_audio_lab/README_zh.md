# reSpeaker Audio Lab

本目录是浏览器实验页面，用于读取真实 reSpeaker USB 音频、探测 XVF3800 参数、轮询 DOA，以及在本地运行 Whisper Tiny 转录。它是本地实验页面，不是发布方案，不包含 `solution.yaml`。

## 本地启动

在仓库根目录执行静态 HTTP 服务：

```bash
python3 -m http.server 8080 --directory solutions/respeaker_audio_lab/assets/web
```

用支持 WebUSB 的浏览器打开 <http://localhost:8080/>。`localhost` 属于浏览器允许设备权限的安全环境，也可以使用部署后的 HTTPS 地址。直接用 `file://` 打开 `index.html` 不受支持。

页面需要分别授权两类设备：先点击“连接 USB 控制”授权设备控制通道，再点击“授权麦克风”，从音频输入列表选择同一台 reSpeaker。浏览器和操作系统可能分别弹出 USB 与麦克风权限提示。页面不会抢占音频接口、分离内核驱动、猜测接口编号或重置 USB 配置。

## 设备能力边界

- XVF3800、Flex 以及旧协议 XVF3000（`2886:0018`）先按 USB VID/PID 识别，再逐项读取探测能力。只有成功回读的参数才会启用。不同固件可能有不同通道路由和控制项；页面不会根据型号名称推断通道映射。2026-09-10 在 macOS 上实测了一台 XVF3000，固件值为 `16`：USB 实读得到 firmware `16` 和 DOA，legacy 参数可读；网页将 `MIN_NS` 从 `.15` 调到 `.16` 后，独立 libusb 回读并恢复为 `.15`，结果一致。
- 同一台 XVF3000 在系统音频设备中显示为 6 通道、16 kHz，但本次浏览器 `getUserMedia` 最多只暴露 2 通道；浏览器 `AudioContext` 实际运行在 48 kHz，两个暴露通道都产生了真实电平。这不能证明浏览器能采集 6 通道，也不能证明原始音频与处理后音频的通道映射。
- reSpeaker Lite 按 USB 音频设备处理。Lite 文档中的 I2C 配置路径不属于本页面能力。将 Lite 在 USB 与 I2S 固件之间切换需要执行设备固件流程，本页面不会执行。
- 未知产品和未知固件在有效固件探测前保持 fail-closed。即使 USB 控制不可用，USB 音频仍可能可以使用。
- DOA 是设备报告的方向值，不是距离估计。物理麦克风布局、通道映射、固件版本和输出路由仍需在设备上实测确认。
- 实机验证仍未完成。当前只验证了一个 macOS 环境下的 XVF3000 USB 控制和浏览器暴露的两个音频通道；Flex、XVF3800、Lite、其他固件、浏览器 6 通道采集以及通道映射仍需逐项实测。

界面以实时信号为主视图：降噪参数放在频谱下方，增益和高通参数放在通道监视区域，AEC 参数放在 AEC 区域，完整参数通过二级对话框查看。

## 本地转录

第一次点击转录会从 [ModelScope](https://modelscope.cn/models/onnx-community/whisper-tiny) 下载并缓存量化的 `onnx-community/whisper-tiny` 模型，以及配置的 Transformers.js/WASM runtime。首次转录需要联网；后续是否能使用取决于浏览器缓存。量化模型约 41 MB，此外还需要 runtime 和 tokenizer，实际大小会随浏览器缓存和资源版本变化。音频在浏览器内处理，页面不会上传录音。

AEC 演示需把远端参考音频输出到 reSpeaker 并经扬声器播放，确认设备固件具有对应参考路由；普通录音回放可使用耳机。转录差异不等于音质评分。

## 验证与发布待办

执行 `node --test solutions/respeaker_audio_lab/assets/web/tests/*.test.mjs` 验证软件逻辑。测试数据是确定性测试夹具，不是实体设备认证。

页面已检查桌面和窄屏布局。部署时需要把 `assets/web/` 下的文件一起放到同一个 HTTPS 静态站点，并分享该站点 URL；`localhost` 仅用于开发，不能直接使用 `file://`。每位使用者都需要在自己的浏览器中授权 USB 和麦克风。模型或 runtime 下载失败时可以在页面重试。

待完成：各型号 USB 固件与系统/浏览器组合实测、确认通道映射，再补齐 SenseCraft 方案清单和端到端验证。本原型没有执行固件烧录或内容发布。

协议参考：[Flex 控制源码](https://github.com/respeaker/reSpeaker_Flex/blob/main/python_control/xvf_host.py)、[Lite 固件](https://github.com/respeaker/ReSpeaker_Lite)、[ModelScope 上的 Tiny 模型](https://modelscope.cn/models/onnx-community/whisper-tiny)。
