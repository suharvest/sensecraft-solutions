## 套餐: Rockchip NPU —— RK3588 / RK3576 {#p1_rockchip}

reComputer RK3588 或 RK3576 在 NPU 上运行商品检测和嵌入，一台 Linux 服务器运行注册服务、管理界面、MQTT broker 和商品库。

- **服务器：** 一台装有 Docker 的 Linux 服务器，不需要 GPU。
- **摄像头：** RTSP 或 USB 摄像头，对准收银台或货架。
- **模型转换：** 一台 x86_64 机器，rknn-toolkit2 不能在板卡上运行。
- **模型许可：** 检测器和嵌入模型仅限非商用，不随本方案提供；商用部署需要用自采或许可宽松的数据重训。

## 步骤 1: 部署注册管理端 {#p1_console type=docker_deploy required=true config=devices/console_stack.yaml}

在服务器上启动注册服务、管理界面和 MQTT broker，并设置角色 token。

### 前置条件

- 一台装有 Docker 和 compose 插件的 Linux 服务器，识别设备能访问到它。
- 至少设置一个 admin token，服务不允许匿名访问。
- 需要从本地网络之外访问管理界面时，在前面加一个 TLS 反向代理。
- 默认使用已发布的镜像；使用自建镜像时覆盖 `RETAIL_SERVER_IMAGE` 和 `RETAIL_WEB_IMAGE`。

### 故障排查

| 现象 | 处理 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 检查服务器能否访问镜像仓库；使用自建镜像时先在本机构建。 |
| 找不到 `docker compose` | 安装 `docker-compose-plugin`。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 校验没有生效，停止使用并检查配置。 |
| 带 admin token 的 `GET /v1/gallery` 返回空库 | 首次注册前属正常。 |
| 8089 端口被占用 | 修改服务端口，设备端配置使用同一个端口。 |

### 部署目标 {#p1_console_remote type=remote config=devices/console_stack.yaml default=true}

部署到识别设备可以访问的一台 Linux 服务器。

### 部署目标 {#p1_console_local type=local config=devices/console_stack.yaml}

部署到这台电脑。识别设备必须能访问这台电脑的 IP。

## 步骤 2: 放置嵌入模型 {#p1_embed type=manual required=true config=devices/place_embedder.yaml}

把 DINOv2-base 嵌入模型放到管理端的模型目录，并启用它。

### 前置条件

- 步骤 1 的管理端已部署。
- `dinov2b_arcface_products10k_224_b1.onnx`（348 MB，sha256 `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`），需自行获取，仅限非商用。
- 服务器上 350 MB 可用空间。

### 故障排查

| 现象 | 处理 |
|---|---|
| 注册成功，但每次检索都返回错的 SKU | 嵌入模型没有启用。设置 `RETAIL_EMBEDDER=onnx`，重启服务，然后重新注册所有 SKU。 |
| 设置 `RETAIL_EMBEDDER=onnx` 后 `server` 容器立刻退出 | 确认 `RETAIL_EMBEDDER_ONNX` 已填写，文件在 `assets/console/models/` 里且文件名一致。 |
| 换模型前后注册的商品库对不上 | 不同模型的商品库不能混用，用新模型重新注册所有 SKU。 |
| 计划商用部署 | 用自采或许可宽松的数据重训嵌入模型，并重建商品库。 |

## 步骤 3: 注册 SKU {#p1_register type=web_dashboard required=true config=devices/register_sku.yaml}

在管理界面的商品库中，为每个 SKU 上传 3 到 8 张图完成注册，每次注册生成一个新的商品库版本。

### 前置条件

- 步骤 1 的 admin token。
- 每个 SKU 3 到 8 张图，至少包括正面、背面、侧面，覆盖两种光照。
- 先确定嵌入模型，之后更换需要重建所有商品库版本。

### 故障排查

| 现象 | 处理 |
|---|---|
| 注册被拒，提示图片少于三张 | 至少上传 3 张。 |
| 同一个 sku_id 返回 409 | 需要替换时带 `replace=true`。 |
| 出了新版本，但设备仍然认不出这个 SKU | 设备端拉取、校验并切换商品库版本的功能尚未实现。 |
| top-1 明显偏低 | 先增加每个 SKU 的注册图数量；仍偏低时用现场图片微调模型。 |

## 步骤 4: 在 Rockchip 上转换并核对检测器 {#p1_convert type=manual required=true config=devices/rk3588_convert.yaml}

在 x86_64 主机上把检测器 ONNX 转成 `.rknn`，拷到板卡上。

### 前置条件

- x86_64 机器装有 rknn-toolkit2 2.3.2、onnx 1.16.1、setuptools 低于 81。
- toolkit 版本与板卡上 `librknnrt.so` 版本一致，不一致时可能加载成功但结果错误。
- 检测器 ONNX，需自行获取，仅限学术与非商用。
- 步骤 2 的嵌入模型 ONNX。
- 设备端为检测和嵌入分配不同的 NPU 核：`RETAIL_RKNN_DET_CORE_MASK=2`、`RETAIL_RKNN_EMBED_CORE_MASK=01`，不要用 `AUTO`。

### 故障排查

| 现象 | 处理 |
|---|---|
| `load_onnx` 在 `onnx.mapping` 上失败 | 安装 onnx 1.16.1。 |
| 找不到 `pkg_resources` | 把 setuptools 降到 81 以下。 |
| INT8 一致率明显低于 98% | 校准图从整个验证集等间隔抽取，不要按文件名取前 N 张。 |
| 板卡上没有 cv2 和 PIL | 在其他机器上做 letterbox 预处理，打包成 `(N, 640, 640, 3)` uint8 BGR 的 `.npy`；设备端只需要 numpy 和 rknnlite。 |

## 步骤 5: 验证注册、检索与设备产物 {#p1_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

验证管理端注册与下载，并核对转换后的模型与 CPU 结果一致。

### 前置条件

- 步骤 1 到 4 已完成。
- 上游仓库克隆，已执行 `uv sync`。
- 自己 SKU 的照片，使用未注册过的角度拍摄。

### 部署完成

#### 快速验证

- `uv run python tools/verify_software_loop.py` 通过。
- 管理端带 admin token 时每注册一次版本号加一，不带 token 时返回 401 或 403。
- `GET /v1/gallery/current/download` 返回的 tar.gz 中 SHA256SUMS 校验通过。
- `.rknn` 与 CPU 结果的检测框一致率（IoU ≥ 0.5）：fp16 接近 99.85%，INT8 接近 98.35%。

#### 后续步骤

- 用自己货架或收银台的数据微调两个模型。
- 设备端进程 `platforms/rk3588/runtime.py`（配置 `platforms/rk3588/runtime.yaml`）串联检测、嵌入、检索与上报，本套餐不负责部署和托管它。
- 用真实摄像头和门店流量测量端到端延迟。

### 故障排查

| 现象 | 处理 |
|---|---|
| 检测框一致率远低于参考值 | 检查解码路径和输出布局。 |
| 软件闭环通过但板卡上不工作 | 软件闭环只验证协议，板卡问题按步骤 4 排查。 |
| 商品库在服务器上校验通过、在设备上不通过 | 对比两边的 sha256，重新传输文件。 |

## 套餐: reComputer R2000（Hailo-8）—— 检测上 NPU，嵌入留 CPU {#p2_pi5_hailo}

reComputer R2000（Hailo-8）在 NPU 上运行商品检测、在 CPU 上运行嵌入，一台 Linux 服务器运行注册服务、管理界面、MQTT broker 和商品库。

- **服务器：** 一台装有 Docker 的 Linux 服务器，不需要 GPU。
- **摄像头：** RTSP 或 USB 摄像头，对准收银台或货架。
- **模型编译：** 一台 x86_64 机器，Hailo Dataflow Compiler 不能在设备上运行。
- **模型许可：** 检测器和嵌入模型仅限非商用，不随本方案提供；商用部署需要用自采或许可宽松的数据重训。
- **限制：** 本套餐目前没有串联检测、嵌入、检索与上报的设备端程序，需自行编写。

## 步骤 1: 部署注册管理端 {#p2_console type=docker_deploy required=true config=devices/console_stack.yaml}

在设备能访问的服务器上启动注册服务、管理界面和 MQTT broker。

### 前置条件

- 一台装有 Docker 和 compose 插件的 Linux 服务器。
- 至少设置一个 admin token，服务不允许匿名访问。
- 需要从本地网络之外访问管理界面时，在前面加一个 TLS 反向代理。
- 默认使用已发布的镜像；使用自建镜像时覆盖 `RETAIL_SERVER_IMAGE` 和 `RETAIL_WEB_IMAGE`。

### 故障排查

| 现象 | 处理 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 检查服务器能否访问镜像仓库；使用自建镜像时先在本机构建。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 校验没有生效，停止使用并检查配置。 |
| 设备访问不到服务端口 | 在设备上直接测试服务端口，设备从该端口拉取商品库。 |
| 8089 端口被占用 | 修改服务端口，设备端配置使用同一个端口。 |

### 部署目标 {#p2_console_remote type=remote config=devices/console_stack.yaml default=true}

部署到识别设备可以访问的一台 Linux 服务器。

### 部署目标 {#p2_console_local type=local config=devices/console_stack.yaml}

部署到这台电脑。识别设备必须能访问这台电脑的 IP。

## 步骤 2: 放置嵌入模型 {#p2_embed type=manual required=true config=devices/place_embedder_pi.yaml}

把 INT8 量化的 DINOv2-small 嵌入模型放到管理端的模型目录，并启用它。商品库必须用设备运行的同一个模型建立，不能和其他套餐的模型混用。

### 前置条件

- 步骤 1 的管理端已部署。
- `dinov2s_arcface_products10k_224_b1_dynint8.onnx`（sha256 `50e886aeab7b61a7eebe6ea3492b2d3ba0e74a859acedcbb9e9917b2b60454f6`），需自行获取，仅限非商用。
- 服务器上 30 MB 可用空间。

### 故障排查

| 现象 | 处理 |
|---|---|
| 注册成功，但每次检索都返回错的 SKU | 嵌入模型没有启用。设置 `RETAIL_EMBEDDER=onnx`，重启服务，然后重新注册所有 SKU。 |
| 设置 `RETAIL_EMBEDDER=onnx` 后 `server` 容器立刻退出 | 确认 `RETAIL_EMBEDDER_ONNX` 已填写，文件在 `assets/console/models/` 里且文件名一致。 |
| 换模型前后注册的商品库对不上 | 不同模型的商品库不能混用，用新模型重新注册所有 SKU。 |
| 计划商用部署 | 用自采或许可宽松的数据重训嵌入模型，并重建商品库。 |

## 步骤 3: 注册 SKU {#p2_register type=web_dashboard required=true config=devices/register_sku.yaml}

每个 SKU 上传 3 到 8 张图完成注册，每次注册生成一个新的商品库版本。

### 前置条件

- 步骤 1 的 admin token。
- 每个 SKU 3 到 8 张图，包括正面、背面、侧面，覆盖两种光照。
- 管理端使用步骤 2 的 DINOv2-small 模型。

### 故障排查

| 现象 | 处理 |
|---|---|
| 注册被拒，提示图片少于三张 | 至少上传 3 张。 |
| 商品库用 base 模型建立，设备运行 small 模型 | 用设备运行的模型重建商品库。 |
| 出了新版本，但设备仍然认不出这个 SKU | 设备端拉取、校验并切换商品库版本的功能尚未实现。 |
| 注册很慢 | 嵌入在服务器 CPU 上计算，每个 SKU 只在注册时计算一次。 |

## 步骤 4: 编译 HEF 并准备 Pi {#p2_compile type=manual required=true config=devices/pi_hailo_compile.yaml}

在 x86_64 主机上编译检测器 HEF，并在设备上准备 HailoRT 环境。

### 前置条件

- 设备上 HailoRT 与 PCIe 驱动版本一致（4.21.0）并已 hold，固件版本匹配。
- `/etc/modprobe.d/hailo.conf` 里有 `force_desc_page_size=4096`。
- `/dev/hailo0` 存在且没有被其他进程占用。
- 一台装有 Hailo AI SW Suite 容器的 x86_64 机器，以及可写的校准目录。

### 故障排查

| 现象 | 处理 |
|---|---|
| single-context 编译失败 | 属正常，编译器会自动改用两 context 分区。 |
| 编译容器写不了 cache | 把挂载的工作目录设为所有用户可写。 |
| 框数量对、坐标全错 | 用 `HEF.get_output_vstream_infos()` 获取输出顺序，不要按名字排序。 |
| 其他进程占用 `/dev/hailo0` | 停掉占用的进程。 |
| 嵌入速度明显偏慢 | 确认使用四线程，且运行的是 INT8 模型而不是 fp32 模型。 |

## 步骤 5: 验证注册、检索与设备产物 {#p2_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

验证管理端注册，并核对 HEF 与 CPU 结果一致。

### 前置条件

- 步骤 1 到 4 已完成。
- 上游仓库克隆，已执行 `uv sync`。
- 自己 SKU 的照片，使用未注册过的角度拍摄。

### 部署完成

#### 快速验证

- `uv run python tools/verify_software_loop.py` 通过。
- 管理端带 admin token 时版本号递增，不带 token 时返回 401 或 403。
- HEF 与 CPU 结果的检测框一致率（IoU ≥ 0.5）接近 94.8%，`hailortcli benchmark` 约 110 fps。
- INT8 嵌入模型四线程下每个裁剪 p50 约 92 ms。

#### 后续步骤

- 安装前确定货架处理策略：嵌入在 CPU 上逐个裁剪计算，框多的画面耗时长，选择抽帧或按货位采样其中一种。
- 用自己的数据微调两个模型。
- 编写设备端程序，串联检测、嵌入、检索与上报。

### 故障排查

| 现象 | 处理 |
|---|---|
| 一致率正常但画面上的检测不对 | 检查解码阈值（0.25）和 letterbox 预处理。 |
| 检测延迟偏高 | 确认没有其他进程占用加速器，且管线已激活。 |
| 读不到芯片温度或功耗 | 该平台不支持读取，记为 unavailable。 |
| 检索效果明显偏低 | 用自己货架的数据测试并微调模型。 |

## 套餐: Jetson Orin —— TensorRT {#p3_jetson_orin}

reComputer J40（Orin NX 16GB）或 J30（Orin Nano 8GB）用 TensorRT fp16 在 GPU 上运行商品检测和嵌入，一台 Linux 服务器运行注册服务、管理界面、MQTT broker 和商品库。

- **服务器：** 一台装有 Docker 的 Linux 服务器，不需要 GPU。
- **摄像头：** RTSP 或 USB 摄像头，对准收银台或货架。
- **模型许可：** 检测器和嵌入模型仅限非商用，不随本方案提供；商用部署需要用自采或许可宽松的数据重训。

## 步骤 1: 部署注册管理端 {#p3_console type=docker_deploy required=true config=devices/console_stack.yaml}

在服务器上启动注册服务、管理界面和 MQTT broker，并设置角色 token。

### 前置条件

- 一台装有 Docker 和 compose 插件的 Linux 服务器。
- 至少设置一个 admin token，服务不允许匿名访问。
- 需要从本地网络之外访问管理界面时，在前面加一个 TLS 反向代理。
- 默认使用已发布的镜像；使用自建镜像时覆盖 `RETAIL_SERVER_IMAGE` 和 `RETAIL_WEB_IMAGE`。

### 故障排查

| 现象 | 处理 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 检查服务器能否访问镜像仓库；使用自建镜像时先在本机构建。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 校验没有生效，停止使用并检查配置。 |
| 找不到 `docker compose` | 安装 `docker-compose-plugin`。 |
| 8089 端口被占用 | 修改服务端口。 |

### 部署目标 {#p3_console_remote type=remote config=devices/console_stack.yaml default=true}

部署到识别设备可以访问的一台 Linux 服务器。

### 部署目标 {#p3_console_local type=local config=devices/console_stack.yaml}

部署到这台电脑。识别设备必须能访问这台电脑的 IP。

## 步骤 2: 放置嵌入模型 {#p3_embed type=manual required=true config=devices/place_embedder_jetson.yaml}

把 fp32 的 DINOv2-small 嵌入模型放到管理端的模型目录，并启用它。步骤 4 用同一份文件构建 TensorRT engine；不能和其他套餐的模型混用。

### 前置条件

- 步骤 1 的管理端已部署。
- `dinov2s_arcface_products10k_224_b1.onnx`（sha256 `7f0136ef6459fdd5461e39e95070c7e964fbe2df4b53309f15f452c60da615be`），需自行获取，仅限非商用。
- 服务器上几十 MB 可用空间。

### 故障排查

| 现象 | 处理 |
|---|---|
| 注册成功，但每次检索都返回错的 SKU | 嵌入模型没有启用。设置 `RETAIL_EMBEDDER=onnx`，重启服务，然后重新注册所有 SKU。 |
| 设置 `RETAIL_EMBEDDER=onnx` 后 `server` 容器立刻退出 | 确认 `RETAIL_EMBEDDER_ONNX` 已填写，文件在 `assets/console/models/` 里且文件名一致。 |
| 换模型前后注册的商品库对不上 | 不同模型的商品库不能混用，用新模型重新注册所有 SKU。 |
| 计划商用部署 | 用自采或许可宽松的数据重训嵌入模型，并重建商品库。 |

## 步骤 3: 注册 SKU {#p3_register type=web_dashboard required=true config=devices/register_sku.yaml}

每个 SKU 上传 3 到 8 张图完成注册，每次注册生成一个新的商品库版本。

### 前置条件

- 步骤 1 的 admin token。
- 每个 SKU 3 到 8 张图，包括正面、背面、侧面，覆盖两种光照。
- 管理端使用步骤 2 的 DINOv2-small 模型，否则设备上的检索结果无效。

### 故障排查

| 现象 | 处理 |
|---|---|
| 注册被拒，提示图片少于三张 | 至少上传 3 张。 |
| 同一个 sku_id 返回 409 | 需要替换时带 `replace=true`。 |
| 版本号不增加 | 注册没有通过图片质量检查，响应里会指出是哪一张图。 |

## 步骤 4: 构建 TensorRT engine {#p3_build type=manual required=true config=devices/jetson_trt_build.yaml}

在板卡上构建检测和嵌入两个 fp16 engine，并校验 SHA。

### 前置条件

- reComputer J40（Orin NX 16GB），JetPack 6.2、TensorRT 10.3。engine 必须在运行它的板卡上构建，不能在板卡之间拷贝。
- 检测器 ONNX，需自行获取，仅限学术与非商用。
- 步骤 2 的嵌入模型 ONNX。
- 上游仓库 commit `16d1347` 或更新版本中的 `platforms/jetson/build_engines.py`。

### 故障排查

| 现象 | 处理 |
|---|---|
| `trtexec` 报 "Static model does not take explicit shapes" | 不要传 `--shapes`；使用 commit `16d1347` 及以后的 `build_engines.py`。 |
| 一块板卡上构建的 engine 在另一块上跑不了 | 在每块板卡上分别构建。 |
| `runtime.py --dry-run` 以 exit code 2 退出 | 重新构建，或执行 `build_engines.py --update-config` 更新配置中的哈希。 |
| 检测框一致率明显偏低 | 检查解码和输出布局。 |
| 检索结果差异明显 | 核对嵌入模型 ONNX 的 sha256 是否为 `7f0136ef…`。 |

## 步骤 5: 验证注册、检索与设备产物 {#p3_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

验证管理端注册与下载、engine 校验，以及设备端检测和检索结果。

### 前置条件

- 步骤 1 到 4 已完成。
- 上游仓库克隆，已执行 `uv sync`。

### 部署完成

#### 快速验证

- `uv run python tools/verify_software_loop.py` 通过。
- 管理端带 admin token 时版本号递增，不带 token 时返回 401 或 403。
- `GET /v1/gallery/current/download` 返回的 tar.gz 中 SHA256SUMS 校验通过。
- `platforms/jetson/runtime.py --config platforms/jetson/runtime.yaml --dry-run` 通过。
- 检测框一致率接近 99.91%，检索指标与 fp32 的最大差接近 0.24 个百分点。
- 通过 `platforms/jetson/runtime.py` 回放一段收银台画面，`/healthz` 中 `frames_dropped`、`capture_drop`、`embed_drop` 均为 0。

#### 把链路跑通

在自己的板卡上运行设备端程序，需要在 `runtime.yaml` 中准备四项：

1. **画面。** 接 USB 摄像头时把 `sources[0].kind` 改成 `usb`、`uri` 改成设备路径（如 `/dev/video0`）；接 RTSP 按 `runtime.yaml` 里的注释配置。
2. **商品库。** 使用步骤 1–3 管理端注册的商品库，或用 `python3 platforms/make_runtime_gallery.py --config platforms/jetson/runtime.yaml --skus-json <SKU 列表>` 在 `gallery.root` 下建立。
3. **MQTT。** 把 `mqtt.host` 改成你自己的 broker。
4. **启动。** 先执行 `python3 platforms/jetson/runtime.py --config platforms/jetson/runtime.yaml --dry-run`，通过后去掉 `--dry-run` 运行。需要开机自启时使用 `platforms/jetson/retail-runtime.service`。

#### 后续步骤

- 7×24 部署前先做长时间稳定性测试。
- 用于货架场景时，按货架配置的 1280² 输入重新测量延迟。

### 故障排查

| 现象 | 处理 |
|---|---|
| `runtime.py --dry-run` 以 exit code 2 退出 | 执行 `build_engines.py --update-config` 重新构建，新哈希会写回配置。 |
| 延迟明显偏高 | 确认 `nvpmodel -q` 为 `MAXN_SUPER`，且没有其他进程占用 GPU。 |
| 软件闭环通过 | 软件闭环只验证协议，设备精度以上面的一致率检查为准。 |
| 需要确认各套餐验证范围 | 本套餐和 RK3588 套餐做过设备端运行实测；Hailo-8 与 RK3576 套餐只验证到模型转换。 |
