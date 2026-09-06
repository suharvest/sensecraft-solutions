## 套餐: Rockchip NPU —— RK3588 / RK3576 {#p1_rockchip}

检测器以 fp16 `.rknn` 跑在 Rockchip NPU 上；嵌入器跑在 Rockchip CPU 的 onnxruntime 上，
因为嵌入器没有 RKNN 转换。管理端——注册、商品库、界面、broker——以容器跑在另一台主机上。

| 设备 | 作用 |
|---|---|
| 管理端 / 本地服务器 | 注册服务、管理界面、MQTT broker、商品库存储 |
| reComputer RK3588 或 RK3576 | NPU 上做检测，CPU 上做嵌入 |
| RTSP / USB 摄像头 | 收银台上方或正对货架的画面 |
| 一台 x86_64 机器 | 模型转换。rknn-toolkit2 不在板上运行 |

**这套硬件上测到了什么。** 检测段，在 Radxa ROCK 5T 上：RKNN fp16 与 CPU 参考的
框一致率 99.85%、p50 56.7 ms，INT8 变体 98.35%、p50 26.0 ms
（`evaluation/runs/2026-09-06-det-rk3588-radxa/results.md`）。
RK3576 上什么都没测；上面的数字只来自 RK3588。

**没测到什么。** 这块板上的嵌入器从没测过延迟。它没有 RKNN 转换，也没有尝试过。
另外，也没有把检测、嵌入、检索与上报串起来的设备侧服务——那个进程在上游仓库里
对任何平台都不存在。这个套餐做的是转换模型、在板上证明转换正确，到此为止。

## 步骤 1: 部署注册管理端 {#p1_console type=docker_deploy required=true config=devices/console_stack.yaml}

在管理端主机上拉起注册服务、管理界面与 broker，并写入角色 token 表。

### 前置条件

- 一台装了 Docker 与 compose 插件、且从识别设备可达的 Linux 主机。不需要 GPU。
- **两个容器镜像都没有推送。** 在这台主机上从上游仓库构建，先构建 SPA
  （`npm --prefix web/ui ci && npm --prefix web/ui run build`），再用
  `platforms/console/Dockerfile.server` 与 `platforms/console/Dockerfile.web`。
  镜像里不跑 npm。这一步在动 compose 之前会先检查两个镜像是否已在本机。
- 至少定好一个 admin token。没有默认 token，也没有匿名读；token 表为空时服务拒绝启动。
- 在本地网络之外能访问界面之前，先在它前面放一个终止 TLS 的反向代理。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 在你构建之前这是预期结果。在这台主机上从上游仓库构建，用你构建出的 tag。 |
| 找不到 `docker compose` | 安装 `docker-compose-plugin`。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 闸门没挡在商品库前面。停下来排查——这一步会打印这条检查的结果。 |
| 带 admin token 的 `GET /v1/gallery` 返回空库 | 首次注册之前这是正确的。 |
| 8089 端口被占用 | 在向导里改服务端口。设备必须拿到同一个值——那是它们拉商品库的端口。 |

## 步骤 2: 放置嵌入模型 {#p1_embed type=manual required=true config=devices/place_embedder.yaml}

把 DINOv2 ONNX 放到管理端挂载的位置，并把服务从占位嵌入器切过去。

### 前置条件

- 步骤 1 的管理端栈，停着或跑着都行——文件放在它的 compose 文件旁边，
  下一次 `docker compose up -d server` 时生效。
- `dinov2b_arcface_products10k_224_b1.onnx`，348 MB，sha256
  `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`。
  本包不含它：`use_scope: non-commercial`、`redistributable: false`
  （JD Products-10K 条款，在其上微调的权重继承该范围）。骨干
  `facebook/dinov2-base` 是 Apache-2.0；限制来自训练数据。
- 管理端主机上 350 MB 空闲空间。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册成功，但每次检索都返回错的 SKU | 服务还在占位嵌入器上。上游 `embedder_backend` 默认 `fake`（`server/config.py`），它把图片字节哈希成向量。`GET /api/health` 不报告这一项，启动也不打日志，所以这个症状是唯一的信号。设 `RETAIL_EMBEDDER=onnx`，重启，然后把所有 SKU 重新注册一遍。 |
| 设了 `RETAIL_EMBEDDER=onnx` 之后 `server` 容器立刻退出 | 要么 `RETAIL_EMBEDDER_ONNX` 是空的——上游在这个组合下拒绝启动——要么路径在容器里不存在。确认文件在 `assets/console/models/` 里，且文件名与变量一致。 |
| 切换前后注册的商品库对不上 | 不能混用。一个嵌入器产出的向量与另一个的不可比。在新模型上把所有 SKU 重新注册一遍。 |
| 计划商用部署 | 用自采或许可宽松的数据重训嵌入器，并重建每一个商品库版本。随包给出的权重不能用于商用。 |

## 步骤 3: 注册 SKU {#p1_register type=web_dashboard required=true config=devices/register_sku.yaml}

打开管理界面的商品库。每个 SKU 用 3 到 8 张图注册；每次注册生成一个新的不可变商品库版本。

### 前置条件

- 步骤 1 里的 admin token。
- 每个 SKU 3–8 张图：至少正面、背面、侧面，覆盖两种光照。少于三张会被拒绝。
- 定下管理端用哪个嵌入器，因为之后再换就得重建所有商品库版本。
  两个不同模型的向量不可比。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册被拒，提示图片少于三张 | 这是设计如此。至少给三张。 |
| 同一个 sku_id 返回 409 | 同样是设计如此。确实要替换就带 `replace=true`，那会生成一个新版本。 |
| 出了新版本，但设备仍然认不出这个 SKU | 它还没拉取并切换。留出一个轮询周期加下载时间；切换在 SHA 校验通过之后才发生。 |
| top-1 明显低于公布数字 | 先看注册张数（同一模型每 SKU 1 张实测 51.11%，8 张实测 79.11%），再考虑域差距——模型是在电商棚拍图上微调的。 |

## 步骤 4: 在 Rockchip 上转换并核对检测器 {#p1_convert type=manual required=true config=devices/rk3588_convert.yaml}

在 x86_64 主机上把 ONNX 转成 `.rknn`，拷到板上，并定下嵌入跑在哪里。

### 前置条件

- 一台 x86_64 机器，装 rknn-toolkit2 2.3.2，onnx 钉 1.16.1，setuptools 低于 81。
  更高版本的 onnx 删掉了 `onnx.mapping`，会在 `load_onnx` 里报错；setuptools 81 起
  没有 `pkg_resources`。
- toolkit 版本必须与板上 `librknnrt.so` 的版本一致。不匹配不一定会明着报错——
  它可能加载成功但算出错的数。
- 检测器 ONNX。本包不含它：权重训练在 SKU-110K 上，仅限学术与非商用，且禁止衍生作品。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `load_onnx` 在 `onnx.mapping` 上失败 | onnx 太新。钉 1.16.1。 |
| 找不到 `pkg_resources` | setuptools 81 或更高。钉到 81 以下。 |
| INT8 一致率明显低于 98% | 看校准图是怎么抽的。按文件名取前 N 张会落进同一个拍摄批次，量化 scale 就只按那个批次定了。要从整个 val 目录等间隔抽。 |
| 板上没有 cv2 和 PIL | 如果那个 Python 还有别的项目在用，就不要装。在别处 letterbox 好，打包成一个 `(N, 640, 640, 3)` uint8 BGR 的 `.npy`；设备端脚本只需要 numpy 和 rknnlite。 |

## 步骤 5: 验证注册、检索与设备产物 {#p1_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

复现软件闭环、走一遍管理端 API、为你自己的转换产物复现 parity 数字，并记下还有什么没验证。

### 前置条件

- 步骤 1 到 4 已完成。
- 一份跑过 `uv sync` 的上游仓库克隆，用于软件闭环与 CPU golden。
- 你自己 SKU 的照片，用没注册过的角度拍，供检索核对使用。

### 部署完成

#### 快速验证

- `uv run python tools/verify_software_loop.py` 通过——注册、事件、查询与回滚在
  FakeEmbedder 与内存 broker 上全部断言干净。
- 管理端在带 admin token 时返回的版本号每注册一次涨一次，不带 token 时返回 401 或 403。
- `GET /v1/gallery/current/download` 返回的 tar.gz 里 SHA256SUMS 校验得过。
- 你的 `.rknn` 复现出接近参照的框一致率：fp16 是 99.85%，INT8 是 98.35%，
  都是与 CPU golden 按 IoU ≥ 0.5 比对。

#### 后续步骤

- 用你自己货架上的数据微调两个模型。上游 model card 直说货架与收银台部署需要自采数据。
- 把设备侧主链写出来。检测、嵌入、库检索与上报都是分开的部件，现在没有东西把它们串起来。
- 在这块板上测嵌入器。它在 RK3588 上从没测过，而它正是决定货架场景能不能跑的那一段。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 框一致率远低于参照 | 差这么多不是量化问题。先查解码路径与输出布局。 |
| 软件闭环过了但板上什么都不工作 | 这是预期的——闭环跑在开发机上的 FakeEmbedder 与内存 broker 上，只证明协议行为。 |
| 商品库在主机上校验得过、在设备上校验不过 | 怪设备之前先比两边的 sha256；传输被截断看起来就像文件损坏。 |

## 套餐: Raspberry Pi 5 + Hailo-8 —— 检测上 NPU，嵌入留 CPU {#p2_pi5_hailo}

唯一一个两段都在目标硬件上跑过的套餐。检测器是 Hailo-8 上的 INT8 HEF；
嵌入器是 Pi 自己四个核上动态量化 INT8 的 DINOv2-small——因为它的 NPU 路线走不通。

| 设备 | 作用 |
|---|---|
| 管理端 / 本地服务器 | 注册服务、管理界面、MQTT broker、商品库存储 |
| Raspberry Pi 5 + Hailo-8（M.2） | NPU 上做检测，CPU 上做嵌入 |
| RTSP / USB 摄像头 | 收银台上方或正对货架的画面 |
| 一台 x86_64 机器 | 编译 HEF。Hailo Dataflow Compiler 不在 Pi 上运行 |

**这套硬件上测到了什么。** 检测：p50 9.04 ms、p95 9.10 ms，单流 110.4 fps，
在 200 张上与 CPU 参考的框一致率 94.77%（`evaluation/runs/2026-09-06-det-hef/`，
两个 boundary 文件均 `status: measured`）。端到端含 letterbox、拼接、解码与 NMS：
p50 18.74 ms / p95 24.25 ms——对约 160 个框做 NMS 比推理本身还贵。
嵌入：四线程下每个裁剪 p50 91.95 ms / p95 105.98 ms，在 7 个档位上与自身 fp32 的
检索准确率相差 0.65 个百分点以内（`evaluation/runs/2026-09-06-embed-small/` §8）。

**为什么嵌入器在 CPU 上。** 两档 Hailo DFC 量化都没过 ≤3 个百分点的验收线。
default 档 top-1 掉 21–44 个百分点；激进档直接塌缩，8171 张评测图产出同一个向量、
AUROC 精确等于 50.00（`evaluation/runs/2026-09-06-embed-hailo/`）。
嵌入器没有生成 HEF，因此那条路径也没有设备延迟数据。

**做规划要盯的数是每个裁剪 92 ms。** 五件商品的收银篮约半秒嵌入。
货架一帧按实测密度 157.6 个框算约 14 秒。货架场景需要抽帧或按货位采样，
而这个决定属于安装之前，不是安装之后。

## 步骤 1: 部署注册管理端 {#p2_console type=docker_deploy required=true config=devices/console_stack.yaml}

与所有套餐相同的管理端——注册服务、管理界面、broker——跑在一台 Pi 可达的主机上。

### 前置条件

- 一台装了 Docker 与 compose 插件的 Linux 主机。不需要 GPU。
- **两个容器镜像都没有推送。** 在这台主机上从上游仓库构建，先构建 SPA。
  这一步在动 compose 之前会先检查两个镜像是否已在本机。
- 至少一个 admin token。没有默认值，也没有匿名读。
- 在界面能从本地网络之外访问之前，先在它前面放一个终止 TLS 的反向代理。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 在你构建之前这是预期结果。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 闸门没挡在商品库前面。停下来排查。 |
| Pi 访问不到服务端口 | 设备是从那个端口拉商品库的，不是走界面。在 Pi 上试，不要在另一个网络的浏览器上试。 |
| 8089 端口被占用 | 在向导里改掉，并把同一个值给设备。 |

## 步骤 2: 放置嵌入模型 {#p2_embed type=manual required=true config=devices/place_embedder.yaml}

把 DINOv2 ONNX 放到管理端挂载的位置，并把服务从占位嵌入器切过去。

### 前置条件

- 步骤 1 的管理端栈，停着或跑着都行——文件放在它的 compose 文件旁边，
  下一次 `docker compose up -d server` 时生效。
- `dinov2b_arcface_products10k_224_b1.onnx`，348 MB，sha256
  `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`。
  本包不含它：`use_scope: non-commercial`、`redistributable: false`
  （JD Products-10K 条款，在其上微调的权重继承该范围）。骨干
  `facebook/dinov2-base` 是 Apache-2.0；限制来自训练数据。
- 管理端主机上 350 MB 空闲空间。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册成功，但每次检索都返回错的 SKU | 服务还在占位嵌入器上。上游 `embedder_backend` 默认 `fake`（`server/config.py`），它把图片字节哈希成向量。`GET /api/health` 不报告这一项，启动也不打日志，所以这个症状是唯一的信号。设 `RETAIL_EMBEDDER=onnx`，重启，然后把所有 SKU 重新注册一遍。 |
| 设了 `RETAIL_EMBEDDER=onnx` 之后 `server` 容器立刻退出 | 要么 `RETAIL_EMBEDDER_ONNX` 是空的——上游在这个组合下拒绝启动——要么路径在容器里不存在。确认文件在 `assets/console/models/` 里，且文件名与变量一致。 |
| 切换前后注册的商品库对不上 | 不能混用。一个嵌入器产出的向量与另一个的不可比。在新模型上把所有 SKU 重新注册一遍。 |
| 计划商用部署 | 用自采或许可宽松的数据重训嵌入器，并重建每一个商品库版本。随包给出的权重不能用于商用。 |

## 步骤 3: 注册 SKU {#p2_register type=web_dashboard required=true config=devices/register_sku.yaml}

每个 SKU 用 3 到 8 张图注册。每次注册生成一个新的不可变商品库版本。

### 前置条件

- 步骤 1 里的 admin token。
- 每个 SKU 3–8 张图，覆盖正面、背面、侧面与两种光照。
- 如果这台 Pi 是基准，就用 DINOv2-small：商品库必须用设备真正跑的那个模型来建，
  否则什么都对不上。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册被拒，提示图片少于三张 | 这是设计如此。 |
| 库是用 base 建的，设备跑的是 small | 跨模型的向量不可比。用设备真正跑的那个模型重建商品库。 |
| 出了新版本，但设备仍然认不出这个 SKU | 留出一个轮询周期加下载时间；切换在 SHA 校验通过之后发生。 |
| 注册很慢 | 管理端主机上的嵌入是 CPU 活。它是按图片算的，不是按帧算的，所以每个 SKU 只花这一次。 |

## 步骤 4: 编译 HEF 并准备 Pi {#p2_compile type=manual required=true config=devices/pi_hailo_compile.yaml}

把 HailoRT 一整套钉在同一版本，在 x86_64 主机上编译检测器 HEF，
并把嵌入器定在 CPU 上，连同由此推出的一帧预算。

### 前置条件

- Pi 上 HailoRT 与 PCIe 驱动同版本且都 hold 住，固件也对得上。
  实测那一轮全程 4.21.0，编译侧是 DFC 3.31.0。
- `/etc/modprobe.d/hailo.conf` 里带 `force_desc_page_size=4096`。
  Pi 5 是 16 KB 页而 Hailo-8 要 4 KB descriptor。
- `/dev/hailo0` 存在且没有别的进程占着。实测数字是独占加速器时的值。
- 一台装了 Hailo AI SW Suite 容器的 x86_64 机器，以及一个它可写的校准目录。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| single-context 编译失败 | 这个模型上是预期的。编译器会切到两 context 分区；这次降级的运行时代价已经含在实测的 9.04 ms 里。 |
| 编译容器写不了 cache | 把挂载进去的工作目录改成可写。它的 `hailo` 用户不是你的 uid。 |
| 框数量对、坐标全错 | 输出 vstream 顺序。用 `HEF.get_output_vstream_infos()` 枚举，绝不要按名字排序——真机上每个尺度内部是降序。 |
| 别的进程占着 `/dev/hailo0` | 测量期间把它停掉。共用加速器会改变本页每一个数字。 |
| 嵌入远慢于 92 ms | 看线程数（实测用的是四线程），再确认你跑的是动态 INT8 模型而不是 fp32——fp32 实测是 180.75 ms。 |

## 步骤 5: 验证注册、检索与设备产物 {#p2_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

复现软件闭环、走一遍管理端 API、为你自己的 HEF 复现 parity 数字，并记下还有什么没验证。

### 前置条件

- 步骤 1 到 4 已完成。
- 一份跑过 `uv sync` 的上游仓库克隆。
- 你自己 SKU 的照片，用没注册过的角度拍。

### 部署完成

#### 快速验证

- `uv run python tools/verify_software_loop.py` 通过。
- 管理端带 admin token 时返回递增的版本号，不带 token 时返回 401 或 403。
- 你的 HEF 与 CPU golden 在 IoU ≥ 0.5 下复现出约 94.8% 的框一致率，
  `hailortcli benchmark` 报出约 110 fps。
- 动态 INT8 嵌入器在四线程下测出每个裁剪约 92 ms p50。

#### 后续步骤

- 安装之前先定下货架策略：每个裁剪 92 ms 时，157 个框的一帧是 14 秒。
  抽帧或按货位采样，选一个，不要糊里糊涂两个都上。
- 用你自己的数据微调两个模型。
- 把设备侧主链写出来。今天没有东西把检测、嵌入、检索与上报串起来。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 一致率接近 94.8% 但画面上的检测看着不对 | 查解码阈值与 letterbox，不是 HEF 的问题。parity 流程用的是 0.25 与 IoU ≥ 0.5。 |
| 延迟高于 9 ms | 有别的东西占着加速器，或者管线没有 activate。这个测量不含前后处理。 |
| 取不到 die 温度或功耗 | 这个平台上读不到。HailoRT 4.21 的 `fw-control` 只有 `identify`，Pi 的 M.2 HAT 也不在支持电流监测的平台之列。记为 unavailable。 |
| 检索明显低于公布数字 | 域差距。模型是在电商棚拍图上微调的；在你自己的货架上测，并从那里开始微调。 |

## 套餐: Jetson Orin —— TensorRT，尚未搭建 {#p3_jetson_orin}

TensorRT 这条路径在设计里，不在代码里。选这个套餐是去搭建并实测它；
它不部署一套能用的系统。

| 设备 | 作用 |
|---|---|
| 管理端 / 本地服务器 | 注册服务、管理界面、MQTT broker、商品库存储 |
| reComputer J40（Orin NX 16GB）或 J30（Orin Nano 8GB） | TensorRT 路径将要跑的地方 |
| RTSP / USB 摄像头 | 收银台上方或正对货架的画面 |

**已有的东西。** 静态 batch-1、opset 11 的 ONNX 及其 sha256，
`core_retail.postprocess` 里四平台共用的纯 numpy YOLOX 解码与 NMS，
另外两个后端拿来对过的 onnxruntime CPU golden，以及那套 parity 流程本身。

**没有的东西。** `backends/` 里的 TensorRT 检测器。针对固定 `images:1x3x640x640`
profile 的 engine 构建。板上的运行时容器。上游仓库 `platforms/` 下只有 console、
hailo、rknn——README 里的 jetson 条目继承自捐赠项目，指向的文件从未拷过来。
另外，设备侧主链三个平台都缺，不只是这一个。

**本包里没有任何数字取自 Jetson。** 计划做这件事的板子在 2026-09-08 之前都在跑长稳。

## 步骤 1: 部署注册管理端 {#p3_console type=docker_deploy required=true config=devices/console_stack.yaml}

管理端是真的，在这里的部署方式与另外两个套餐一样。它也是这个套餐里唯一如此的部分。

### 前置条件

- 一台装了 Docker 与 compose 插件的 Linux 主机。不需要 GPU。
- **两个容器镜像都没有推送。** 在这台主机上从上游仓库构建，先构建 SPA。
- 至少一个 admin token。没有默认值，没有匿名读。
- 对外开放之前，在界面前面放一个终止 TLS 的反向代理。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 在你构建之前这是预期结果。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 闸门没挡在商品库前面。停下来排查。 |
| 找不到 `docker compose` | 安装 `docker-compose-plugin`。 |
| 8089 端口被占用 | 在向导里改掉。 |

## 步骤 2: 放置嵌入模型 {#p3_embed type=manual required=true config=devices/place_embedder.yaml}

把 DINOv2 ONNX 放到管理端挂载的位置，并把服务从占位嵌入器切过去。

### 前置条件

- 步骤 1 的管理端栈，停着或跑着都行——文件放在它的 compose 文件旁边，
  下一次 `docker compose up -d server` 时生效。
- `dinov2b_arcface_products10k_224_b1.onnx`，348 MB，sha256
  `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`。
  本包不含它：`use_scope: non-commercial`、`redistributable: false`
  （JD Products-10K 条款，在其上微调的权重继承该范围）。骨干
  `facebook/dinov2-base` 是 Apache-2.0；限制来自训练数据。
- 管理端主机上 350 MB 空闲空间。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册成功，但每次检索都返回错的 SKU | 服务还在占位嵌入器上。上游 `embedder_backend` 默认 `fake`（`server/config.py`），它把图片字节哈希成向量。`GET /api/health` 不报告这一项，启动也不打日志，所以这个症状是唯一的信号。设 `RETAIL_EMBEDDER=onnx`，重启，然后把所有 SKU 重新注册一遍。 |
| 设了 `RETAIL_EMBEDDER=onnx` 之后 `server` 容器立刻退出 | 要么 `RETAIL_EMBEDDER_ONNX` 是空的——上游在这个组合下拒绝启动——要么路径在容器里不存在。确认文件在 `assets/console/models/` 里，且文件名与变量一致。 |
| 切换前后注册的商品库对不上 | 不能混用。一个嵌入器产出的向量与另一个的不可比。在新模型上把所有 SKU 重新注册一遍。 |
| 计划商用部署 | 用自采或许可宽松的数据重训嵌入器，并重建每一个商品库版本。随包给出的权重不能用于商用。 |

## 步骤 3: 注册 SKU {#p3_register type=web_dashboard required=true config=devices/register_sku.yaml}

注册今天就能用，而且与缺失的设备侧路径无关——在任何东西跑上 Orin 之前，
商品库就可以建好并版本化。

### 前置条件

- 步骤 1 里的 admin token。
- 每个 SKU 3–8 张图，正面、背面、侧面，两种光照。
- 定下用哪个嵌入器建库并记下来，因为最终跑在 Orin 上的必须是同一个模型。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册被拒，提示图片少于三张 | 这是设计如此。 |
| 同一个 sku_id 返回 409 | 设计如此。要替换就带 `replace=true`。 |
| 不确定该统一到哪个嵌入器 | 每 SKU 8 张图时 DINOv2-base 实测 top-1 84.67%，DINOv2-small 同档 79.11% 且只有四分之一大。两者都没在 Orin 上跑过。 |
| 版本号不涨 | 注册没过质量闸门。响应里会说是哪一张图。 |

## 步骤 4: 搭建 TensorRT 路径 {#p3_build type=manual required=true config=devices/jetson_trt_build.yaml}

写清楚缺什么、怎么构建 engine，以及在它的任何延迟数字有意义之前必须通过的 parity 检查。

### 前置条件

- 一块装好 JetPack 与 TensorRT 的 Orin 板。engine 在它将要运行的那块板上构建——
  engine 与设备和 TensorRT 版本绑定，不得在板之间分发。
- 检测器 ONNX。本包不含它：权重训练在 SKU-110K 上，仅限学术与非商用，且禁止衍生作品。
- 愿意把后端写出来。这一步不会替你装一个。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 在找 `platforms/jetson/tools/build_engine.sh` | 它不在那里。README 里提到它的那条继承自捐赠项目，文件从未拷过来。 |
| 一块板上构建的 engine 在另一块板上跑不了 | 这是预期的。engine 与设备和 TensorRT 版本绑定。按板构建。 |
| parity 远低于 RKNN fp16 的 99.85% 参照 | 差这么多是解码或输出布局的问题，不是 fp16 精度的问题。 |
| 想要一个可以引用的延迟数字 | 没有，而且从别的平台推一个出来是错的——同一个模型上 RK3588 与 Hailo-8 差了 6 倍。 |

## 步骤 5: 验证注册、检索与设备产物 {#p3_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

复现今天确实能跑的软件闭环与管理端往返，并如实记下设备侧的缺口，
而不是报一个绿色对勾。

### 前置条件

- 步骤 1 到 3 已完成。步骤 4 是一项开发任务，可以仍然开着。
- 一份跑过 `uv sync` 的上游仓库克隆。

### 部署完成

#### 快速验证

- `uv run python tools/verify_software_loop.py` 通过。
- 管理端带 admin token 时返回递增的版本号，不带 token 时返回 401 或 403。
- `GET /v1/gallery/current/download` 返回的 tar.gz 里 SHA256SUMS 校验得过。
- 设备侧的 parity 检查还没有可跑的对象，而这正是应当记下的准确结果。

#### 后续步骤

- 写出 TensorRT 检测器后端，并在板上构建 engine。
- 测延迟之前先跑与 CPU golden 的 parity 检查。
- 写出设备侧主链——它在每个平台上都缺。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 期待一套可部署的 Jetson 系统 | 没有这样一套。这个套餐存在，是为了把缺口写出来而不是让它静静消失。 |
| 软件闭环过了，看起来像做完了 | 闭环跑在开发机上的 FakeEmbedder 上。它证明协议行为，不证明任何一块板上的任何事。 |
| 想把它标成已验证 | 本包里没有任何套餐可以带 `verified: [hardware]`。有些部分在硬件上跑过；这个包没有。 |
