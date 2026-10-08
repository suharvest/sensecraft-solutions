## 套餐: Clip + reComputer Jetson {#clip_edge_box}

录音从 Clip 同步到 reComputer Jetson，在主机上转写并分出说话人，结果在本地网页查看。

| 设备 | 用途 |
|------|------|
| reSpeaker Clip | 佩戴录音 |
| reComputer J40（Jetson Orin NX，JetPack 6.2） | 同步录音、转写、提供结果页 |

**部署完成后你可以：**
- 在浏览器打开结果页，查看带时间戳和说话人标签的文字稿
- 用 HTTP 接口上传录音或取回转写结果
- 订阅 MQTT 消息，在转写完成时收到通知
- 可选：为每段转写生成 AI 摘要

**前提条件：** 主机有蓝牙（Jetson 无线网卡模块）· 至少 15 GB 可用磁盘 · 首次部署需要联网

## 步骤 1: 部署转写服务 {#deploy_stack type=docker_deploy required=true config=devices/jetson_stack.yaml}

在 reComputer Jetson 上安装转写服务，并把你的 Clip 写入配置。

### 部署目标: 远程部署 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_stack.yaml default=true}

从这台电脑通过 SSH 部署到 reComputer J40。

### 前置条件

- 主机是 Jetson Orin NX 模组，系统为 JetPack 6.2；其他型号或版本会在部署开始时停止并提示
- 主机有至少 15 GB 可用磁盘，并且能访问互联网
- Clip 已从手机 App 解除绑定

### 接线

1. 给 reComputer J40 接上电源和网线，确认它与这台电脑在同一网络
2. 把 Clip 充上电，放在主机旁边
3. 填写主机 IP、SSH 用户名和密码
4. 填写 Clip 名称：“Clip” 加上机身上印的 4 位编号，例如 `Clip 7036`；手机 App 中显示的也是这个名称
5. 按需打开“通过 Wi-Fi 加速同步”和“AI 摘要（可选）”，然后点击部署

### 部署完成

首次部署会下载语音识别模型（约 1.8 GB）并启动服务，耗时取决于网速。完成后：

1. 在部署日志末尾找到 API key，保存好
2. 在浏览器打开 `http://<主机IP>:8631/`，输入 API key 进入结果页

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示 Jetson 模组或 JetPack 不匹配 | 本方案只支持 Jetson Orin NX + JetPack 6.2，换用符合要求的主机 |
| 磁盘空间不足 | 清理主机磁盘，留出至少 15 GB |
| 模型下载失败或很慢 | 检查主机能否访问互联网后重新部署，已下载的模型会保留 |
| 提示 Clip 名称格式不对 | 按 `Clip 7036` 的格式填写：Clip、空格、4 位编号 |
| 提示 AI 摘要缺少服务地址 | 填写服务地址和模型名称，或关闭 AI 摘要 |
| 端口 8631、8621、8622 或 1883 被占用 | 停止主机上占用这些端口的其他服务后重新部署 |

### 部署目标: 本机部署 {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_stack.yaml}

在 reComputer J40 本机上运行 SenseCraft Solution 并部署。

### 前置条件

- 本机是 Jetson Orin NX 模组，系统为 JetPack 6.2
- 本机有至少 15 GB 可用磁盘，并且能访问互联网
- Clip 已从手机 App 解除绑定

### 接线

1. 确认本机已接网
2. 把 Clip 充上电，放在主机旁边
3. 填写 Clip 名称，例如 `Clip 7036`
4. 按需打开“通过 Wi-Fi 加速同步”和“AI 摘要（可选）”，然后点击部署

### 部署完成

首次部署会下载语音识别模型（约 1.8 GB）并启动服务，耗时取决于网速。完成后：

1. 在部署日志末尾找到 API key，保存好
2. 在浏览器打开 `http://localhost:8631/`，输入 API key 进入结果页

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示 Jetson 模组或 JetPack 不匹配 | 本方案只支持 Jetson Orin NX + JetPack 6.2 |
| 写入配置或模型时提示权限不足 | 改用“远程部署”，从另一台电脑通过 SSH 部署到本机 |
| 磁盘空间不足 | 清理磁盘，留出至少 15 GB |
| 端口 8631、8621、8622 或 1883 被占用 | 停止占用这些端口的其他服务后重新部署 |

## 步骤 2: 检查服务状态 {#verify_stack type=http_debug required=true config=devices/verify_clip.yaml}

确认转写服务已经就绪。

### 接线

1. 填写主机 IP（本机部署填 `localhost`）
2. 点击检查，返回 HTTP 200 表示服务就绪

### 部署完成

转写服务已在 reComputer Jetson 上运行。

#### 初始设置

1. 在浏览器打开 `http://<主机IP>:8631/`，输入部署日志末尾显示的 API key
2. 忘记 API key 时，在主机上运行 `sudo cat /opt/clip-private-transcription/config/api_key` 查看
3. 要改 Clip、Wi-Fi 同步或 AI 摘要设置，回到步骤 1 修改后重新部署；API key 留空会沿用原来的

#### 快速验证

1. 用 Clip 录一段 30 秒左右的对话，放回主机旁边
2. 等录音同步完成，在结果页看到新的文字稿，每段有时间戳和说话人标签

没有 Clip 在手时，也可以上传一段 16 kHz 单声道 WAV 录音测试：

```bash
curl -H "Authorization: Bearer <API key>" -F file=@sample.wav http://<主机IP>:8631/v1/transcribe
```

订阅转写完成通知：`mosquitto_sub -h <主机IP> -t 'clip-pt/+/transcript/+/ready'`

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 返回 503 | 语音识别仍在加载，等几分钟再试 |
| 连接被拒绝 | 确认主机 IP 正确，并在主机上运行 `docker ps` 查看服务是否在运行 |
| 结果页一直没有新录音 | 确认 Clip 有电、在主机蓝牙范围内，且没有同时绑定手机 App |
| 附近有多个 Clip，连错了设备 | 在步骤 1 填写“Clip 蓝牙地址（可选）”后重新部署 |
| 开启 Wi-Fi 同步后同步失败 | 确认填写的无线接口没有被主机用来上网；没有空闲接口时关闭 Wi-Fi 同步，只用蓝牙 |
| 没有生成摘要 | 检查 AI 对话服务的地址、模型名称和密钥；很短的录音不生成摘要 |
