## 套餐: ARM64 Linux 主机 + Jetson Orin NX 语音 {#rpi_jetson}

ARM64 Linux 主机运行 Home Assistant，reComputer J40 负责听懂语音和生成回复语音，两台设备在同一局域网内配合工作。

| 设备 | 用途 |
|------|------|
| ARM64 Linux 主机（64 位系统，8GB 内存） | 运行 Home Assistant |
| reComputer J40 系列（Jetson Orin NX 16GB） | 本地语音识别和语音合成 |
| Home Assistant Connect ZBT-2 | 接入 Zigbee 设备 |
| Home Assistant Voice 预览版 | 房间里的语音终端 |

**部署完成后你可以：**
- 用中文或英文语音控制灯光等设备，说完到识别出文字中位数 0.12 秒
- 把 Zigbee 传感器和开关接入 Home Assistant
- 在 iPhone 的「家庭」App 和 Siri 里控制同一批设备

**前提条件：** 两台设备在同一局域网 · reComputer J40 至少 30 GB 可用磁盘，首次启动需联网下载语音模型

## 步骤 1: 部署 Home Assistant {#rpi_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

在 ARM64 Linux 主机上安装 Home Assistant。

### 前置条件

- 主机运行 64 位 Linux 系统，至少 8 GB 可用磁盘
- ZBT-2 可以稍后再接：「ZBT-2 设备路径」先留空，接上 ZBT-2 后填写路径再部署一次

### 接线

1. 把 ARM64 Linux 主机接入局域网并开机
2. 把 ZBT-2 插到主机的 USB 口；在主机上执行 `ls /dev/serial/by-id/`，把列出的路径填到「ZBT-2 设备路径」
3. 默认端口为 8123；主机上已有其他程序占用 8123 时，填写另一个端口
4. 点击部署

### 部署完成

1. 在浏览器打开 **http://\<主机 IP\>:8123**（改过端口时换成你填的端口）；首次启动需要等待片刻
2. 按页面提示创建管理员账号

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示端口已被占用 | 在「Home Assistant 端口」填写另一个端口后重新部署 |
| 改了端口但 Home Assistant 仍用原来的端口 | 已安装过的 Home Assistant 保留首次安装时的端口，部署时填写的端口对它不再生效；继续用原来的端口访问 |
| 用本方案早期版本装过 Home Assistant，重新部署后变成全新的空配置 | 早期版本把配置存放在 `/opt/ha-whole-home/ha-config`，现在改为 `~/ha-whole-home/ha-config`，旧配置不会自动迁移。在主机上执行 `docker stop $(docker ps -q --filter label=com.docker.compose.project=ha_whole_home_rpi)`，再执行 `mkdir -p ~/ha-whole-home && sudo cp -a /opt/ha-whole-home/ha-config/. ~/ha-whole-home/ha-config/`，然后重新部署 |
| 页面打不开 | 等待几分钟后刷新；确认浏览器所在电脑和主机在同一局域网 |
| Home Assistant 里看不到 ZBT-2 | 确认「ZBT-2 设备路径」填的是 `/dev/serial/by-id/` 下的完整路径，重新部署 |
| 连接主机失败 | 检查 IP 地址、用户名和密码，确认主机已开机并接入局域网 |

### 部署目标: 本机部署 {#rpi_local type=local device=arm64_linux device_name="ARM64 Linux 主机（64 位系统，8GB 内存）" config=devices/ha_rpi.yaml}

在当前这台 ARM64 Linux 主机上安装。

### 部署目标: 远程部署 {#rpi_remote type=remote device=arm64_linux device_name="ARM64 Linux 主机（64 位系统，8GB 内存）" config=devices/ha_rpi.yaml default=true}

通过网络连接 ARM64 Linux 主机安装，需要它的 IP 地址、用户名和密码。

---

## 步骤 2: 部署 Jetson 语音服务 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

在 reComputer J40 上安装语音识别和语音合成服务，供 Home Assistant 调用。

### 前置条件

- reComputer J40（Jetson Orin NX 16GB），至少 30 GB 可用磁盘
- 首次启动需联网下载语音模型，下载完成前服务不可用

### 接线

1. 把 reComputer J40 接入与 Home Assistant 主机相同的局域网并开机
2. 端口保持默认即可：语音转文字 10300、文字转语音 10200、语音服务 8623；其中某个端口已被占用时再修改
3. 记下 reComputer J40 的 IP 地址和这两个端口，步骤 3 会用到
4. 点击部署

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示磁盘空间不足 | 清理出至少 30 GB 可用空间后重新部署 |
| 提示端口已被占用 | 换一个未被占用的端口后重新部署，三个端口不能相同 |
| 部署后很久没有就绪 | 首次启动要先下载语音模型，耗时取决于网速；确认 reComputer J40 能访问互联网 |
| 提示缺少 NVIDIA 容器运行环境 | 确认 reComputer J40 刷的是完整的 JetPack 系统（含 NVIDIA 容器运行环境）后重试 |
| 连接设备失败 | 检查 IP 地址、用户名和密码，确认设备已开机并接入局域网 |

### 部署目标: 本机部署 {#jetson_local type=local device=jetson device_name="reComputer J40（Jetson Orin NX 16GB）" config=devices/jetson_voice.yaml}

在当前这台 reComputer J40 上安装。

### 部署目标: 远程部署 {#jetson_remote type=remote device=jetson device_name="reComputer J40（Jetson Orin NX 16GB）" config=devices/jetson_voice.yaml default=true}

通过网络连接 reComputer J40 安装，需要它的 IP 地址、用户名和密码。

---

## 步骤 3: 接入本地语音并验证 {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

在 Home Assistant 里添加语音服务，然后用一句话测试。

### 部署完成

1. 打开 Home Assistant，进入 **设置 → 设备与服务 → 添加集成**，搜索 **Wyoming Protocol**；主机填 reComputer J40 的 IP 地址，端口填步骤 2 的语音转文字端口（默认 10300）
2. 再添加一个 **Wyoming Protocol** 集成，主机相同，端口填文字转语音端口（默认 10200）
3. 进入 **设置 → 语音助手**，打开语音助手，语言选中文或英文，「语音转文字」和「文字转语音」分别选刚添加的两个服务，保存
4. 点右上角的对话按钮，说或输入「打开客厅灯」，对应的灯被打开并收到回复

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 添加集成时提示无法连接 | 确认步骤 2 已就绪、IP 和端口填写正确，Home Assistant 主机能访问 reComputer J40 |
| 语音助手里选不到语音服务 | 确认两个 Wyoming Protocol 集成都已添加成功 |
| 重新部署步骤 2 时改了端口，语音不再工作 | 删除这两个 Wyoming Protocol 集成，用新端口重新添加 |
| 指令被识别但设备没反应 | 确认指令里的名称与 Home Assistant 里设备或区域的名称一致 |

---

# 部署完成

Home Assistant 和本地语音服务已就绪。

### 初始设置

1. **接入 Zigbee 设备**：进入 **设置 → 设备与服务 → 添加集成**，选择 **Zigbee Home Automation**，串口选 ZBT-2；之后在该集成里点「添加设备」，并让 Zigbee 设备进入配对模式
2. **接入苹果「家庭」**：Home Assistant 的通知里会出现 HomeKit Bridge 的配对二维码，用 iPhone 的「家庭」App 扫码添加
3. **接入语音终端**：按 Home Assistant Voice 预览版的说明连上 Wi-Fi 并加入 Home Assistant，在它的设备页把语音助手选为步骤 3 配置的那一个

### 快速验证

- 对语音终端说「打开客厅灯」，灯被打开并听到回复
- 在 iPhone 的「家庭」App 里能看到并控制同一批设备
- Zigbee 传感器的读数在 Home Assistant 里刷新
