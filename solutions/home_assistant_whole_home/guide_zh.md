## 套餐: ARM64 Linux 主机 + 语音主机（J40、RK3588 + RK1828 或 J30） {#rpi_jetson}

ARM64 Linux 主机运行 Home Assistant，语音主机负责听懂语音、生成回复语音；开关设备之外的问题交给大模型回答，两台设备在同一局域网内配合工作。

| 设备 | 用途 |
|------|------|
| ARM64 Linux 主机（64 位系统，8GB 内存） | 运行 Home Assistant |
| 语音主机（下表任选一台） | 本地语音识别和语音合成 |
| Home Assistant Connect ZBT-2 | 接入 Zigbee 设备 |
| Home Assistant Voice 预览版 | 房间里的语音终端 |

| 语音主机 | 回答设备控制之外的问题 |
|------|------|
| reComputer J40（Jetson Orin NX 16GB） | 本机运行的大模型 |
| reComputer RK3588（16GB）+ RK1828 加速卡 | 加速卡上运行的大模型 |
| reComputer RK3588（不带 RK1828 加速卡） | 你填写的云端大模型服务 |
| reComputer J30（Jetson Orin Nano 8GB） | 你填写的云端大模型服务 |

**部署完成后你可以：**
- 用中文或英文语音控制灯光等设备，说完到识别出文字中位数 0.12 秒
- 问「今天适合开窗吗」这类问题，由大模型回答；开关设备的指令仍由 Home Assistant 在本地执行
- 把 Zigbee 传感器和开关接入 Home Assistant
- 在 iPhone 的「家庭」App 和 Siri 里控制同一批设备

**前提条件：** 两台设备在同一局域网 · 语音主机首次启动需联网下载模型 · 选用云端大模型时，需要一个兼容 OpenAI 接口的大模型服务地址、模型名称和服务密钥

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

---

## 步骤 2: 部署语音主机 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

在语音主机上安装语音识别和语音合成服务，供 Home Assistant 调用。reComputer J40 和带 RK1828 加速卡的 RK3588 同时安装本地大模型；其他语音主机使用你填写的云端大模型服务。

### 前置条件

- 可用磁盘：reComputer J40 至少 40 GB，J30 至少 20 GB，RK3588 + RK1828 至少 16 GB，RK3588 和 RK3576 至少 10 GB
- 首次启动需联网下载模型，下载完成前服务不可用
- RK3588 + RK1828：加速卡已接好供电，驱动和固件已安装（系统里能看到 `/dev/pcie-rkep-*` 设备），且卡上没有运行其他大模型
- 云端大模型：准备兼容 OpenAI 接口的服务地址（例如 `https://api.deepseek.com`）、模型名称和服务密钥；服务密钥只在步骤 3 的 Home Assistant 里填写
- 本地大模型（J40、RK3588 + RK1828）：准备 Home Assistant 主机的 IP 地址，本地大模型只接受这台主机和语音主机本机的连接

### 接线

1. 把语音主机接入与 Home Assistant 主机相同的局域网并开机
2. 端口保持默认即可：语音转文字 10300、文字转语音 10200、语音服务 8623，本地大模型 8000（J40）或 1828（RK1828）；其中某个端口已被占用时再修改
3. 本地大模型：填写 Home Assistant 主机的 IP 地址；云端大模型：填写大模型服务地址，部署时会先检查语音主机能否访问它
4. 记下语音主机的 IP 地址和端口，步骤 3 会用到
5. 点击部署

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示磁盘空间不足 | 按前置条件清理出足够的可用空间后重新部署 |
| 提示端口已被占用 | 换一个未被占用的端口后重新部署，各端口不能相同 |
| 部署后很久没有就绪 | 首次启动要先下载模型，耗时取决于网速；确认语音主机能访问互联网 |
| 提示缺少 NVIDIA 容器运行环境 | 确认 reComputer J40 / J30 刷的是完整的 JetPack 系统（含 NVIDIA 容器运行环境）后重试 |
| 提示找不到 RK1828 加速卡 | 检查加速卡供电、驱动和固件；没有加速卡时改选「RK3588（云端大模型）」 |
| 提示无法访问大模型服务 | 核对服务地址，确认语音主机能访问互联网 |
| 提示服务地址不是兼容 OpenAI 的接口 | 填服务商文档里「兼容 OpenAI」的地址 |
| 提示缺少 curl | 在语音主机上安装 curl 后重新部署 |
| 提示缺少 iptables | 在语音主机上安装 iptables 后重新部署；本地大模型靠它只对 Home Assistant 主机开放 |
| 语音主机或 Docker 重启后本地大模型没有启动 | 本地大模型要等访问限制生效后才启动（语音主机或 Docker 重启时会自动重新应用）；在语音主机上执行 `sudo systemctl status ha-whole-home-llm` 查看原因，排除后执行 `sudo systemctl restart ha-whole-home-llm` |
| 连接设备失败 | 检查 IP 地址、用户名和密码，确认设备已开机并接入局域网 |

### 部署目标: 本机部署 {#jetson_local type=local device=jetson device_name="reComputer J40（Jetson Orin NX 16GB）" config=devices/jetson_voice.yaml}

在当前这台 reComputer J40 上安装，大模型在本机运行。

### 部署目标: 远程部署 {#jetson_remote type=remote device=jetson device_name="reComputer J40（Jetson Orin NX 16GB）" config=devices/jetson_voice.yaml default=true}

通过网络连接 reComputer J40 安装，大模型在本机运行；需要它的 IP 地址、用户名和密码。

### 部署目标: RK3588 + RK1828（本地大模型） {#rk3588_rk1828_remote type=remote device=rk3588_rk1828 device_name="reComputer RK3588（16GB）+ RK1828" config=devices/rk3588_rk1828_voice.yaml}

通过网络连接装有 RK1828 加速卡的 reComputer RK3588 安装，大模型在加速卡上运行；需要它的 IP 地址、用户名和密码。

### 部署目标: J30（云端大模型） {#j30_remote type=remote device=j30 device_name="reComputer J30（Jetson Orin Nano 8GB）" config=devices/jetson_nano_voice.yaml}

通过网络连接 reComputer J30 安装，设备控制之外的问题由你填写的云端大模型回答。

语音服务启动时需要超过 2.5 GB 可用内存，J30 上不要同时运行其他 AI 服务。

---

## 步骤 3: 接入本地语音并验证 {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

在 Home Assistant 里添加语音服务和大模型对话，然后测试。

### 部署完成

1. 打开 Home Assistant，进入 **设置 → 设备与服务 → 添加集成**，搜索 **Wyoming Protocol**；主机填语音主机的 IP 地址，端口填步骤 2 的语音转文字端口（默认 10300）
2. 再添加一个 **Wyoming Protocol** 集成，主机相同，端口填文字转语音端口（默认 10200）
3. 再添加一个 **LiteLLM** 集成：
   - reComputer J40 或 RK3588 + RK1828：服务地址填 `http://<语音主机 IP>:<本地大模型端口>`（默认 8000 或 1828），密钥留空
   - 其他语音主机：服务地址填步骤 2 填写的大模型服务地址，密钥填大模型服务商提供的服务密钥
4. 在 LiteLLM 集成里添加对话代理：模型选步骤 2 的模型名称（本地大模型只列出一项），「控制 Home Assistant」不勾选；「指令」改为下面这段，保存：

   ```
   你是家里的语音助手，用简短的中文口语回答。你不能控制家里的设备，也看不到设备状态。用户要你开关或调节设备时，不要说已经完成，请对方用设备的准确名称再说一次。
   ```
5. 进入 **设置 → 语音助手**，打开语音助手，语言选中文或英文；「对话代理」选刚添加的 LiteLLM 对话代理，并打开「优先在本地处理命令」；「语音转文字」和「文字转语音」分别选刚添加的两个 Wyoming 服务，保存
6. 点右上角的对话按钮，说或输入「打开客厅灯」，对应的灯被打开并收到回复；再问「今天适合开窗吗」，收到大模型的回答

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 添加集成时提示无法连接 | 确认步骤 2 已就绪、IP 和端口填写正确，Home Assistant 主机能访问语音主机 |
| 添加 LiteLLM 时提示无法连接或密钥无效 | 本地大模型：等步骤 2 就绪后重试，确认步骤 2 填的 Home Assistant 主机 IP 正确（换了 IP 要重新部署步骤 2）；云端大模型：核对服务地址和密钥，确认 Home Assistant 主机能访问互联网 |
| 开关设备的指令交给了大模型回答 | 在语音助手里打开「优先在本地处理命令」 |
| 开灯指令没执行，大模型却说已经打开 | 设备名称没被识别对，指令转给了大模型；按第 4 步改「指令」，大模型会请你用准确名称重说 |
| 问其他问题时只回复听不懂 | 语音助手的「对话代理」改选 LiteLLM 对话代理 |
| 语音助手里选不到语音服务 | 确认两个 Wyoming Protocol 集成都已添加成功 |
| 重新部署步骤 2 时改了端口，语音不再工作 | 删除这两个 Wyoming Protocol 集成，用新端口重新添加 |
| 指令被识别但设备没反应 | 确认指令里的名称与 Home Assistant 里设备或区域的名称一致 |

---

## 套餐: ARM64 Linux 主机 + RK3588 / RK3576 语音主机（云端大模型） {#rpi_rk_cloud}

ARM64 Linux 主机运行 Home Assistant，语音主机负责听懂语音、生成回复语音；开关设备之外的问题交给大模型回答，两台设备在同一局域网内配合工作。

| 设备 | 用途 |
|------|------|
| ARM64 Linux 主机（64 位系统，8GB 内存） | 运行 Home Assistant |
| 语音主机（下表任选一台） | 本地语音识别和语音合成 |
| Home Assistant Connect ZBT-2 | 接入 Zigbee 设备 |
| Home Assistant Voice 预览版 | 房间里的语音终端 |

| 语音主机 | 回答设备控制之外的问题 |
|------|------|
| reComputer RK3588（不带 RK1828 加速卡） | 你填写的云端大模型服务 |
| reComputer RK3576（8GB） | 你填写的云端大模型服务 |

**部署完成后你可以：**
- 用中文或英文语音控制灯光等设备，说完到识别出文字中位数 0.12 秒
- 问「今天适合开窗吗」这类问题，由大模型回答；开关设备的指令仍由 Home Assistant 在本地执行
- 把 Zigbee 传感器和开关接入 Home Assistant
- 在 iPhone 的「家庭」App 和 Siri 里控制同一批设备

**前提条件：** 两台设备在同一局域网 · 语音主机首次启动需联网下载模型 · 一个兼容 OpenAI 接口的大模型服务地址、模型名称和服务密钥

## 步骤 1: 部署 Home Assistant {#rk_ha_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

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

### 部署目标: 本机部署 {#rk_ha_local type=local device=arm64_linux device_name="ARM64 Linux 主机（64 位系统，8GB 内存）" config=devices/ha_rpi.yaml}

在当前这台 ARM64 Linux 主机上安装。

### 部署目标: 远程部署 {#rk_ha_remote type=remote device=arm64_linux device_name="ARM64 Linux 主机（64 位系统，8GB 内存）" config=devices/ha_rpi.yaml default=true}

通过网络连接 ARM64 Linux 主机安装，需要它的 IP 地址、用户名和密码。

---

---

## 步骤 2: 部署语音主机 {#rk_voice_deploy type=docker_deploy required=true config=devices/rk3588_voice.yaml}

在语音主机上安装语音识别和语音合成服务，供 Home Assistant 调用。reComputer J40 和带 RK1828 加速卡的 RK3588 同时安装本地大模型；其他语音主机使用你填写的云端大模型服务。

### 前置条件

- 可用磁盘：reComputer J40 至少 40 GB，J30 至少 20 GB，RK3588 + RK1828 至少 16 GB，RK3588 和 RK3576 至少 10 GB
- 首次启动需联网下载模型，下载完成前服务不可用
- RK3588 + RK1828：加速卡已接好供电，驱动和固件已安装（系统里能看到 `/dev/pcie-rkep-*` 设备），且卡上没有运行其他大模型
- 云端大模型：准备兼容 OpenAI 接口的服务地址（例如 `https://api.deepseek.com`）、模型名称和服务密钥；服务密钥只在步骤 3 的 Home Assistant 里填写
- 本地大模型（J40、RK3588 + RK1828）：准备 Home Assistant 主机的 IP 地址，本地大模型只接受这台主机和语音主机本机的连接

### 接线

1. 把语音主机接入与 Home Assistant 主机相同的局域网并开机
2. 端口保持默认即可：语音转文字 10300、文字转语音 10200、语音服务 8623，本地大模型 8000（J40）或 1828（RK1828）；其中某个端口已被占用时再修改
3. 本地大模型：填写 Home Assistant 主机的 IP 地址；云端大模型：填写大模型服务地址，部署时会先检查语音主机能否访问它
4. 记下语音主机的 IP 地址和端口，步骤 3 会用到
5. 点击部署

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示磁盘空间不足 | 按前置条件清理出足够的可用空间后重新部署 |
| 提示端口已被占用 | 换一个未被占用的端口后重新部署，各端口不能相同 |
| 部署后很久没有就绪 | 首次启动要先下载模型，耗时取决于网速；确认语音主机能访问互联网 |
| 提示缺少 NVIDIA 容器运行环境 | 确认 reComputer J40 / J30 刷的是完整的 JetPack 系统（含 NVIDIA 容器运行环境）后重试 |
| 提示找不到 RK1828 加速卡 | 检查加速卡供电、驱动和固件；没有加速卡时改选「RK3588（云端大模型）」 |
| 提示无法访问大模型服务 | 核对服务地址，确认语音主机能访问互联网 |
| 提示服务地址不是兼容 OpenAI 的接口 | 填服务商文档里「兼容 OpenAI」的地址 |
| 提示缺少 curl | 在语音主机上安装 curl 后重新部署 |
| 提示缺少 iptables | 在语音主机上安装 iptables 后重新部署；本地大模型靠它只对 Home Assistant 主机开放 |
| 连接设备失败 | 检查 IP 地址、用户名和密码，确认设备已开机并接入局域网 |

### 部署目标: RK3588（云端大模型） {#rk3588_remote type=remote device=rk3588 device_name="reComputer RK3588" config=devices/rk3588_voice.yaml default=true}

通过网络连接不带加速卡的 reComputer RK3588 安装，设备控制之外的问题由你填写的云端大模型回答。

### 部署目标: RK3588（云端大模型，本机部署） {#rk3588_local type=local device=rk3588 device_name="reComputer RK3588" config=devices/rk3588_voice.yaml}

在当前这台不带加速卡的 reComputer RK3588 上安装，设备控制之外的问题由你填写的云端大模型回答。

### 部署目标: RK3576（云端大模型） {#rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576（8GB）" config=devices/rk3576_voice.yaml}

通过网络连接 reComputer RK3576 安装，设备控制之外的问题由你填写的云端大模型回答。

### 部署目标: RK3576（云端大模型，本机部署） {#rk3576_local type=local device=rk3576 device_name="reComputer RK3576（8GB）" config=devices/rk3576_voice.yaml}

在当前这台 reComputer RK3576 上安装，设备控制之外的问题由你填写的云端大模型回答。

---

## 步骤 3: 接入本地语音并验证 {#rk_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

在 Home Assistant 里添加语音服务和大模型对话，然后测试。

### 部署完成

1. 打开 Home Assistant，进入 **设置 → 设备与服务 → 添加集成**，搜索 **Wyoming Protocol**；主机填语音主机的 IP 地址，端口填步骤 2 的语音转文字端口（默认 10300）
2. 再添加一个 **Wyoming Protocol** 集成，主机相同，端口填文字转语音端口（默认 10200）
3. 再添加一个 **LiteLLM** 集成：
   - reComputer J40 或 RK3588 + RK1828：服务地址填 `http://<语音主机 IP>:<本地大模型端口>`（默认 8000 或 1828），密钥留空
   - 其他语音主机：服务地址填步骤 2 填写的大模型服务地址，密钥填大模型服务商提供的服务密钥
4. 在 LiteLLM 集成里添加对话代理：模型选步骤 2 的模型名称（本地大模型只列出一项），「控制 Home Assistant」不勾选；「指令」改为下面这段，保存：

   ```
   你是家里的语音助手，用简短的中文口语回答。你不能控制家里的设备，也看不到设备状态。用户要你开关或调节设备时，不要说已经完成，请对方用设备的准确名称再说一次。
   ```
5. 进入 **设置 → 语音助手**，打开语音助手，语言选中文或英文；「对话代理」选刚添加的 LiteLLM 对话代理，并打开「优先在本地处理命令」；「语音转文字」和「文字转语音」分别选刚添加的两个 Wyoming 服务，保存
6. 点右上角的对话按钮，说或输入「打开客厅灯」，对应的灯被打开并收到回复；再问「今天适合开窗吗」，收到大模型的回答

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 添加集成时提示无法连接 | 确认步骤 2 已就绪、IP 和端口填写正确，Home Assistant 主机能访问语音主机 |
| 添加 LiteLLM 时提示无法连接或密钥无效 | 本地大模型：等步骤 2 就绪后重试，确认步骤 2 填的 Home Assistant 主机 IP 正确（换了 IP 要重新部署步骤 2）；云端大模型：核对服务地址和密钥，确认 Home Assistant 主机能访问互联网 |
| 开关设备的指令交给了大模型回答 | 在语音助手里打开「优先在本地处理命令」 |
| 开灯指令没执行，大模型却说已经打开 | 设备名称没被识别对，指令转给了大模型；按第 4 步改「指令」，大模型会请你用准确名称重说 |
| 问其他问题时只回复听不懂 | 语音助手的「对话代理」改选 LiteLLM 对话代理 |
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
