基于 KNN 预测模型的暖通空调能源优化系统，支持 OPC-UA 集成。

## 套餐: 标准部署 {#default}

部署一套基于 KNN 算法的暖通优化系统，从历史数据中学习并给出最优参数建议。

| 设备 | 用途 |
|------|------|
| reComputer R1100 | 边缘计算设备，内置 Docker |

**部署完成后你可以：**
- 获得 AI 根据历史数据给出的温度调节建议
- 通过 OPC-UA 对接工业暖通控制器
- 通过 Web 面板监控和调参

**前提条件：** Docker 已安装 · OPC-UA 控制器（或用内置模拟器测试）

## 步骤 1: 暖通控制系统 {#hvac type=docker_deploy required=true config=devices/deploy.yaml}

部署智能温控优化服务，自动从建筑数据中学习最佳温度设置。

### 部署目标 {#hvac_local type=local config=devices/deploy.yaml default=true}

点击下方"部署"按钮，系统将自动在本机启动暖通控制服务。

### 接线

![接线图](gallery/architecture.svg)

1. 确保 Docker 已安装并运行
2. 点击部署启动容器
3. 通过 localhost:8280 访问 Web 界面

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| Docker 未运行 | 启动 Docker Desktop 应用 |
| 端口 8280 被占用 | 关闭占用该端口的程序，或修改配置使用其他端口 |
| 容器启动后停止 | 执行 `docker logs missionpack_knn` 查看错误日志 |
| 网页打不开 | 等待 30 秒让服务完全启动 |

### 部署目标 {#hvac_remote type=remote config=devices/deploy.yaml}

点击下方"部署"按钮，系统将自动把暖通控制服务部署到远程设备。

### 接线

![接线图](gallery/recomputer.svg)

1. 通过 SSH 连接远程设备
2. 远程部署 Docker 容器
3. 通过设备 IP:8280 访问 Web 界面

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址和用户名密码是否正确 |
| 远程设备无 Docker | 先在远程设备上安装 Docker |
| 部署超时 | 检查远程设备网络，确保能访问镜像仓库 |
| 网页打不开 | 检查防火墙是否开放 8280 端口 |

## 步骤 2: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

HVAC 控制面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |
### 部署完成

暖通控制系统已就绪！

#### 访问地址

http://\<服务器IP\>:8280

#### 下一步

1. 连接 OPC-UA 服务器（或使用内置模拟器）
2. 上传训练数据
3. 配置参数

#### 常用命令

`docker logs missionpack_knn` 查看日志
