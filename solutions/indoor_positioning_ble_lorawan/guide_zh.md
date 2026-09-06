# 开始之前

这套系统**室内用 BLE 信标、室外用追踪器自带的 GNSS** 定位人员与资产，并画在同一张地图上。
下面三个套餐只差信标与追踪器的数量，跑的是同一个应用镜像、同一套功能。

部署仍是原来的五个硬件/软件步骤，另加两个新的配置步骤：把平面图配准到室外地图，以及配置地理围栏。
这两件事的参考资料——底图、投影的适用范围、围栏迟滞默认值、上行字段映射——集中写在这里一次，
不在每个套餐下重复。

**这不是安全认证系统。** 位置可能延迟、错误或缺失：LoRaWAN 上行本身就允许丢包，GNSS 在室内不工作，
BLE 三边定位在金属环境下会退化。不要把它当作"位置错了或没报就会伤到人"这类场景的唯一控制手段。

**应用镜像的 tag 尚未发布。** 本方案包指向
`seeedcloud/sensecraft-indoor-positioning:outdoor-2026-09-05`，由上游 `feature/outdoor` 分支构建。
执行部署步骤之前，需要先构建并推送这个 tag，或者在本地构建后按同名 tag 打标——
之前发布的镜像不含任何室外功能。

### 参考：室外地图与底图选择

面板是 `/web/map` 单页，用图层控件在 **室内** 和 **室外** 之间切换；投屏可以直接开
`/web/map?layer=outdoor`，订阅的是同一条 WebSocket。一个设备只画在两者之一——室内
Canvas 视图或室外 Leaflet 视图——不会两边都画。

预置了两种底图源：

| 源 | 什么时候用 | 前提 |
|---|---|---|
| OpenStreetMap 栅格瓦片（默认） | 运行面板的主机能联网 | 能出网访问 OSM 瓦片服务器 |
| 离线 PMTiles 归档 | 内网隔离或现场网络不可靠 | 事先构建好一个 `.pmtiles` 文件 |

高德与天地图作为禁用模板存在。它们给的是 GCJ-02 坐标，偏移纠正没有实现，位置会差出几十米。保持禁用。

构建离线归档——在有外网的机器上做，不要在现场做：

```bash
# macOS；或从 github.com/protomaps/go-pmtiles 下 release 二进制
brew install protomaps/tap/pmtiles

# 不要下载全球包再切。extract 是发 HTTP Range 请求，只拉 bbox 内的瓦片。
pmtiles extract \
  https://build.protomaps.com/20240401.pmtiles \
  data/pmtiles/demo.pmtiles \
  --bbox=113.9310,22.5230,113.9450,22.5330 \
  --maxzoom=18

pmtiles show data/pmtiles/demo.pmtiles
```

`--bbox` 是 `west,south,east,north`，十进制度。从配准原点向四周扩 1-2 km。
上面这组约 1.4 km x 1.1 km，产物几 MB。

把文件放在 compose 文件旁边的 `data/pmtiles` 目录里；它以只读方式挂到 `/app/uploads/pmtiles`，
通过现有的 `/uploads` 静态挂载对外提供。预置的 `pmtiles-offline` 源指向
`/uploads/pmtiles/demo.pmtiles`；文件名不同就改这个 URL，或者在 `dashboard_config.json` 里
覆盖 `outdoor.tileSources`。归档缺失时地图打一条 console 错误并回落到在线源。

两种底图的数据都来自 OpenStreetMap，因此 ODbL 要求的署名"© OpenStreetMap contributors"
及其到 <https://www.openstreetmap.org/copyright> 的链接必须保持可见。默认已经渲染，不要去掉。

未验证：评测过程中没有构建也没有加载过 PMTiles 归档，因为构建环境访问不到
`build.protomaps.com`。走通的是 UI 上的切换与回落路径，归档路径没有走通。

### 参考：平面图配准是怎么回事

配准用四个数把平面图钉到地球上——原点纬度、原点经度、旋转角、缩放——按地图存在
`dashboard_config.json` 里（没有数据库表，也没有迁移）。没有这四个数的地图就是纯室内，与之前一样。

变换是在原点展开的局部切平面。实测误差在 **|纬度| <= 60°、离原点 2 km 以内不超过 0.21 m**，
远在 0.7 m 预算之内；服务端 Python 与浏览器 JavaScript 两个实现在同一份 fixture 上相差 2.7e-20 度，
往返闭合 7.5e-10 m。实际影响：原点要放在建筑附近，不要放在某个站点级基准点上；纬度绝对值超过 85° 会直接拒绝配准。

配准之后，这张图的 metric 历史段与实时点会投影到与 WGS84 段同一张 Leaflet 图上。
不同坐标系的段之间永远不连线——切换点上的断口是有意的，不是渲染 bug。

### 参考：地理围栏

围栏是一个 WGS84 多边形（或多重多边形），或者"中心点 + `radius_m`"的圆。
`location_mode: geo` 的告警规则引用一个围栏和一个方向（`enter`、`exit` 或 `both`），
并且——与原来的 BLE 模式不同——围栏附近不需要任何信标。

决定告警会不会触发的默认值：

| 参数 | 默认值 | 影响 |
|---|---|---|
| 确认条件 | 新一侧连续 3 个点，跨度 >= 10 s | 少于三条上行就完成的一次穿越可能完全不报 |
| 精度门槛 | 丢弃 accuracy 差于 25 m 的点 | 这套硬件上从不生效——accuracy 恒为 null |
| 缓冲带 | 点到边界距离小于自身 accuracy 时保持原状态 | 同样从不生效，原因相同 |
| 首次观测 | 只落地 inside/outside | 重启后不会立刻补一条假告警 |
| 迟滞隔离粒度 | 按（设备, 告警规则） | 同一围栏上的两条规则各自独立计数 |

进入告警走 `tracker_checkin` 广播、离开告警走 `tracker_position_detection`，
两者都额外带一个 `geofence` 段；入库记录的 `pos_type` 是 `gps`、`beacons` 是空数组。
规则里的 `time_range` 在 geo 模式下不起作用。

### 参考：上行里的 GNSS 字段

两种接入方式映射的是同一组 measurement id：

| Measurement id | 含义 | 说明 |
|---|---|---|
| 4197 | 经度 | 用 `is not None` 校验，所以真实的 0.0 会保留 |
| 4198 | 纬度 | 两者都在才认这次 GNSS fix |
| 5002 | BLE 扫描结果（MAC + RSSI） | 同一包里有 GNSS fix 时也照常解析 |
| 3000 | 电量 | SenseCAP 侧收到它才汇总成一份报告 |
| 4200 / 5003 | SOS（5003 的事件 id 7） | |

同时带 GNSS 与 BLE 的一包生成一份组合报告，两类定位结果分别追加到两条历史轨迹上，
分别标 `coordSystem: wgs84` 与 `coordSystem: metric`。界面展示哪一种由迟滞状态机决定：
20 s 内 3 个 GNSS fix 且 15 s 没有已配置信标转室外；连续两次、每次 ≥2 个已配置信标转回室内。
不在配置里的信标不算"在室内"的证据。状态机证据不足时——设备出现后的头两个包——走简化规则：
有有效经纬度就算室外。

**`accuracy` 没有数据源。** SenseCAP 与 ChirpStack 都不发 GNSS 精度测点，
所以这个字段贯通到了末端但恒为 `null`，`alt` 同理。依赖它的东西——围栏的精度门槛与边界缓冲带——
因此在现场是空转的，只有单元测试覆盖。服务端每放行一个 accuracy 为 null 的点就打一条日志。
将来固件补上这个测点的话，结构上不用改。

### 参考：到底测了什么

针对服务端的回放实测，回路里没有真实追踪器也没有真实网关：200 个并发标签稳定，P95 828 ms；
500 标签下降档，P95 2.35 s；1000 标签 P95 4.1 s，丢失 0%、进程未崩溃；50 标签 2 s 间隔 P95 220 ms；
SOS 告警 P50 24 ms；离线判定 903 s 与 950 s，对应硬编码的 15 min 阈值。每一档跑 2-4 min，
设备是经 Tailscale 访问的 Jetson Orin Nano Super。用真实 T1000 测的相对真值定位误差还没有做。
完整条件与来源见方案介绍页。

## 套餐: 入门套件 {#starter}

适合 500 平方米以内的小型办公室或单个房间。搭建快，硬件最少。

| 设备 | 数量 | 用途 |
|------|------|------|
| SenseCAP M2 网关 | 1 | LoRaWAN 网络覆盖 |
| BC03 蓝牙信标 | 6 | 室内定位参考点 |
| SenseCAP T1000 追踪器 | 1+ | 被追踪的资产/人员，室内 BLE 扫描、室外 GNSS |

**你会得到：**
- 室内外定位画在同一张地图上
- 平面图配准到室外地图
- 进出围栏告警，围栏里不需要放信标

**覆盖范围：** 500 平方米以内 · LoRaWAN 标称覆盖 2 km

**重要：** 依赖这套系统之前，先看本指南开头的安全声明与实测边界摘要。
位置可能延迟、错误或缺失，而且这套硬件上的 `accuracy` 恒为 null。

## 步骤 1: 部署蓝牙信标 {#beacons type=manual required=true}

把蓝牙信标固定安装在室内，作为定位参考点。只靠 GNSS 覆盖的区域（院子、道路、停车场）不需要放信标。

### 接线

1. 每个区域至少放 3 个信标（三边定位），或放 1 个（只到房间级）
2. 安装高度 2.5-3 m，间距 10-15 m
3. 记录每个信标的 MAC 地址与位置

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 信标指示灯不亮 | 电池耗尽 - 更换电池 |
| 定位不准 | 信标太少或间距太大 - 增加信标密度 |
| 追踪器扫不到信标 | 信标装得太高或被遮挡 - 调整安装位置 |
| 人在楼里但一直显示"室外" | 只有已配置的信标才算室内证据 - 把该信标的 MAC 加进地图配置 |

---

## 步骤 2: 配置 LoRaWAN 网关 {#gateway type=manual required=true}

接入网关，打通追踪器与定位应用之间的无线链路。

### 接线

1. 网关上电，接入网络（有线或 WiFi）
2. 用 SenseCraft App 扫码绑定网关
3. 绿灯常亮表示就绪

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 指示灯不亮 | 供电问题 - 检查电源适配器与线缆 |
| 红灯闪烁 | 未联网 - 检查网线或 WiFi 配置 |
| App 扫码失败 | 网关未联网 - 确认网关在线 |
| 追踪器数据不上报 | 频段不匹配 - 确认网关与追踪器频段一致 |

---

## 步骤 3: 部署定位应用 {#app_server type=docker_deploy required=true config=devices/app_deploy.yaml}

本方案包指向的镜像 tag 尚未发布 - 见本指南开头的说明。

### 部署目标 {#app_server_local type=local config=devices/app_deploy.yaml default=true}

把定位应用部署到本机。

### 接线

1. 确认已安装并启动 Docker Desktop
2. 确认 5173 端口空闲
3. 要用离线底图的话，部署前把 `.pmtiles` 归档放到 compose 文件旁边的 `data/pmtiles` 目录

### 部署完成

1. 访问 `http://localhost:5173`，用 `admin` / `83EtWJUbGrPnQjdCqyKq` 登录
2. 上传平面图，填写它覆盖的实际尺寸（米）
3. 在平面图上标注信标位置（填 MAC 地址）
4. 把 LoRaWAN 网络服务器指向这台主机，或在面板里配置 SenseCAP / ChirpStack 接入

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 部署失败 | Docker 没运行 - 启动 Docker Desktop |
| 找不到镜像 | 室外版 tag 尚未发布 - 从上游分支构建并在本地打同名 tag |
| 端口被占用 | 其他程序占用 5173 - 关掉它或换端口 |
| 网页打不开 | 服务还没起完 - 等几分钟后刷新 |

### 部署目标 {#app_server_remote type=remote config=devices/app_deploy.yaml}

通过 SSH 把定位应用部署到远程服务器。

### 接线

1. 目标设备接入网络
2. 拿到设备 IP 地址
3. 拿到 SSH 凭据（用户名/密码）
4. 确认远程服务器已装 Docker
5. 要用离线底图的话，`.pmtiles` 归档最终要落在远程部署目录下的 `data/pmtiles` 里

### 部署完成

1. 访问 `http://<设备IP>:5173`，用 `admin` / `83EtWJUbGrPnQjdCqyKq` 登录
2. 上传平面图，填写它覆盖的实际尺寸（米）
3. 在平面图上标注信标位置（填 MAC 地址）
4. 把 LoRaWAN 网络服务器指向这台主机，或在面板里配置 SenseCAP / ChirpStack 接入

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | IP 或凭据不对 - 检查 IP 地址与用户名/密码 |
| 部署失败 | 远程服务器没有 Docker - 先装 Docker |
| 找不到镜像 | 室外版 tag 尚未发布 - 构建并推送，或在远程主机上 load |
| 网页打不开 | 防火墙拦截 - 在远程服务器上放行 5173 端口 |

---

## 步骤 4: 配置并激活追踪器 {#tracker type=manual required=true}

配置追踪器，并确认两种定位数据都能上来。

### 接线

1. 长按电源键 3 s 开机，绿灯闪烁表示正在入网
2. 用 SenseCraft App 连接追踪器
3. 选对 LoRaWAN 频段，并同时打开 BLE 扫描与 GNSS 定位
4. 在室内靠近信标走动，按键触发上报，确认平面图上出现位置
5. 走到室外，等到 GNSS fix，确认设备切换到室外地图

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 开机后一直闪烁 | 入网失败 - 检查网关是否在线、频段是否一致 |
| 网页上看不到追踪器 | 接入没配好 - 检查面板里的网络服务器 / SenseCAP 设置 |
| 位置不更新 | 追踪器在休眠 - 按键触发上报，或调整上报周期 |
| 室内位置显示错误 | 信标坐标配错 - 检查平面图上的信标标注 |
| 不切到室外 | 需要 20 s 内 3 个 GNSS fix 且 15 s 没有已配置信标；靠窗时室内也能定位，会来回抖 |

---

## 步骤 5: 平面图配准 {#georeference type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

把上传的平面图钉到室外地图上，让室内外轨迹共用一个视图。只有完全不需要两者同屏时才跳过。

### 前置条件

- 平面图已上传，并已填写实际尺寸（米）
- 已用 `admin` 登录 - guest 会话在配准接口上返回 403
- 站点在室外地图上可见（在线 OSM 瓦片，或你的 PMTiles 归档）

### 接线

1. 在地图下拉里选 **室外**，把视野移到站点
2. 进入配准模式并选中平面图；初猜是视图中心、正北、scale 1
3. 用 Drag / Rotate / Scale 把平面图对到建筑上；宽高比锁定
4. 核对工具条上的四个数 - 原点纬度、原点经度、旋转角、缩放 - 它们与图片双向同步
5. 保存，面板提示 "Registration saved."

原点要放在你关心的区域 2 km 以内。这是实测投影误差不超过 0.21 m 的半径。

### 部署完成

刷新浏览器，重新进入配准模式并选中同一张图：四个参数应当仍是保存值。
然后确认这张图上的设备与它的 metric 轨迹现在与 WGS84 轨迹画在同一张 Leaflet 图上，
且两段在切换点之间不连线。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 保存返回 422 | 纬度超过 85°，或 scale 为 0 / 负数 |
| 保存返回 403 | 当前是 guest 会话 - 换 admin 登录 |
| 刷新后参数丢失 | 没存上 - 检查容器里 `dashboard_config.json` 的 `maps[].map.registration` |
| 填完坐标后地图一片纯蓝 | 表单改动时视野会跟到图片上；没跟上就手动移回站点再填一次 |
| 旋转/缩放把手不出现 | 叠加层图片还没加载完 - 退出再进配准模式 |

---

## 步骤 6: 配置地理围栏告警 {#geofence type=manual required=true verify=true config=devices/geofence_setup.yaml}

用 WGS84 画一个围栏，设备进出时告警。围栏里不需要放信标。

### 前置条件

- 至少有一个追踪器在上报 GNSS 位置
- 明确你关心的方向：进入、离开，还是两者

### 接线

1. 新建围栏：GeoJSON 多边形，或者中心点加 `radius_m`
2. 新建告警规则，`location_mode` 设为 `geo`，指向该围栏，选择方向
3. 过一遍上面参考章节里的迟滞默认值 - 尤其是"连续 3 点、10 s"的确认条件
4. 制造一次穿越：带着追踪器走过边界，或者用上游仓库的 `evaluation/replay_chirpstack.py` 回放 `evaluation/traces/geofence_dwell.jsonl`

### 部署完成

出现一条进入告警和一条离开告警，各自落在新一侧的第 3 个连续点上；在边界上徘徊则一条都不出——
参考实测在边界上翻转 6 次产生 0 条告警。告警要同时出现在面板的告警列表里，
以及带 `geofence` 段的 WebSocket 广播里；入库记录的 `pos_type` 是 `gps`、`beacons` 是空数组。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 完全不告警 | 这次穿越不足 3 条上行、或不足 10 s - 把围栏画大些，或缩短上报周期 |
| 告警偏晚 | 预期行为：确认需要连续 3 个点且跨度至少 10 s |
| 重启后立刻来一条告警 | 不应该发生 - 首次观测只落地状态；出现了说明规则重复配置了 |
| `time_range` 不起作用 | 正常 - geo 模式下由围栏自己的确认取代 |
| 仍然强制要选信标 | 规则还在 BLE 模式 - 把 `location_mode` 改成 geo |

---

## 步骤 7: 打开定位面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

定位面板已就绪。点击下方在浏览器中打开。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 确认前一个部署步骤已成功，服务运行正常 |
| 主机/端口错误 | 部署到远程设备的话，用实际设备 IP 更新地址 |
| 地图下拉里没有"室外" | 跑的还是室外版之前的镜像 tag - 用室外版 tag 重新部署 |

---
### 部署完成

系统已就绪。

#### 快速验证

1. 带追踪器在室内靠近信标走动，确认它出现在平面图上
2. 走到室外，确认几个 GNSS fix 之后它切到室外地图
3. 穿过围栏边界，确认告警出现
4. 按追踪器按键，确认 SOS 告警

#### 下一步

底图、配准的适用范围、围栏默认值与上行字段映射，都在本指南开头的参考章节里。

- [查看 Wiki 文档](https://wiki.seeedstudio.com/cn/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub 仓库](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [体验在线演示](https://indoorpositioning-demo.seeed.cc/)

## 套餐: 标准配置 {#standard}

适合 500-2000 平方米的中型场地，例如仓库、办公楼或门店。

| 设备 | 数量 | 用途 |
|------|------|------|
| SenseCAP M2 网关 | 1 | LoRaWAN 网络覆盖 |
| BC03 蓝牙信标 | 15 | 室内定位参考点 |
| SenseCAP T1000 追踪器 | 3+ | 被追踪的资产/人员，室内 BLE 扫描、室外 GNSS |

**你会得到：**
- 室内外定位画在同一张地图上
- 平面图配准到室外地图
- 进出围栏告警，围栏里不需要放信标

**覆盖范围：** 500-2000 平方米 · LoRaWAN 标称覆盖 2 km

**重要：** 依赖这套系统之前，先看本指南开头的安全声明与实测边界摘要。
位置可能延迟、错误或缺失，而且这套硬件上的 `accuracy` 恒为 null。

## 步骤 1: 部署蓝牙信标 {#beacons_standard type=manual required=true}

把蓝牙信标固定安装在室内，作为定位参考点。只靠 GNSS 覆盖的区域（院子、道路、停车场）不需要放信标。

### 接线

1. 每个区域至少放 3 个信标（三边定位），或放 1 个（只到房间级）
2. 安装高度 2.5-3 m，间距 10-15 m
3. 记录每个信标的 MAC 地址与位置

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 信标指示灯不亮 | 电池耗尽 - 更换电池 |
| 定位不准 | 信标太少或间距太大 - 增加信标密度 |
| 追踪器扫不到信标 | 信标装得太高或被遮挡 - 调整安装位置 |
| 人在楼里但一直显示"室外" | 只有已配置的信标才算室内证据 - 把该信标的 MAC 加进地图配置 |

---

## 步骤 2: 配置 LoRaWAN 网关 {#gateway_standard type=manual required=true}

接入网关，打通追踪器与定位应用之间的无线链路。

### 接线

1. 网关上电，接入网络（有线或 WiFi）
2. 用 SenseCraft App 扫码绑定网关
3. 绿灯常亮表示就绪

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 指示灯不亮 | 供电问题 - 检查电源适配器与线缆 |
| 红灯闪烁 | 未联网 - 检查网线或 WiFi 配置 |
| App 扫码失败 | 网关未联网 - 确认网关在线 |
| 追踪器数据不上报 | 频段不匹配 - 确认网关与追踪器频段一致 |

---

## 步骤 3: 部署定位应用 {#app_server_standard type=docker_deploy required=true config=devices/app_deploy.yaml}

本方案包指向的镜像 tag 尚未发布 - 见本指南开头的说明。

### 部署目标 {#app_server_local type=local config=devices/app_deploy.yaml default=true}

把定位应用部署到本机。

### 接线

1. 确认已安装并启动 Docker Desktop
2. 确认 5173 端口空闲
3. 要用离线底图的话，部署前把 `.pmtiles` 归档放到 compose 文件旁边的 `data/pmtiles` 目录

### 部署完成

1. 访问 `http://localhost:5173`，用 `admin` / `83EtWJUbGrPnQjdCqyKq` 登录
2. 上传平面图，填写它覆盖的实际尺寸（米）
3. 在平面图上标注信标位置（填 MAC 地址）
4. 把 LoRaWAN 网络服务器指向这台主机，或在面板里配置 SenseCAP / ChirpStack 接入

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 部署失败 | Docker 没运行 - 启动 Docker Desktop |
| 找不到镜像 | 室外版 tag 尚未发布 - 从上游分支构建并在本地打同名 tag |
| 端口被占用 | 其他程序占用 5173 - 关掉它或换端口 |
| 网页打不开 | 服务还没起完 - 等几分钟后刷新 |

### 部署目标 {#app_server_remote type=remote config=devices/app_deploy.yaml}

通过 SSH 把定位应用部署到远程服务器。

### 接线

1. 目标设备接入网络
2. 拿到设备 IP 地址
3. 拿到 SSH 凭据（用户名/密码）
4. 确认远程服务器已装 Docker
5. 要用离线底图的话，`.pmtiles` 归档最终要落在远程部署目录下的 `data/pmtiles` 里

### 部署完成

1. 访问 `http://<设备IP>:5173`，用 `admin` / `83EtWJUbGrPnQjdCqyKq` 登录
2. 上传平面图，填写它覆盖的实际尺寸（米）
3. 在平面图上标注信标位置（填 MAC 地址）
4. 把 LoRaWAN 网络服务器指向这台主机，或在面板里配置 SenseCAP / ChirpStack 接入

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | IP 或凭据不对 - 检查 IP 地址与用户名/密码 |
| 部署失败 | 远程服务器没有 Docker - 先装 Docker |
| 找不到镜像 | 室外版 tag 尚未发布 - 构建并推送，或在远程主机上 load |
| 网页打不开 | 防火墙拦截 - 在远程服务器上放行 5173 端口 |

---

## 步骤 4: 配置并激活追踪器 {#tracker_standard type=manual required=true}

配置追踪器，并确认两种定位数据都能上来。

### 接线

1. 长按电源键 3 s 开机，绿灯闪烁表示正在入网
2. 用 SenseCraft App 连接追踪器
3. 选对 LoRaWAN 频段，并同时打开 BLE 扫描与 GNSS 定位
4. 在室内靠近信标走动，按键触发上报，确认平面图上出现位置
5. 走到室外，等到 GNSS fix，确认设备切换到室外地图

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 开机后一直闪烁 | 入网失败 - 检查网关是否在线、频段是否一致 |
| 网页上看不到追踪器 | 接入没配好 - 检查面板里的网络服务器 / SenseCAP 设置 |
| 位置不更新 | 追踪器在休眠 - 按键触发上报，或调整上报周期 |
| 室内位置显示错误 | 信标坐标配错 - 检查平面图上的信标标注 |
| 不切到室外 | 需要 20 s 内 3 个 GNSS fix 且 15 s 没有已配置信标；靠窗时室内也能定位，会来回抖 |

---

## 步骤 5: 平面图配准 {#georeference_standard type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

把上传的平面图钉到室外地图上，让室内外轨迹共用一个视图。只有完全不需要两者同屏时才跳过。

### 前置条件

- 平面图已上传，并已填写实际尺寸（米）
- 已用 `admin` 登录 - guest 会话在配准接口上返回 403
- 站点在室外地图上可见（在线 OSM 瓦片，或你的 PMTiles 归档）

### 接线

1. 在地图下拉里选 **室外**，把视野移到站点
2. 进入配准模式并选中平面图；初猜是视图中心、正北、scale 1
3. 用 Drag / Rotate / Scale 把平面图对到建筑上；宽高比锁定
4. 核对工具条上的四个数 - 原点纬度、原点经度、旋转角、缩放 - 它们与图片双向同步
5. 保存，面板提示 "Registration saved."

原点要放在你关心的区域 2 km 以内。这是实测投影误差不超过 0.21 m 的半径。

### 部署完成

刷新浏览器，重新进入配准模式并选中同一张图：四个参数应当仍是保存值。
然后确认这张图上的设备与它的 metric 轨迹现在与 WGS84 轨迹画在同一张 Leaflet 图上，
且两段在切换点之间不连线。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 保存返回 422 | 纬度超过 85°，或 scale 为 0 / 负数 |
| 保存返回 403 | 当前是 guest 会话 - 换 admin 登录 |
| 刷新后参数丢失 | 没存上 - 检查容器里 `dashboard_config.json` 的 `maps[].map.registration` |
| 填完坐标后地图一片纯蓝 | 表单改动时视野会跟到图片上；没跟上就手动移回站点再填一次 |
| 旋转/缩放把手不出现 | 叠加层图片还没加载完 - 退出再进配准模式 |

---

## 步骤 6: 配置地理围栏告警 {#geofence_standard type=manual required=true verify=true config=devices/geofence_setup.yaml}

用 WGS84 画一个围栏，设备进出时告警。围栏里不需要放信标。

### 前置条件

- 至少有一个追踪器在上报 GNSS 位置
- 明确你关心的方向：进入、离开，还是两者

### 接线

1. 新建围栏：GeoJSON 多边形，或者中心点加 `radius_m`
2. 新建告警规则，`location_mode` 设为 `geo`，指向该围栏，选择方向
3. 过一遍上面参考章节里的迟滞默认值 - 尤其是"连续 3 点、10 s"的确认条件
4. 制造一次穿越：带着追踪器走过边界，或者用上游仓库的 `evaluation/replay_chirpstack.py` 回放 `evaluation/traces/geofence_dwell.jsonl`

### 部署完成

出现一条进入告警和一条离开告警，各自落在新一侧的第 3 个连续点上；在边界上徘徊则一条都不出——
参考实测在边界上翻转 6 次产生 0 条告警。告警要同时出现在面板的告警列表里，
以及带 `geofence` 段的 WebSocket 广播里；入库记录的 `pos_type` 是 `gps`、`beacons` 是空数组。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 完全不告警 | 这次穿越不足 3 条上行、或不足 10 s - 把围栏画大些，或缩短上报周期 |
| 告警偏晚 | 预期行为：确认需要连续 3 个点且跨度至少 10 s |
| 重启后立刻来一条告警 | 不应该发生 - 首次观测只落地状态；出现了说明规则重复配置了 |
| `time_range` 不起作用 | 正常 - geo 模式下由围栏自己的确认取代 |
| 仍然强制要选信标 | 规则还在 BLE 模式 - 把 `location_mode` 改成 geo |

---

## 步骤 7: 打开定位面板 {#dashboard_standard type=web_dashboard required=true config=devices/dashboard.yaml}

定位面板已就绪。点击下方在浏览器中打开。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 确认前一个部署步骤已成功，服务运行正常 |
| 主机/端口错误 | 部署到远程设备的话，用实际设备 IP 更新地址 |
| 地图下拉里没有"室外" | 跑的还是室外版之前的镜像 tag - 用室外版 tag 重新部署 |

---
### 部署完成

系统已就绪。

#### 快速验证

1. 带追踪器在室内靠近信标走动，确认它出现在平面图上
2. 走到室外，确认几个 GNSS fix 之后它切到室外地图
3. 穿过围栏边界，确认告警出现
4. 按追踪器按键，确认 SOS 告警

#### 下一步

底图、配准的适用范围、围栏默认值与上行字段映射，都在本指南开头的参考章节里。

- [查看 Wiki 文档](https://wiki.seeedstudio.com/cn/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub 仓库](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [体验在线演示](https://indoorpositioning-demo.seeed.cc/)

## 套餐: 企业版 {#enterprise}

适合 2000 平方米以上的大型园区、多楼层建筑，以及室内外都要覆盖的站点。

| 设备 | 数量 | 用途 |
|------|------|------|
| SenseCAP M2 网关 | 1 | LoRaWAN 网络覆盖 |
| BC03 蓝牙信标 | 30 | 室内定位参考点 |
| SenseCAP T1000 追踪器 | 10+ | 被追踪的资产/人员，室内 BLE 扫描、室外 GNSS |

**你会得到：**
- 室内外定位画在同一张地图上
- 平面图配准到室外地图
- 进出围栏告警，围栏里不需要放信标

**覆盖范围：** 2000 平方米以上 · LoRaWAN 标称覆盖 2 km

**重要：** 依赖这套系统之前，先看本指南开头的安全声明与实测边界摘要。
位置可能延迟、错误或缺失，而且这套硬件上的 `accuracy` 恒为 null。

## 步骤 1: 部署蓝牙信标 {#beacons_enterprise type=manual required=true}

把蓝牙信标固定安装在室内，作为定位参考点。只靠 GNSS 覆盖的区域（院子、道路、停车场）不需要放信标。

### 接线

1. 每个区域至少放 3 个信标（三边定位），或放 1 个（只到房间级）
2. 安装高度 2.5-3 m，间距 10-15 m
3. 记录每个信标的 MAC 地址与位置

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 信标指示灯不亮 | 电池耗尽 - 更换电池 |
| 定位不准 | 信标太少或间距太大 - 增加信标密度 |
| 追踪器扫不到信标 | 信标装得太高或被遮挡 - 调整安装位置 |
| 人在楼里但一直显示"室外" | 只有已配置的信标才算室内证据 - 把该信标的 MAC 加进地图配置 |

---

## 步骤 2: 配置 LoRaWAN 网关 {#gateway_enterprise type=manual required=true}

接入网关，打通追踪器与定位应用之间的无线链路。

### 接线

1. 网关上电，接入网络（有线或 WiFi）
2. 用 SenseCraft App 扫码绑定网关
3. 绿灯常亮表示就绪

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 指示灯不亮 | 供电问题 - 检查电源适配器与线缆 |
| 红灯闪烁 | 未联网 - 检查网线或 WiFi 配置 |
| App 扫码失败 | 网关未联网 - 确认网关在线 |
| 追踪器数据不上报 | 频段不匹配 - 确认网关与追踪器频段一致 |

---

## 步骤 3: 部署定位应用 {#app_server_enterprise type=docker_deploy required=true config=devices/app_deploy.yaml}

本方案包指向的镜像 tag 尚未发布 - 见本指南开头的说明。

### 部署目标 {#app_server_local type=local config=devices/app_deploy.yaml default=true}

把定位应用部署到本机。

### 接线

1. 确认已安装并启动 Docker Desktop
2. 确认 5173 端口空闲
3. 要用离线底图的话，部署前把 `.pmtiles` 归档放到 compose 文件旁边的 `data/pmtiles` 目录

### 部署完成

1. 访问 `http://localhost:5173`，用 `admin` / `83EtWJUbGrPnQjdCqyKq` 登录
2. 上传平面图，填写它覆盖的实际尺寸（米）
3. 在平面图上标注信标位置（填 MAC 地址）
4. 把 LoRaWAN 网络服务器指向这台主机，或在面板里配置 SenseCAP / ChirpStack 接入

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 部署失败 | Docker 没运行 - 启动 Docker Desktop |
| 找不到镜像 | 室外版 tag 尚未发布 - 从上游分支构建并在本地打同名 tag |
| 端口被占用 | 其他程序占用 5173 - 关掉它或换端口 |
| 网页打不开 | 服务还没起完 - 等几分钟后刷新 |

### 部署目标 {#app_server_remote type=remote config=devices/app_deploy.yaml}

通过 SSH 把定位应用部署到远程服务器。

### 接线

1. 目标设备接入网络
2. 拿到设备 IP 地址
3. 拿到 SSH 凭据（用户名/密码）
4. 确认远程服务器已装 Docker
5. 要用离线底图的话，`.pmtiles` 归档最终要落在远程部署目录下的 `data/pmtiles` 里

### 部署完成

1. 访问 `http://<设备IP>:5173`，用 `admin` / `83EtWJUbGrPnQjdCqyKq` 登录
2. 上传平面图，填写它覆盖的实际尺寸（米）
3. 在平面图上标注信标位置（填 MAC 地址）
4. 把 LoRaWAN 网络服务器指向这台主机，或在面板里配置 SenseCAP / ChirpStack 接入

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | IP 或凭据不对 - 检查 IP 地址与用户名/密码 |
| 部署失败 | 远程服务器没有 Docker - 先装 Docker |
| 找不到镜像 | 室外版 tag 尚未发布 - 构建并推送，或在远程主机上 load |
| 网页打不开 | 防火墙拦截 - 在远程服务器上放行 5173 端口 |

---

## 步骤 4: 配置并激活追踪器 {#tracker_enterprise type=manual required=true}

配置追踪器，并确认两种定位数据都能上来。

### 接线

1. 长按电源键 3 s 开机，绿灯闪烁表示正在入网
2. 用 SenseCraft App 连接追踪器
3. 选对 LoRaWAN 频段，并同时打开 BLE 扫描与 GNSS 定位
4. 在室内靠近信标走动，按键触发上报，确认平面图上出现位置
5. 走到室外，等到 GNSS fix，确认设备切换到室外地图

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 开机后一直闪烁 | 入网失败 - 检查网关是否在线、频段是否一致 |
| 网页上看不到追踪器 | 接入没配好 - 检查面板里的网络服务器 / SenseCAP 设置 |
| 位置不更新 | 追踪器在休眠 - 按键触发上报，或调整上报周期 |
| 室内位置显示错误 | 信标坐标配错 - 检查平面图上的信标标注 |
| 不切到室外 | 需要 20 s 内 3 个 GNSS fix 且 15 s 没有已配置信标；靠窗时室内也能定位，会来回抖 |

---

## 步骤 5: 平面图配准 {#georeference_enterprise type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

把上传的平面图钉到室外地图上，让室内外轨迹共用一个视图。只有完全不需要两者同屏时才跳过。

### 前置条件

- 平面图已上传，并已填写实际尺寸（米）
- 已用 `admin` 登录 - guest 会话在配准接口上返回 403
- 站点在室外地图上可见（在线 OSM 瓦片，或你的 PMTiles 归档）

### 接线

1. 在地图下拉里选 **室外**，把视野移到站点
2. 进入配准模式并选中平面图；初猜是视图中心、正北、scale 1
3. 用 Drag / Rotate / Scale 把平面图对到建筑上；宽高比锁定
4. 核对工具条上的四个数 - 原点纬度、原点经度、旋转角、缩放 - 它们与图片双向同步
5. 保存，面板提示 "Registration saved."

原点要放在你关心的区域 2 km 以内。这是实测投影误差不超过 0.21 m 的半径。

### 部署完成

刷新浏览器，重新进入配准模式并选中同一张图：四个参数应当仍是保存值。
然后确认这张图上的设备与它的 metric 轨迹现在与 WGS84 轨迹画在同一张 Leaflet 图上，
且两段在切换点之间不连线。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 保存返回 422 | 纬度超过 85°，或 scale 为 0 / 负数 |
| 保存返回 403 | 当前是 guest 会话 - 换 admin 登录 |
| 刷新后参数丢失 | 没存上 - 检查容器里 `dashboard_config.json` 的 `maps[].map.registration` |
| 填完坐标后地图一片纯蓝 | 表单改动时视野会跟到图片上；没跟上就手动移回站点再填一次 |
| 旋转/缩放把手不出现 | 叠加层图片还没加载完 - 退出再进配准模式 |

---

## 步骤 6: 配置地理围栏告警 {#geofence_enterprise type=manual required=true verify=true config=devices/geofence_setup.yaml}

用 WGS84 画一个围栏，设备进出时告警。围栏里不需要放信标。

### 前置条件

- 至少有一个追踪器在上报 GNSS 位置
- 明确你关心的方向：进入、离开，还是两者

### 接线

1. 新建围栏：GeoJSON 多边形，或者中心点加 `radius_m`
2. 新建告警规则，`location_mode` 设为 `geo`，指向该围栏，选择方向
3. 过一遍上面参考章节里的迟滞默认值 - 尤其是"连续 3 点、10 s"的确认条件
4. 制造一次穿越：带着追踪器走过边界，或者用上游仓库的 `evaluation/replay_chirpstack.py` 回放 `evaluation/traces/geofence_dwell.jsonl`

### 部署完成

出现一条进入告警和一条离开告警，各自落在新一侧的第 3 个连续点上；在边界上徘徊则一条都不出——
参考实测在边界上翻转 6 次产生 0 条告警。告警要同时出现在面板的告警列表里，
以及带 `geofence` 段的 WebSocket 广播里；入库记录的 `pos_type` 是 `gps`、`beacons` 是空数组。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 完全不告警 | 这次穿越不足 3 条上行、或不足 10 s - 把围栏画大些，或缩短上报周期 |
| 告警偏晚 | 预期行为：确认需要连续 3 个点且跨度至少 10 s |
| 重启后立刻来一条告警 | 不应该发生 - 首次观测只落地状态；出现了说明规则重复配置了 |
| `time_range` 不起作用 | 正常 - geo 模式下由围栏自己的确认取代 |
| 仍然强制要选信标 | 规则还在 BLE 模式 - 把 `location_mode` 改成 geo |

---

## 步骤 7: 打开定位面板 {#dashboard_enterprise type=web_dashboard required=true config=devices/dashboard.yaml}

定位面板已就绪。点击下方在浏览器中打开。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 确认前一个部署步骤已成功，服务运行正常 |
| 主机/端口错误 | 部署到远程设备的话，用实际设备 IP 更新地址 |
| 地图下拉里没有"室外" | 跑的还是室外版之前的镜像 tag - 用室外版 tag 重新部署 |

---
### 部署完成

系统已就绪。

#### 快速验证

1. 带追踪器在室内靠近信标走动，确认它出现在平面图上
2. 走到室外，确认几个 GNSS fix 之后它切到室外地图
3. 穿过围栏边界，确认告警出现
4. 按追踪器按键，确认 SOS 告警

#### 下一步

底图、配准的适用范围、围栏默认值与上行字段映射，都在本指南开头的参考章节里。

- [查看 Wiki 文档](https://wiki.seeedstudio.com/cn/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub 仓库](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [体验在线演示](https://indoorpositioning-demo.seeed.cc/)
