# reSpeaker 声学前端与麦克风阵列调优部署指南

本方案为 reSpeaker 系列 USB 麦克风阵列（reSpeaker Lite、reSpeaker XVF3800）提供基于 Chromium 内核浏览器（Chrome、Edge）的免驱声学调优环境。

---

## 套餐: 声学前端实时调测工作台 {#acoustic_tuning_workbench}

## 步骤 1: 打开声学调测工作台 {#audio_lab type=web_dashboard required=true config=devices/online_audio_lab.yaml}

通过 WebUSB 与 WebAudio 接口直接连通硬件，无需在操作系统安装额外的 Python 驱动或配置复杂的编译环境。

### 前置条件

1. 使用 USB 数据线将 reSpeaker 麦克风阵列（reSpeaker Lite 或 reSpeaker XVF3800）连接到电脑的 USB 接口。
2. 推荐使用 Google Chrome 或 Microsoft Edge 浏览器访问工作台（需要浏览器支持 WebUSB 与 WebAudio 特性）。
3. macOS 用户请确认已在系统设置中允许浏览器访问麦克风；Linux 用户若遇权限问题，请添加 udev 规则。

### 接线

1. **连接 USB 控制**：点击页面右上角的「连接设备」按钮，在浏览器弹出的系统 USB 设备列表中选中你的 reSpeaker 设备并点击配对。
2. **授权麦克风采集**：点击「开始采集」，并在浏览器提示框中允许麦克风权限，此时页面上的实时音频波形与电平表将开始刷新。
3. **声学前端调测与对比**：
   - **降噪对比**：对比原始麦克风通道与经过硬件 DSP（降噪、自动增益、波束成形）处理后的音频波形差异；
   - **回声实验**：播放提示音测试内置硬件 AEC 回声消除能力，评估打断唤醒（Barge-in）抑制表现；
   - **声源与通道**：观察 360 度声源方位角（DOA）追踪与多物理麦克风通道映射；
   - **录音与转录**：录制音频样本并调用端侧轻量 Whisper 引擎验证收音清晰度。

### 故障排查

| 现象 | 排查措施 |
|---|---|
| 点击「连接设备」找不到硬件 | 检查 USB 线缆是否具备数据传输功能，重新插拔设备或更换 USB 端口 |
| 无法获取麦克风音频流 | 检查浏览器地址栏左侧的权限设置，确保未禁止网页调用麦克风 |
| 录音转录无反应 | 首次转录需下载约 40MB 的端侧轻量 WASM 模型，请确保网络通畅并耐心等待缓存完成 |

### 部署目标 {#audio_lab_target type=local device_name="Local Browser" config=devices/online_audio_lab.yaml}
