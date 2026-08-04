## 套餐: 停车位监控 {#default}

使用 reCamera 内置 AI 实时检测停车位状态。连上摄像头即可部署，无需额外服务器。

| 设备 | 用途 |
|------|------|
| reCamera | 检测车位占用和空闲状态 |

**部署完成后你可以：**
- 实时查看车位状态（空闲/占用）
- 通过 Dashboard 查看带颜色标记的检测画面
- 调节检测灵敏度

**前提条件：** reCamera 通过 USB 或网络连接

## 步骤 1: 部署到 reCamera {#deploy_flow type=recamera_nodered required=true config=devices/recamera.yaml}

将停车位检测流程和 AI 模型部署到 reCamera。

### 接线

1. 用 USB-C 线将 reCamera 连接到电脑
2. 输入 reCamera 的 IP 地址和 SSH 密码
3. 点击部署按钮安装停车位检测流程

### 部署完成

1. 在浏览器打开 **http://\<reCamera-IP\>:1880/dashboard/preview**
2. 你应该能看到带检测框的实时摄像头画面
3. 在文本输入框中输入车位编号（如 `A1,A2,A3`）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查 USB 线连接；两个密码都试试：`recamera` 和 `recamera.2` |
| 没有摄像头画面 / 黑屏 | 部署后摄像头服务需要约 90 秒重启；等待后刷新页面 |
| 模型下载失败 | 确保 reCamera 能上网（WiFi 或 USB 共享网络） |
| 检测不准确 | 调节 Dashboard 上的 Confidence 和 IoU 滑块 |

---

## 步骤 2: 配置车位标签 {#verify_dashboard type=manual required=false}

在下一步打开面板后，为现场设置车位：

1. 在文本输入框中输入车位编号（如 `A1,A2,A3` — 每个编号对应一个检测到的车位，从左到右排列）
2. 调节 **Confidence** 和 **IoU** 滑块以适应你的环境

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 显示 "Monitoring Slots: None" | 在 Dashboard 的文本输入框中输入车位编号 |
| 车位状态闪烁 | 提高 Confidence 阈值；稳定算法需要 15 帧确认 |
| 车位编号对不上 | 编号按从左到右的位置对应——调整编号顺序匹配摄像头视角 |

## 步骤 3: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

停车监控面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |
### 部署完成

你的 AI 停车位监控已经开始运行了。

#### 快速验证

- 打开 **http://\<reCamera-IP\>:1880/dashboard/preview**
- 绿色圆圈 = 空闲车位，红色圆圈 = 已占用
- 状态面板实时显示车位数量

#### 使用建议

- 将 reCamera 以略微倾斜的角度朝向停车位安装（正面视角效果最佳）
- 当前设计针对 3 个相邻停车位优化
- 系统使用多帧验证机制，避免阴影或临时遮挡导致误判

#### 后续步骤

- [查看 Wiki 文档](https://wiki.seeedstudio.com/cn/ai_parking_slot_monitoring_demo_with_recamera/)
- [报告问题](https://github.com/Seeed-Studio/wiki-documents/issues)
