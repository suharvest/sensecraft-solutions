## 套餐: 摄像头 + reComputer J30 / J40（Orin） {#orin}

Jetson Orin 用 TensorRT 运行分类器，提供网页、触发接口和 MQTT 输出。首次部署在设备上构建 TensorRT engine。可选开放词汇分类（步骤 4），在基线跑通后再切换。

- **摄像头：** USB 或 IP 摄像头，俯视投放区，一次拍一件。
- **可选外设：** 实体按钮作为触发源；翻盖、继电器或指示灯由 actuator 回调驱动。接线与 GPIO 读取需自行集成。

**使用限制：**

- 中国四分类映射由本项目维护，各城市口径不同，不要作为收费、处罚或合规判定的唯一依据。
- 一帧只分类一件物品，放两件时只输出一个结果。
- `textile`（布料）没有训练数据，不会被识别；`hazardous`（有害垃圾）不会输出。
- 训练数据是干净的单件物品照片，湿的、压扁的、堆叠或装袋的垃圾上精度会下降，请用现场数据验证。

## 步骤 1: 部署垃圾分类 {#deploy_jetson_waste type=docker_deploy required=true config=devices/jetson_waste.yaml}

填写设备、摄像头和分类器选项，部署步骤会下载模型、构建 engine，并启动分类器和本地 MQTT broker。首次启动需要等待 engine 构建完成。

### 前置条件

- JetPack 6.x 的 Jetson Orin，已配置 NVIDIA container runtime。
- 至少 10 GB 可用磁盘。
- 使用 USB 摄像头时，在 `assets/jetson/docker-compose.yml` 里取消注释对应的 `/dev/videoN` 行，不要挂载整个 `/dev`。
- 容器镜像需在设备上从上游仓库构建，retag 成 compose 文件里的名字，或把 `WASTE_IMAGE` 设为本地 tag。
- 分类器选项：默认 `baseline`；`open_vocab` 见步骤 4。

### 故障排查

| 现象 | 处理 |
|---|---|
| `This target is not a NVIDIA Jetson` | 目标机器不是 Jetson，换成 Jetson Orin。 |
| `trtexec not found` | 执行 `sudo apt install tensorrt`。 |
| `WARNING: nvidia runtime missing` | 执行 `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`，然后重新部署。 |
| Engine 构建报 `Static model does not take explicit shapes` | 去掉 `--minShapes`/`--optShapes`/`--maxShapes` 参数。 |
| ONNX 的 sha256 对不上 | 文件不是发布版本，不要继续。删除设备上的 ONNX 文件后重新部署，会重新下载。 |
| 找不到 `docker compose` | 手动安装 `docker-compose-plugin`。 |
| Compose 解析 `._docker-compose.yml` 失败 | 在设备上执行 `find … -name '._*' -delete` 删除 Mac 带来的附属文件。 |
| 容器起来了但没有相机 | 取消注释 compose 文件里的 `/dev/videoN` 行。 |
| `edge-waste-mosquitto` 一直重启，报 `Address in use` | 1883 被其他 broker 占用。把 `config/mosquitto.conf` 和 `config/config.json` 里的 `mqtt.port` 改成空闲端口（如 18831），再执行 `docker compose up -d --force-recreate mosquitto`。 |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml default=true}

从本机通过 SSH 部署到 Orin，填写设备 IP、SSH 凭据、摄像头地址和分类器选项。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml}

直接在 Orin 上运行部署。

## 步骤 2: 查看实时分类画面 {#preview_orin_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

打开设备自带的页面，查看实时画面、触发按钮和最近的分类结果。在验证前用它对准摄像头。

### 故障排查

| 现象 | 处理 |
|---|---|
| 页面打不开 | 在设备上执行 `docker ps` 确认 `waste` 容器在运行，查看 `docker logs edge-waste-app`。 |
| 预览是黑的 | USB 摄像头检查 `/dev/videoN` 是否已挂进容器；RTSP 先用 VLC 测试地址。 |
| 预览正常但 `/events` 一直空 | 还没有触发。默认模式下只在触发时分类。 |
| 物品在画面里很小 | 调整摄像头，让物品占满大部分画面。 |

## 步骤 3: 接好触发并确认一次分类 {#trigger_setup_orin type=manual required=true verify=true config=devices/trigger_setup.yaml}

把一件物品放到摄像头下，触发一次，确认 MQTT 收到一条分类结果。

### 前置条件

- 步骤 1 已完成，容器在运行。
- 同网络的机器上有 `mosquitto_sub`，或使用 broker 容器：`docker exec edge-waste-mosquitto mosquitto_sub …`。
- 一件非布料的待分类物品。

### 部署完成

分类器已运行，并完成一次端到端分类。

#### 快速验证

1. 打开 `http://<设备IP>:8080/`，确认画面对准投放区，物品占满大部分画面。
2. 订阅：`mosquitto_sub -h <设备IP> -t '<设备名>/waste/+/results' -v`。
3. 触发一次：`curl -X POST http://<设备IP>:8080/trigger`。
4. 确认收到一条消息，`category` 与 `top3[0]` 一致。
5. 在 800 ms 内触发两次，确认只收到一条消息。

#### MQTT 消息

每次分类发布一条 JSON，主要字段如下（`stream_id` 从 payload 读取，不要解析主题）：

```json
{
  "type": "waste_sorting_result",
  "stream_id": "bin1-cam1",
  "timestamp": 1757030400123,
  "trigger": "button",
  "category": {
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "top3": [
    {"rank": 0, "class_name": "plastic", "confidence": 0.913, "china_category": "recyclable"},
    {"rank": 1, "class_name": "glass", "confidence": 0.052, "china_category": "recyclable"},
    {"rank": 2, "class_name": "residual", "confidence": 0.021, "china_category": "residual"}
  ],
  "image_ref": {
    "kind": "local",
    "uri": "/var/lib/edge-waste-sorting/captures/2026-09-05/bin1-cam1-4207.jpg"
  },
  "model": {"name": "efficientnet_lite0_waste8", "accelerator": "tensorrt"}
}
```

#### 下一步

- 接翻盖或指示灯：设置 `"actuator": {"enabled": true, "min_confidence": 0.5}` 并编写集成代码。
- 正式使用前把 MQTT 指向带凭据的 broker，自带 broker 允许匿名连接，只用于调试。
- 需要识别词表外物品或不重训加类时，见步骤 4。
- 采集现场数据验证精度。

### 故障排查

| 现象 | 处理 |
|---|---|
| 一条消息都没有 | 查看 `/healthz` 的触发计数；不增长时检查 `config/config.json` 里的 `trigger.sources`。 |
| 按一次按钮出两条消息 | 调高 `trigger.debounce_ms`，不低于约 300 ms。 |
| 类别总是 `residual` | 置信度低于 `rules.min_confidence`。检查光照、取景，以及物品是否属于八个类别。 |
| 玻璃与塑料判错 | 两者都属于可回收物，四分类结果不受影响。 |
| 大多判成 `organic` | 改善取景与光照；彻底解决需要重新平衡数据后重训。 |
| 布料物品被判成别的 | 属已知限制，布料没有训练数据。 |
| 物品不是生活垃圾 | 基线分类器无法拒识词表外物品，需要时切换到步骤 4。 |

## 步骤 4: 切换到开放词汇分类（可选） {#enable_open_vocab_orin type=manual required=false verify=true config=devices/enable_open_vocab.yaml}

换成 SigLIP 2 开放词汇分类器：可以拒识词表外物品、中英文输出、不重训加类，代价是 top-1 精度下降、时延上升。

### 前置条件

- 步骤 1 已用 `model_track: baseline` 跑通。
- 额外约 372 MB 放视觉模型，另需 engine 空间。
- 原型库和 meta 文件需手工拷到设备，并用 `assets/models/SHA256SUMS.open_vocab` 执行 `sha256sum -c` 校验。
- 仅 Orin 套餐支持。

### 故障排查

| 现象 | 处理 |
|---|---|
| Engine 构建比基线久得多 | 属正常，不要中途终止。 |
| Engine 构建报 `Static model does not take explicit shapes` | 去掉 `--minShapes`/`--optShapes`/`--maxShapes` 参数。 |
| 时延明显变高 | 属正常。无法接受时切回 `baseline`。 |
| 置信度整体变了 | 修改过 `temperature` 后需要重调 `min_confidence`；标定值是 0.0075。 |
| 换成中文四分类原型库后四分类精度下降 | 改用先分八类再映射四分类的层级方式。 |
| 未知物体仍拿到高置信度材质标签 | `residual` 类上的拒识效果较弱，属已知限制。 |

## 套餐: 摄像头 + reComputer R2000（Hailo-8） {#recomputer_r20}

reComputer R2000 系列（Hailo-8）在 NPU 上运行 EfficientNet-Lite0 分类器，提供网页、触发接口和 MQTT 输出。

- **摄像头：** USB 或 IP 摄像头，俯视投放区，一次拍一件。
- **可选外设：** 实体按钮作为触发源；翻盖、继电器或指示灯由 actuator 回调驱动。接线与 GPIO 读取需自行集成。

**使用限制：**

- 中国四分类映射由本项目维护，各城市口径不同，不要作为收费、处罚或合规判定的唯一依据。
- 一帧只分类一件物品。
- `textile`（布料）不会被识别，`hazardous`（有害垃圾）不会输出。
- 请用现场数据验证精度；长时间满载运行请在出货整机上验证散热。
- 不支持开放词汇分类。

## 步骤 1: 在 Hailo 上部署垃圾分类 {#deploy_hailo_waste type=docker_deploy required=true config=devices/hailo_waste.yaml}

填写设备和摄像头信息，部署步骤会检查 Hailo 环境，下载并校验模型，然后启动分类器。

### 前置条件

- 装有 Docker 的 Raspberry Pi OS，Hailo-8 已插入，存在 `/dev/hailo0`。
- 已安装 HailoRT 4.21.x，并执行 `sudo apt-mark hold hailort hailort-pcie-driver`。
- `/etc/modprobe.d/` 里有 `options hailo_pci force_desc_page_size=4096`，设置后重启过。
- 至少 4 GB 可用磁盘。
- 设备能访问 `sensecraft-statics.seeed.cc`（HTTPS），用于下载模型。
- 容器镜像需在设备上从上游仓库构建，retag 成 compose 文件里的名字，或把 `WASTE_IMAGE` 设为本地 tag。

### 故障排查

| 现象 | 处理 |
|---|---|
| `No /dev/hailo0` | 检查模块是否插好：`lspci \| grep -i hailo`、`dmesg \| grep -i hailo`。 |
| `libhailort.so.4.21.0 not found` | 安装 HailoRT 4.21，驱动、库和 Python 绑定保持同一版本。 |
| `expected both hailort and hailort-pcie-driver on hold` | 执行 `sudo apt-mark hold hailort hailort-pcie-driver`。 |
| `hailo_pci is missing force_desc_page_size=4096` | 执行 `echo 'options hailo_pci force_desc_page_size=4096' \| sudo tee /etc/modprobe.d/hailo.conf && sudo reboot`。 |
| `No HEF for this solution` | 模型下载或校验失败，重跑步骤 1。设备无法访问 `sensecraft-statics.seeed.cc` 时，在别处下载后放到步骤提示的路径。 |
| `_pyhailort` 导入报错 | Python 绑定只能在同一 Python 小版本下导入（Bookworm 为 3.11，trixie 为 3.13），确认系统与绑定版本一致。 |
| 自己训练的 MobileNetV3-Small 在 Hailo 上精度很差 | 该模型 INT8 量化后精度失效，使用随附的 EfficientNet-Lite0。 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml default=true}

从本机通过 SSH 部署到设备。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml}

直接在设备上运行部署。

## 步骤 2: 查看实时分类画面 {#preview_hailo_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

打开设备自带的页面，查看实时画面、触发按钮和分类结果。在验证前用它对准摄像头。

### 故障排查

| 现象 | 处理 |
|---|---|
| 页面打不开 | 在设备上执行 `docker ps` 确认 `waste` 容器在运行，查看 `docker logs edge-waste-app`。 |
| 预览是黑的 | USB 摄像头检查 `/dev/videoN` 是否已挂进容器；RTSP 先用 VLC 测试地址。 |
| 预览正常但 `/events` 一直空 | 先触发一次；仍为空时检查模型是否下载成功，见步骤 1 的「No HEF for this solution」。 |
| 物品在画面里很小 | 调整摄像头，让物品占满大部分画面。 |

## 步骤 3: 接好触发并确认一次分类 {#trigger_setup_hailo type=manual required=true verify=true config=devices/trigger_setup.yaml}

把一件物品放到摄像头下，触发一次，确认 MQTT 收到一条分类结果。

### 前置条件

- 步骤 1 已完成，容器在运行。
- 同网络的机器上有 `mosquitto_sub`，或使用 broker 容器：`docker exec edge-waste-mosquitto mosquitto_sub …`。
- 一件非布料的待分类物品。

### 部署完成

分类器已在 Hailo-8 上运行，并完成一次端到端分类。

#### 快速验证

1. 打开 `http://<设备IP>:8080/`，确认画面对准投放区，物品占满大部分画面。
2. 订阅：`mosquitto_sub -h <设备IP> -t '<设备名>/waste/+/results' -v`。
3. 触发一次：`curl -X POST http://<设备IP>:8080/trigger`。
4. 确认收到一条消息，`category` 与 `top3[0]` 一致。
5. 在 800 ms 内触发两次，确认只收到一条消息。

#### MQTT 消息

消息格式与 Orin 套餐相同，`model.accelerator` 为 `hailo`：

```json
{
  "type": "waste_sorting_result",
  "stream_id": "bin1-cam1",
  "category": {
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "model": {"name": "efficientnet_lite0_waste8", "accelerator": "hailo"}
}
```

#### 下一步

- 保持两个 Hailo 包 hold 状态和 `force_desc_page_size=4096` 设置，升级 HailoRT 会导致模型无法加载。
- 正式使用前把 MQTT 指向带凭据的 broker。

### 故障排查

| 现象 | 处理 |
|---|---|
| 一条消息都没有 | 检查 models 目录里是否有 HEF 文件；没有则重跑步骤 1，有则查看容器日志。 |
| 触发计数不动 | 检查 `config/config.json` 里的 `trigger.sources`。 |
| 按一次按钮出两条消息 | 调高 `trigger.debounce_ms`，不低于约 300 ms。 |
| `configure(hef)` 崩溃 | 设置 `force_desc_page_size=4096` 后重启设备。 |
| 预测集中到单一类别 | 反馈给我们。 |
| 需要开放词汇分类 | 本套餐不支持，使用 Orin 套餐。 |

## 套餐: reCamera（SG2002） {#recamera}

## 步骤 1: 在 reCamera 上部署分类器 {#deploy_recamera_waste type=recamera_cpp required=true config=devices/recamera_waste.yaml}

分类器安装到 reCamera 上，在相机自身的 TPU 上运行，不需要主机。

需要：相机可通过 USB 或网络访问、`recamera` 用户的 SSH 密码、`/userdata` 上约 10 MB 可用空间。

### 接线

1. 用 USB-C 连接 reCamera，或确认它在网络中可达
2. 填入 IP 地址（USB 连接默认为 `192.168.42.1`）和 `recamera` 用户的 SSH 密码
3. 部署

### 落到设备上的内容

部署会安装应用和模型，把数据流 ID、MQTT 目标、置信度阈值等设置写入 `/etc/waste-sorting.conf`，并启动应用。相机同一时间只运行一个应用，重启后由控制台恢复。

### 故障排查

| 现象 | 处理 |
|------|------|
| 应用一启动就退出 | 模型未加载。确认 `/userdata/local/models/efficientnet_lite0_waste8_cv181x_bf16.cvimodel` 存在且完整，重新部署。 |
| 停掉另一个应用后 `start` 连续两次失败 | 重启相机。 |

## 步骤 2: 确认一次分类 {#verify_recamera_waste type=manual required=true verify=true}

步骤 1 完成后应用已在运行。在投放区放一件物品，订阅步骤 1 填写的 broker（默认是相机自身）：

```bash
mosquitto_sub -h <相机IP> -t 'waste/<stream id>/results' -v
```

一件物品产生一条 JSON 记录，包含物料类别和中国四分类。

### 故障排查

| 现象 | 处理 |
|------|------|
| 主题上什么都没有 | 核对步骤 1 填写的 broker 地址、端口（默认 1883）和凭据，订阅同一个 broker |
| 一帧两件物品只出一条记录 | 属已知限制，一次投放一件 |

## 套餐: reCamera Pro {#recamera_pro}

分类器以 INT8 在 reCamera Pro 自身的 NPU 上运行，不需要主机。

## 步骤 1: 在 reCamera Pro 上部署分类器 {#deploy_recamera_pro_waste type=recamera_pro_app required=true config=devices/recamera_pro_waste.yaml}

先在相机 Web 控制台的应用中心安装 `waste-sorting` 应用，本步骤下发设置并将它设为当前应用。激活后相机上正在运行的其他应用会停止。

需要：Web 控制台管理员凭据、`/userdata` 上约 10 MB 可用空间。

### 接线

填写设备名称。需要把结果发到其他系统时再填 broker 地址，每次分类会以一条 JSON 发到 `waste/<设备名称>/results`；broker 留空时结果只在相机上的应用面板查看。

### 故障排查

| 现象 | 处理 |
|------|------|
| 应用中心里没有这个应用 | 先在应用中心安装 `waste-sorting`，本步骤不负责安装 |
| 激活超时 | 重跑本步骤；仍失败时在应用中心查看应用状态 |
| 应用起来了但从不分类 | 确认模型已下发到 `/userdata/local/models/waste-sorting/` |
| broker 上收不到事件，但相机面板上有结果 | 核对 broker 地址、端口和凭据 |

## 步骤 2: 确认一次分类 {#verify_recamera_pro_waste type=manual required=true verify=true}

在投放区放一件物品，确认出现一条新结果：broker 留空时看应用面板，填了 broker 时订阅：

```bash
mosquitto_sub -h <broker IP> -t 'waste/<设备名>/results' -v
```

需要认证时带上 broker 的端口和凭据。一件物品产生一条 JSON 记录。

### 故障排查

| 现象 | 处理 |
|------|------|
| 主题上什么都没有 | 核对 broker、端口和设备名，设备名是主题的第二段 |
| broker 拒绝连接 | 使用步骤 1 填写的用户名和密码 |
| 哪里都没有结果，包括相机上 | 在应用中心确认 `waste-sorting` 仍是当前应用 |

## 套餐: 摄像头 + reComputer RK3588 {#recomputer_rk3588}

分类器以 INT8 在 reComputer RK3588 的 NPU 上运行，适合一台主机服务多个投放点，或摄像头无法更换的场合。

## 步骤 1: 在 reComputer RK3588 上部署分类器 {#deploy_recomputer_rk3588_waste type=manual required=true verify=true config=devices/recomputer_rk3588_waste.yaml}

按四个子步骤操作：核对模型、安装 RKNN Lite 运行时、准备一帧输入、运行分类。

需要：能 SSH 登录板卡、几百 MB 可用空间，以及已转换好的模型；自行转换时需要一台装有 `rknn-toolkit2` 2.3.2 的 x86_64 Linux 主机，转换不能在板卡上进行。

### 故障排查

| 现象 | 处理 |
|------|------|
| `init_runtime` 处只抛一个 `RKNN_ERR_FAIL` | 安装与板卡上 `librknnrt` 同版本的 Python 绑定 |
| 没有可核对的模型文件 | 在装有 `rknn-toolkit2` 2.3.2 的 x86_64 Linux 主机上转换模型后拷到板卡 |
