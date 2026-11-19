# 生产工位工时与物料监测：运维与发布

这是候选发布，验证范围以 validation.md 为准。应用镜像包含 CUDA/cuDNN/TensorRT 用户态库，NVIDIA Runtime 注入驱动和宿主机多媒体接口。不能以挂载整套宿主 /usr/lib 的方式替换镜像运行依赖。

<a id="solution-naming"></a>

## 方案名称与部署标识

本方案中文名称为「生产工位工时与物料监测」，英文名称为「Workstation Time and Material Monitoring」。仓库中的唯一方案入口为 `solutions/workstation_monitoring/solution.yaml`，对外查询和部署使用 Solution ID `workstation_monitoring`，替代原候选方案 ID `jetson_worktime`。

| 用途 | 当前标识 |
|---|---|
| Solution ID 与方案目录名 | `workstation_monitoring` |
| 内部设备／步骤 ID、Compose 项目名称 | `jetson_worktime` |
| 默认部署目录 | `~/.sensecraft/deployments/jetson_worktime/` |
| 容器内应用目录 | `/opt/jetson-worktime/` |
| 镜像仓库 | `chenduola6/jetson-worktime` |

部署器按远程基础路径与内部设备 ID 拼接部署目录，因此设备 ID 和双语指南中的步骤锚点继续使用 `jetson_worktime`。已有配置、数据库、数据集与训练输出继续保存在原目录。Compose 项目名称、`WORKTIME_*` 环境变量、应用内部包名及容器路径均沿用现有值。

本次改名继续复用已发布的镜像、固定摘要与已验证的离线归档；旧名称可能出现在镜像元数据和归档文件名中，具体版本与校验值见[发布记录](release.md)。硬件与系统兼容条件仍以当前 Jetson 基线为准。

## 目录与诊断

在引擎显示的远程部署目录执行：

```sh
docker compose ps -a
docker compose logs --tail 100 web trainer
python3 scripts/release.py check
python3 scripts/release.py diagnose
```

`persistent/configs` 保存摄像头与区域设置；`persistent/data` 保存 SQLite、模型、图片与训练记录；`persistent/outputs` 保存训练产物；`persistent/logs` 保存状态文件。容器控制台日志使用 Docker local 日志驱动轮换，每服务最多约 100MB。默认关闭逐帧观察诊断，避免长期运行快速写满磁盘。应用在上传或导入模型前保留 2GB 空闲空间，但仍应定期归档图片与训练产物。

本方案不停止或删除其他 Compose 项目。默认端口已被占用时应换端口；安装阶段不会杀死占用端口的程序。USB 相机限定 V4L2 设备类型访问，设备目录只读挂载。程序以 SSH 用户同一 UID/GID 运行，根文件系统只读。

## 手动恢复

自动恢复失败时，读取 `release-state/release.json` 的 deployment_id，并在原部署目录执行：

```sh
python3 scripts/release.py rollback YOUR_DEPLOYMENT_ID
```

操作可重复执行；已提交的发布不会被旧失败回调回滚。SSH 断开后设备看护进程最多等待 15 分钟再恢复；该期间会拒绝并行发布。设备断电会终止看护进程，重新连接后再次部署会先处理未完成记录。回滚恢复配置、SQLite 与行为状态，不删除用户采集图片或新训练产物。升级前需停止训练。数据库备份使用 SQLite backup API 处理 WAL，恢复前停止当前服务并清理 WAL/SHM。

## 维护者构建

在 ARM64 Jetson 使用 `assets/docker/scripts/package.py build --resources /绝对资源目录`。资源应包含 ARM64 uv、固定 Torch/Torchvision wheels、MediaMTX、姿态模型和官方检测权重，版本和 SHA256 在 assets/image/resources.lock.json 中。资源目录放在仓库外，禁止将开发机 data、outputs、.env、摄像头凭据或设备 TensorRT 缓存加入构建。

构建后生成的 release-manifest.json 固定镜像层；发布后还应写入 registry digest。维护者执行 `package.py publish` 使用设备已有 Docker 登录发布。部署只消费预构建镜像。CUDA 基础层的复现文件在 assets/image/cuda-runtime/。

引擎取消请求会先显示已取消，设备仍可能执行恢复；确认部署步骤结束、发布记录为 rolled_back 且服务健康后再关闭工具。提交已经完成时，以设备发布记录为准。

离线导出执行 `package.py export --output /绝对输出目录`。归档包含镜像、Compose、发布管理器和摘要，校验后可用 `package.py install --archive /绝对路径/包.tar` 部署。在线部署优先使用仓库现有的一键入口；离线平台包优先使用 solution-cli stage，以保留平台统一管理。

## 兼容边界

严格拒绝不同 L4T、内核或 CPU 架构。当前系统元包名称可能与实际 L4T 组件版本不同，因此同时检查实际 L4T/内核并运行 GPU 自检。JetPack 6.2 原版系统与当前开发机混合组件栈需分别验收。Nano 无硬件编码器，使用 x264，不能以 NX 上强制 x264 的测试代替 Nano 真机验证。

8GB 设备、24 小时稳定性、断电恢复需要独立验收；未通过前保持 rc 标签。新发布不要覆盖已经分发的版本标签。数据备份、主机驱动升级、系统网络配置属于设备维护范围。
