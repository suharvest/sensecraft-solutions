## 套餐: Rockchip NPU —— RK3588 / RK3576 {#p1_rockchip}

检测器与嵌入器都以 fp16 `.rknn` 跑在 Rockchip NPU 上。管理端——注册、商品库、界面、
broker——以容器跑在另一台主机上。

| 设备 | 作用 |
|---|---|
| 管理端 / 本地服务器 | 注册服务、管理界面、MQTT broker、商品库存储 |
| reComputer RK3588 系列 | 检测与嵌入都跑在 NPU 上 |
| RTSP / USB 摄像头 | 收银台上方或正对货架的画面 |
| 一台 x86_64 机器 | 模型转换。rknn-toolkit2 不在板上运行 |

**这套硬件上测到了什么。** 全部在 RK3588 板上（librknnrt 2.3.2，driver 0.9.8）：

| 段 | 数 |
|---|---|
| 检测器，RKNN fp16 对 CPU 参考 | 框一致率 99.85%，p50 56.7 ms |
| 检测器，RKNN INT8 对 CPU 参考 | 框一致率 98.35%，p50 26.0 ms |
| 嵌入器（DINOv2-small + ArcFace），RKNN fp16 对 fp32 ONNX CPU | 21 个检索指标最大差 0.85 pp |
| 嵌入器，RKNN fp16，单裁剪，三个 NPU 核 | 48.93 ms p50 / 56.47 ms p95 |
| 嵌入器，同一模型跑 CPU（动态 INT8，4 线程） | 93.45 ms p50 / 94.86 ms p95 |
| 检测与嵌入共用三个核 | 嵌入 88.94 ms p50，检测 76.91 ms p50 |
| 检测占 core 2、嵌入占 core 0+1 | 嵌入 53.19 ms p50，检测 60.88 ms p50 |

最后两行对应两个部署前要设好的开关：给两个模型各自的核
（`RETAIL_RKNN_DET_CORE_MASK=2`、`RETAIL_RKNN_EMBED_CORE_MASK=01`）；核掩码不要
留 `AUTO`——实测 `AUTO` 只用 core 0，core 1 与 core 2 全程 0%。

RK3576 上什么都没测；上面的数字只来自 RK3588。

**没测到什么。** 这套配置从画面到管理端看到识别结果的端到端延迟没有测。另外，
也没有把检测、嵌入、检索与上报串起来的设备侧服务——那个进程在上游仓库里对任何
平台都不存在。这个套餐做的是转换两个模型、在板上证明转换正确，到此为止。

## 步骤 1: 部署注册管理端 {#p1_console type=docker_deploy required=true config=devices/console_stack.yaml}

在管理端主机上拉起注册服务、管理界面与 broker，并写入角色 token 表。

### 前置条件

- 一台装了 Docker 与 compose 插件、且从识别设备可达的 Linux 主机。不需要 GPU。
- **两个容器镜像均已发布**（`edge-retail-console-server:0.1.1`、
  `edge-retail-console-web:0.1.0`），`RETAIL_SERVER_IMAGE`/`RETAIL_WEB_IMAGE`
  默认指向它们。要用自建版本，先在这台主机上构建 SPA
  （`npm --prefix web/ui ci && npm --prefix web/ui run build`），再用
  `platforms/console/Dockerfile.server` 与 `platforms/console/Dockerfile.web`
  构建镜像（镜像里不跑 npm），并覆盖这两个变量。这一步在动 compose 之前会先
  检查两个镜像是否已在本机或可拉取。
- 至少定好一个 admin token。没有默认 token，也没有匿名读；token 表为空时服务拒绝启动。
- 在本地网络之外能访问界面之前，先在它前面放一个终止 TLS 的反向代理。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 发布的默认镜像拉取失败——检查能否访问镜像仓库。只有覆盖成自建 tag 但还没在本机构建时才相关。 |
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
| 出了新版本，但设备仍然认不出这个 SKU | 控制台侧提供版本化、带签名的商品库；设备端运行时——拉取版本、校验 checksum、原子切换——尚未实现（开发中，见上游 spec）。 |
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
- 步骤 2 的嵌入器 ONNX，如果还没放的话。它的许可与检测器的是两回事，限制不比后者松：
  `use_scope: non-commercial`、`redistributable: false`，继承自 JD Products-10K
  训练数据（骨干 `facebook/dinov2-base` 本身是 Apache-2.0）。不得随本包分发，
  也不得打进镜像；商用部署必须用自采或许可宽松的数据重训它，并重建每一个商品库版本——
  一个嵌入器产出的向量与另一个的不可比。

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

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 框一致率远低于参照 | 差这么多不是量化问题。先查解码路径与输出布局。 |
| 软件闭环过了但板上什么都不工作 | 这是预期的——闭环跑在开发机上的 FakeEmbedder 与内存 broker 上，只证明协议行为。 |
| 商品库在主机上校验得过、在设备上校验不过 | 怪设备之前先比两边的 sha256；传输被截断看起来就像文件损坏。 |

## 套餐: reComputer R2000（Hailo-8）—— 检测上 NPU，嵌入留 CPU {#p2_pi5_hailo}

唯一一个两段都在目标硬件上跑过的套餐。检测器是 Hailo-8 上的 INT8 HEF；
嵌入器是 Pi 自己四个核上动态量化 INT8 的 DINOv2-small——因为它的 NPU 路线走不通。

| 设备 | 作用 |
|---|---|
| 管理端 / 本地服务器 | 注册服务、管理界面、MQTT broker、商品库存储 |
| reComputer R2000 + Hailo-8（M.2） | NPU 上做检测，CPU 上做嵌入 |
| RTSP / USB 摄像头 | 收银台上方或正对货架的画面 |
| 一台 x86_64 机器 | 编译 HEF。Hailo Dataflow Compiler 不在 Pi 上运行 |

**这套硬件上测到了什么。** 检测：p50 9.04 ms、p95 9.10 ms，单流 110.4 fps，
在 200 张上与 CPU 参考的框一致率 94.77%（`evaluation/runs/2026-09-06-det-hef/`，
两个 boundary 文件均 `status: measured`）。端到端含 letterbox、拼接、解码与 NMS：
p50 18.74 ms / p95 24.25 ms——对约 160 个框做 NMS 比推理本身还贵。
嵌入：四线程下每个裁剪 p50 91.95 ms / p95 105.98 ms，在 7 个档位上与自身 fp32 的
检索准确率相差 0.65 个百分点以内（`evaluation/runs/2026-09-06-embed-small/` §8）。

**为什么嵌入器在 CPU 上。** 两档 Hailo 量化都没过 ≤3 个百分点的验收线。
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
- **两个容器镜像均已发布**，`RETAIL_SERVER_IMAGE`/`RETAIL_WEB_IMAGE` 默认
  指向它们。要用自建版本，在这台主机上从上游仓库构建，先构建 SPA，再覆盖
  这两个变量。
  这一步在动 compose 之前会先检查两个镜像是否已在本机。
- 至少一个 admin token。没有默认值，也没有匿名读。
- 在界面能从本地网络之外访问之前，先在它前面放一个终止 TLS 的反向代理。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 发布的默认镜像拉取失败——检查能否访问镜像仓库。只有覆盖成自建 tag 但还没在本机构建时才相关。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 闸门没挡在商品库前面。停下来排查。 |
| Pi 访问不到服务端口 | 设备是从那个端口拉商品库的，不是走界面。在 Pi 上试，不要在另一个网络的浏览器上试。 |
| 8089 端口被占用 | 在向导里改掉，并把同一个值给设备。 |

## 步骤 2: 放置嵌入模型 {#p2_embed type=manual required=true config=devices/place_embedder_pi.yaml}

把 DINOv2 ONNX 放到管理端挂载的位置，并把服务从占位嵌入器切过去。这个套餐用的是
动态量化 INT8 的 DINOv2-small，不是 RK3588 套餐用的 DINOv2-base 文件——商品库与建它的那个
模型绑定，两者不能互换。

### 前置条件

- 步骤 1 的管理端栈，停着或跑着都行——文件放在它的 compose 文件旁边，
  下一次 `docker compose up -d server` 时生效。
- `dinov2s_arcface_products10k_224_b1_dynint8.onnx`，23,541,073 字节，sha256
  `50e886aeab7b61a7eebe6ea3492b2d3ba0e74a859acedcbb9e9917b2b60454f6`。
  本包不含它：`use_scope: non-commercial`、`redistributable: false`
  （JD Products-10K 条款，在其上微调的权重继承该范围）。骨干
  `facebook/dinov2-small` 是 Apache-2.0；限制来自训练数据。
- 管理端主机上 30 MB 空闲空间。

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
| 出了新版本，但设备仍然认不出这个 SKU | 控制台侧提供版本化、带签名的商品库；设备端运行时——拉取版本、校验 checksum、原子切换——尚未实现（开发中，见上游 spec）。 |
| 注册很慢 | 管理端主机上的嵌入是 CPU 活。它是按图片算的，不是按帧算的，所以每个 SKU 只花这一次。 |

## 步骤 4: 编译 HEF 并准备 Pi {#p2_compile type=manual required=true config=devices/pi_hailo_compile.yaml}

把 HailoRT 一整套钉在同一版本，在 x86_64 主机上编译检测器 HEF，
并把嵌入器定在 CPU 上，连同由此推出的一帧预算。

### 前置条件

- Pi 上 HailoRT 与 PCIe 驱动同版本且都 hold 住，固件也对得上。
  实测那一轮全程 4.21.0，编译侧版本见 `devices/pi_hailo_compile.yaml`（3.31.0）。
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

## 套餐: Jetson Orin —— TensorRT {#p3_jetson_orin}

两段都以 TensorRT fp16 engine 跑在 Orin NX 自己的 GPU 上。实测于一台 Seeed
reComputer J40 整机——是整机实测：检测器 p50 5.18 ms / p95 5.28 ms，
与 CPU 参考的框一致率 99.91%（50 张，与 RK3588 用的同一批 golden）；嵌入器
p50 4.23 ms / p95 4.69 ms，21 项检索指标与 fp32 最大差 0.24 个百分点。
一次 2956 帧的收银台回放跑通了完整的设备侧运行时——检测、嵌入、库检索、
MQTT 上报——零掉帧，这也是本包里唯一一个把两段串起来在真机上跑过的套餐，
而不是止步于模型转换。以上数字均为 n=300、纯推理，engine 在运行它的这台设备上构建。

| 设备 | 作用 |
|---|---|
| 管理端 / 本地服务器 | 注册服务、管理界面、MQTT broker、商品库存储 |
| reComputer J40（Orin NX 16GB） | 检测与嵌入，两段都经 TensorRT fp16 跑在 GPU 上——实测机型 |
| reComputer J30（Orin Nano 8GB） | 同一家族、同样角色；没有实测数字，本页数字全部来自 Orin NX（J40） |
| RTSP / USB 摄像头 | 收银台上方或正对货架的画面 |

## 步骤 1: 部署注册管理端 {#p3_console type=docker_deploy required=true config=devices/console_stack.yaml}

管理端是真的，在这里的部署方式与另外两个套餐一样。与 RK3588、Hailo-8 套餐不同，
这个套餐不止步于管理端——步骤 4 还会构建一套已经在真机上跑通端到端的设备侧运行时。

### 前置条件

- 一台装了 Docker 与 compose 插件的 Linux 主机。不需要 GPU。
- **两个容器镜像均已发布**，`RETAIL_SERVER_IMAGE`/`RETAIL_WEB_IMAGE` 默认
  指向它们。要用自建版本，在这台主机上从上游仓库构建，先构建 SPA，再覆盖
  这两个变量。
- 至少一个 admin token。没有默认值，没有匿名读。
- 对外开放之前，在界面前面放一个终止 TLS 的反向代理。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| compose 运行前提示 "MISSING: `<image>`" | 发布的默认镜像拉取失败——检查能否访问镜像仓库。只有覆盖成自建 tag 但还没在本机构建时才相关。 |
| 匿名 `GET /v1/gallery` 返回 200 | token 闸门没挡在商品库前面。停下来排查。 |
| 找不到 `docker compose` | 安装 `docker-compose-plugin`。 |
| 8089 端口被占用 | 在向导里改掉。 |

## 步骤 2: 放置嵌入模型 {#p3_embed type=manual required=true config=devices/place_embedder_jetson.yaml}

把 DINOv2 ONNX 放到管理端挂载的位置，并把服务从占位嵌入器切过去。这个套餐用的是
fp32 的 DINOv2-small ONNX——与步骤 4 构建 TensorRT engine 用的是同一份文件——
不是 RK3588 套餐用的 DINOv2-base，也不是 Hailo-8 套餐用的动态量化 INT8 文件：
商品库与建它的那个模型绑定。

### 前置条件

- 步骤 1 的管理端栈，停着或跑着都行——文件放在它的 compose 文件旁边，
  下一次 `docker compose up -d server` 时生效。
- `dinov2s_arcface_products10k_224_b1.onnx`，sha256
  `7f0136ef6459fdd5461e39e95070c7e964fbe2df4b53309f15f452c60da615be`。
  本包不含它：`use_scope: non-commercial`、`redistributable: false`
  （JD Products-10K 条款，在其上微调的权重继承该范围）。骨干
  `facebook/dinov2-small` 是 Apache-2.0；限制来自训练数据。
- 管理端主机上几十 MB 空闲空间。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册成功，但每次检索都返回错的 SKU | 服务还在占位嵌入器上。上游 `embedder_backend` 默认 `fake`（`server/config.py`），它把图片字节哈希成向量。`GET /api/health` 不报告这一项，启动也不打日志，所以这个症状是唯一的信号。设 `RETAIL_EMBEDDER=onnx`，重启，然后把所有 SKU 重新注册一遍。 |
| 设了 `RETAIL_EMBEDDER=onnx` 之后 `server` 容器立刻退出 | 要么 `RETAIL_EMBEDDER_ONNX` 是空的——上游在这个组合下拒绝启动——要么路径在容器里不存在。确认文件在 `assets/console/models/` 里，且文件名与变量一致。 |
| 切换前后注册的商品库对不上 | 不能混用。一个嵌入器产出的向量与另一个的不可比。在新模型上把所有 SKU 重新注册一遍。 |
| 计划商用部署 | 用自采或许可宽松的数据重训嵌入器，并重建每一个商品库版本。随包给出的权重不能用于商用。 |

## 步骤 3: 注册 SKU {#p3_register type=web_dashboard required=true config=devices/register_sku.yaml}

每个 SKU 用 3–8 张照片注册。每次注册生成一个新的不可变商品库版本。

### 前置条件

- 步骤 1 里的 admin token。
- 每个 SKU 3–8 张图，正面、背面、侧面，两种光照。
- 步骤 2 的 DINOv2-small 嵌入器：商品库必须用与 reComputer J30 / J40 上 TensorRT engine
  同一个模型构建，否则这个套餐的检索会返回噪声。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 注册被拒，提示图片少于三张 | 这是设计如此。 |
| 同一个 sku_id 返回 409 | 设计如此。要替换就带 `replace=true`。 |
| 不确定该统一到哪个嵌入器 | DINOv2-small 在这个套餐自己的 TensorRT engine 上、每 SKU 8 张图时实测 top-1 79.20%（fp32 参照是 79.11%；21 项检索指标全部与 fp32 保持在 0.24pp 以内）；DINOv2-base（RK3588 套餐）同档 84.67%，但没有转换过 TensorRT。 |
| 版本号不涨 | 注册没过质量闸门。响应里会说是哪一张图。 |

## 步骤 4: 构建 TensorRT engine {#p3_build type=manual required=true config=devices/jetson_trt_build.yaml}

在板上构建两个 fp16 engine，用 runtime 配置里的 SHA 校验它们，
并重跑那套产出本页数字的 parity 检查。

### 前置条件

- 一台 reComputer J40（Orin NX 16GB，family key `recomputer_j40`），装好 JetPack 6.2
  与 TensorRT 10.3——即实测数字所用的版本。engine 在它将要运行的那块板上构建——
  engine 与设备和 TensorRT 版本绑定，不得在板之间分发。
- 检测器 ONNX。本包不含它：权重训练在 SKU-110K 上，仅限学术与非商用，且禁止衍生作品。
- 步骤 2 的嵌入器 ONNX，如果还没放的话。它的许可与检测器的是两回事，限制不比后者松：
  `use_scope: non-commercial`、`redistributable: false`，继承自 JD Products-10K
  训练数据（骨干 `facebook/dinov2-small` 本身是 Apache-2.0）。不得随本包分发，
  也不得打进镜像；商用部署必须用自采或许可宽松的数据重训它，并重建每一个商品库版本——
  一个嵌入器产出的向量与另一个的不可比。
- 上游仓库 commit `16d1347` 或更新版本里的 `platforms/jetson/build_engines.py`。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `trtexec` 报 "Static model does not take explicit shapes" | 两份 ONNX 都是静态 batch-1，不要传 `--shapes`。`build_engines.py`（commit `16d1347`+）已经处理了这一点——只有真正动态 batch 轴的图才需要传。 |
| 一块板上构建的 engine 在另一块板上跑不了 | 这是预期的。engine 与设备和 TensorRT 版本绑定。按板构建。 |
| `runtime.py --dry-run` 以 exit code 2 退出 | engine 重算出的 sha256 与 `runtime.yaml` 里记的对不上。重新构建，或重跑 `build_engines.py --update-config` 刷新记录的哈希。 |
| parity 远低于实测的 99.91%（检测框一致率） | 差这么多是解码或输出布局的问题，不是 fp16 精度的问题。 |
| 检索差值远高于实测的 0.24 个百分点（21 项指标最大差） | 核对 ONNX sha256 是否为 `7f0136ef…`——差这么多更可能是嵌入器权重不对，不是 fp16 损失。 |

## 步骤 5: 验证注册、检索与设备产物 {#p3_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

复现软件闭环、管理端往返，以及产出本页数字的那套设备侧 parity 流程。

### 前置条件

- 步骤 1 到 4 已完成。
- 一份跑过 `uv sync` 的上游仓库克隆。

### 部署完成

#### 快速验证

- `uv run python tools/verify_software_loop.py` 通过。
- 管理端带 admin token 时返回递增的版本号，不带 token 时返回 401 或 403。
- `GET /v1/gallery/current/download` 返回的 tar.gz 里 SHA256SUMS 校验得过。
- `platforms/jetson/runtime.py --config platforms/jetson/runtime.yaml
  --dry-run` 通过：两个 engine 的 sha256 都与 `runtime.yaml` 一致。
- 检测 parity 检查报告框一致率接近 99.91%（50 张），检索差值检查报告
  21 项指标最大差接近 0.24 个百分点。
- 通过 `platforms/jetson/runtime.py` 跑一次收银台回放，`/healthz` 里
  `frames_dropped`、`capture_drop`、`embed_drop` 都是 0。

#### 把链路跑通

实测的收银台回放用的是合成素材，不是真实摄像头画面——在自己的板子上复现整条链路
需要补齐 `runtime.yaml` 要的四样东西：

1. **画面。** `runtime.yaml` 里 `sources[0].uri` 指向 `local/frames_checkout`，
   按配置的 `fps` 循环读一个 JPEG 目录。跑合成素材可以用
   `uv run python tools/make_checkout_sim.py --grocery-root
   /path/to/GroceryStoreDataset/dataset --skus 30 --events 40 --fps 15
   --seed 20260907 --out evaluation/data/checkout_sim` 产出 `<out>/frames/`，
   拷贝或软链到 `platforms/jetson/local/frames_checkout`。接真摄像头就把
   `sources[0].kind` 改成 `usb`，`uri` 改成设备路径（如 `/dev/video0`），
   或按 `runtime.yaml` 里的注释接 RTSP 源。
2. **商品库。** `python3 platforms/make_runtime_gallery.py --config
   platforms/jetson/runtime.yaml --skus-json
   evaluation/data/checkout_sim/gallery_skus.json` 会用上面那个工具产出的注册图，
   以 `runtime.yaml` 里配的那个模型嵌入，在 `gallery.root`（`local/gallery`）
   下建出一个版本——等有了真实 SKU，步骤 1–3 的管理端注册流程是另一条路。
3. **MQTT。** `runtime.yaml` 的 `mqtt.host` 出厂指向的是评测用的 broker；
   要发真实事件之前，先改成自己部署可控的 broker。
4. **启动。** `python3 platforms/jetson/runtime.py --config
   platforms/jetson/runtime.yaml`（照步骤 4，先加 `--dry-run` 跑一遍）。要开机
   自启就用 `platforms/jetson/retail-runtime.service` 这份 systemd 单元模板。

#### 后续步骤

- 若要 7×24 部署，跑一次比单轮 2956 帧更长的长稳。
- 若要切到货架场景，用货架 preset 的 1280² 输入重新计时——本页数字全部来自
  640² 的收银台 preset。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `runtime.py --dry-run` 以 exit code 2 退出 | 某个 engine 的 sha256 与 `runtime.yaml` 对不上。用 `build_engines.py --update-config` 重新构建，它会把新哈希写回配置。 |
| 延迟明显高于检测 5.18 ms / 嵌入 4.23 ms p50 | 检查 `nvpmodel -q` 是否为 `MAXN_SUPER`，以及是否有别的进程占着 GPU——运行时自身的并发数字（8.76 ms / 5.37 ms p50）是两个模型共享同一块 GPU 的情形，不是回归。 |
| 软件闭环过了，看起来像做完了 | 闭环跑在开发机上的 FakeEmbedder 上，证明的是协议行为，不是设备精度——上面的设备侧 parity 检查才是证明精度的那道检查。 |
| 想把它标成已验证 | 这是本包里唯一有真机设备侧运行时实测（收银台回放）的套餐；其它套餐止步于模型转换。 |
