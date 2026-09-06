## 套餐: 单目深度估计 {#default}

在 reCamera 自己的 TPU 上跑单目深度模型。输入一张普通图像，输出稠密的相对深度图——
不需要双目，也不需要深度相机。

| 设备 | 作用 |
|------|------|
| reCamera | 运行深度模型并推流 |

**你会得到：**
- RTSP 视频流，右下角带彩色深度预览
- MQTT：逐帧百分位、近距离面积占比、3x3 方位近度网格
- Home Assistant 的近距离面积与近距离存在两个实体

**前置条件：** 一台通过 USB 或网络可达的 reCamera，以及一个物体距离差异明显的场景。
对着空白墙面或天花板会得到一张平坦、没有信息量的深度图——这是模型已知的弱项，不是故障。

## 步骤 1: 安装应用与模型 {#deploy type=recamera_cpp required=true config=devices/recamera_depth.yaml}

安装 `.deb`，并把深度模型放到 `/userdata/local/models/`。

### 连接

1. 用 USB-C 连接 reCamera，或确认它在网络上可达
2. 填入 IP 地址（USB 连接时是 `192.168.42.1`）和 `recamera` 用户的 SSH 密码
3. 执行部署

### 设备上会多出什么

| 路径 | 内容 |
|------|------|
| `/usr/local/bin/depth-estimation` | 应用本体 |
| `/etc/init.d/K92depth-estimation` | init 脚本，停用状态 |
| `/userdata/local/models/fastdepth_224_bf16.cvimodel` | 模型，2.9 MB |

init 脚本刻意以停用状态安装（`K92` 而非 `S92`）。同一时间只能有一个应用占用摄像头，
所以启动由控制台负责。

## 步骤 2: 在控制台启动 {#start type=manual required=true}

在浏览器打开相机的控制台，在应用画廊里启用**单目深度估计**。

如果顶部显示 **Node-RED 模式**横幅，先切回 Console 模式。Node-RED 模式下画廊应用会被
停用；而且有一个 supervisor 脚本在看着 Node-RED，手动停掉会被拉回来，复活的 Node-RED
会和应用抢摄像头。

## 步骤 3: 验证输出 {#verify type=manual required=false verify=true}

### 视频流

用 VLC 或任意 VMS 打开 `rtsp://<相机IP>:8554/live0`。深度预览在右下角：红色近，蓝色远。

### 数值

订阅 `recamera/depth-estimation/results`：

```json
{
  "depth": {
    "unit": "relative",
    "smaller_is_nearer": true,
    "p02": 0.949, "p50": 1.531, "p98": 2.672,
    "near_ratio": 0.346,
    "near_present": true,
    "zones": [0.49, 0.27, 1.00,
              0.74, 0.78, 0.98,
              0.77, 0.80, 0.96]
  }
}
```

`zones` 是按阅读顺序排列的 3x3 网格，每格取值 0（远）到 1（画面内最近）。
上面这组数里右列最近。

### 先校验一次

站到画面一侧，确认那一侧读数更近。如果整张图都很平，先看场景再怀疑模型——大面积
无纹理表面确实不足以让它工作。

**不要把这些数字换算成距离。** 它们是相对排序，没有米制含义。

### 故障排查

| 现象 | 处理 |
|------|------|
| 应用启动后立刻退出 | 模型文件缺失或路径不对，检查 `/userdata/local/models/` |
| 画面卡住，日志出现 `get chn frame fail` | VPSS 管线挂死。重启应用无法恢复，需重启相机。常见触发是两个进程同时占用摄像头，最多见的是 Node-RED 被拉起 |
| 深度图很平 | 把相机对准有真实纵深的场景。空白墙面、天花板、玻璃和天空是已知弱项 |
| 画廊里看不到应用 | 控制台只扫描 `/userdata/local/apps/`，重新执行一次部署 |
