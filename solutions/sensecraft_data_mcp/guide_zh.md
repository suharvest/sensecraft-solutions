## 套餐: SenseCAP PaaS MCP 数据桥 {#default}

部署一个常驻的轻量桥接服务，通过 MCP（Model Context Protocol）把你的 SenseCAP PaaS 账号数据接入小智语音助手（或任意兼容 MCP 的宿主）。

| 设备 | 用途 |
|--------|---------|
| 任意 Docker 主机（如 reComputer R1100） | 运行 MCP 数据桥容器 |

**你将获得：**
- 暴露给语音助手的 9 个 MCP 工具：设备总览播报、单设备详细读数播报、注册设备、查询设备 key、读取最新遥测数据、查询历史遥测数据、聚合绘图数据点、浏览/读取 Arduino 代码模板
- 一条出站连接到你的小智 MCP 接入点的 WebSocket 连接——不开放任何入站端口，不对外暴露
- 凭据只在部署时传入，不会打进镜像——之后随时可以用新凭据重新部署

**前置条件：** 已安装 Docker · 一组 SenseCAP PaaS Access ID/Key（sensecap.seeed.cc → API 密钥）· 从小智智控台获取的 MCP 接入点地址

## 步骤 1: 部署 MCP 数据桥 {#deploy type=docker_deploy required=true config=devices/mcp_bridge.yaml}

用你的 SenseCAP PaaS 凭据和小智 MCP 接入点部署桥接容器。

### 部署完成

数据桥已启动，并已连接到你的小智 MCP 接入点。

#### 验证一下

1. 打开小智 App 或设备，开始一段对话
2. 说一句类似「我的设备现在怎么样」的话
3. 小智应该会调用数据桥的 `get_farm_overview` 工具，念出你有几台设备、有没有需要关注的
4. 再问一句某个具体设备，比如「大棚气象站现在怎么样」——小智应该会调用 `get_device_reading`，把这台设备当前每个通道的读数念给你听

#### 下一步

- [项目 README](https://github.com/Love4yzp/sensecraft-data-mcp) —— 完整工具列表以及手动/stdio 用法
- 要更换凭据，直接用新的 Access ID/Key 或接入点地址重新部署这一步即可，无需重新构建镜像

### 部署目标 {#local type=local config=devices/mcp_bridge.yaml default=true}

部署在你正在使用的这台机器上。

### 故障排查

| 问题 | 解决方法 |
|-------|----------|
| 找不到 Docker | 安装 Docker Desktop 并确保其正在运行 |
| 容器反复重启 | 查看日志：`docker logs sensecraft-data-mcp` —— 通常是 Access ID/Key 或接入点地址填错了 |
| 小智一直不调用工具 | 确认 MCP 接入点地址（包括 `?token=` 部分）是从小智智控台完整复制过来的 |
| 播报的时间差好几个小时 | 把"设备所在时区"填成设备实际所在的 IANA 时区（如 `Asia/Shanghai`）再重新部署。留空时国内站默认按北京时间处理，其余站点默认按 UTC 处理——不会瞎猜时区 |

### 部署目标 {#remote type=remote device_name="reComputer R1100" config=devices/mcp_bridge.yaml}

通过 SSH 部署到 reComputer（或任意 Docker 主机）。

### 故障排查

| 问题 | 解决方法 |
|-------|----------|
| SSH 连接失败 | 检查设备 IP、用户名、密码，以及设备是否已开启 SSH |
| Docker Compose 不可用 | 安装：`sudo apt-get install -y docker-compose-plugin` |
| 容器反复重启 | 在设备上查看日志：`docker logs sensecraft-data-mcp` —— 通常是 Access ID/Key 或接入点地址填错了 |
| 播报的时间差好几个小时 | 把"设备所在时区"填成设备实际所在的 IANA 时区（如 `Asia/Shanghai`）再重新部署。留空时国内站默认按北京时间处理，其余站点默认按 UTC 处理——不会瞎猜时区 |
