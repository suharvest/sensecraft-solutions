# Deployment validation record — 2026-09-10

本记录是本地审核稿，记录方案包动作与发布状态；不包含真实密钥。

## 动作模拟验收

已用统一平台脚本对 6 个 cloud target（`cloud_j30`、`cloud_j40`、`cloud_rk3576`、`cloud_rk3588`、`cloud_r2000`、`cloud_r2000_cpu`）做配置模拟。这里的 cloud 部署按一个平台步骤处理：后台和对应的转写服务由同一个部署目标准备，不再把“部署后台”和“部署服务端 ASR”作为两个用户步骤。测试使用临时目录，未连接或修改真实设备。

Cloud 验收覆盖：`remote_path/<id>` 目录、compose 目录上传约定、首次生成 ASR key、重复执行保持 key、ASR `.env` `0600`、backend 变量保留、自动写入 `CAPTURE_OVS_BASE_URL`/`CAPTURE_OVS_API_KEY`、缺失 `voice-service.yaml` 时安全失败、Compose 文件存在检查，以及 MySQL、MinIO、OVS、voice-service、voice-web、gateway 六个服务的统一配置检查。未把“仅调用 voice-service”或重启逻辑作为验收结论。

Local 验收覆盖：原始模板正常生成配置、重复执行稳定、生成文件 `0600`、HTTP batch 与 audio stream 关闭、请求 header 一致、非法 URL/key 拒绝且无副作用、失败时原模板不写入。输入值通过 action executor 的环境变量语义传递。

可重跑证据：

- 统一平台复跑脚本：`/tmp/retail_voice_platform_check-20260910-rerun.py`
- 统一平台复跑原始输出：`/tmp/retail_voice_platform_check-20260910-rerun-v2.out`（6 个平台配置目标、4 个 Compose 配置检查均 `PASS`，末尾为 `ALL PASS`）
- 已发布 digest 复跑原始输出：`/tmp/retail_voice_platform_check-20260910-rerun-v4-pinned.out`（仅 fixture Compose 渲染与字段断言，不是设备启动）
- `/tmp/local_action_review.py`、`/tmp/local_action_review.out`、`/tmp/cloud_action_review.py`、`/tmp/cloud_action_review.out`：历史验证材料，当前结论不引用。

历史记录中的 Gateway “18 项、本人未重跑”已被当前复核替代：gateway 副本与上游实现字节一致，当前 19 项回归通过（见下方当前发布状态）。

## 镜像与发布状态

4 个 ASR 镜像的 registry digest 来源为 `openvoicestream/deploy/IMAGE-TAGS.md:24-27`，对应 `retail-voice-rpi-20260910-v014a0`、`retail-voice-rpi-hailo-20260910-v014a0`、`retail-voice-rk-20260910-v014a0` 和 `retail-voice-jetson-20260910-v014a0`。这些镜像记录的 voxedge 版本为 `0.0.14a0`，已发布的 voxedge 版本为 `0.0.14a0`。

首轮 backend/web 发布目标、必填占位和失败记录均为历史证据，保留如下用于追溯。当前五份发布 compose 已移除 `VOICE_SERVICE_IMAGE`/`VOICE_WEB_IMAGE` 必填占位并固定已发布 digest。源配置保留 ASR key 生成、64 MiB 音频上限；1200 秒是 CLI 健康等待上限，不是 HTTP timeout。

### Orin NX CLI 验证

2026-09-10 使用 SenseCraft Solution CLI 对 Fleet 设备 `orin-nx`（主机名 `orinnx`）执行了一次实际部署验证。部署 ID 为 `d76cdbb3-6cc6-4c12-a752-20049601e6a2`，最终 `exit 1`。连接、硬件检测、网络、操作系统、Docker 检查、远程目录准备、文件上传和前置配置阶段均通过；失败发生在 `pull_images` 阶段：`VOICE_SERVICE_IMAGE` 未提供，Compose 明确要求 capture-capable voice-service image，不能使用当前 frozen image。原始日志：`/tmp/retail-voice-orin-nx-solutionctl-20260910.log`。

本次首轮失败没有进入加载镜像、启动服务或健康检查阶段。Orin NX 上原有容器未停止、未重启、未替换；该记录是历史失败，不代表当前候选。

第四次 CLI 实际部署已完成 `start_services` 与 `health_check`：部署 ID `5b393333-80f1-4c67-88df-5ffaf25718b0`，日志显示 `Services started`、`All services healthy`，`SOLUTIONCTL_EXIT=0`（原始日志：`/tmp/retail-voice-orin-nx-solutionctl-20260910-retry4.log`）。随后真实音频请求返回 HTTP 502，响应体为 `ovs_status_404`；这次 404 是上游模型发现为空导致的 `unknown_model`，不是路由不存在。对应源码当时的 `/v1/models` 返回 `data: []`，五个 profile 未提供对外 `asr_model_id`；模型选择回退链见 `openvoicestream/server/main.py:5042-5046` 与 `openvoicestream/server/api/openai_compat.py:897`。现已在 profile 与部署环境补齐模型 ID；第五次 NX 实机音频验收仍待结果，不能据此宣称通过。第五次运行日志（`/tmp/retail-voice-orin-nx-solutionctl-20260910-retry5.log`）只作为当前运行记录，不能替代音频验收证据。

首轮待审批候选（历史）如下：

| 产物 | 精确镜像 ID | 目标标签 |
|---|---|---|
| voice-service | `sha256:72463e94c6cf9d3476643f3af91af17dae4f3b80412ddb3d8f3c331f62922bde` | `sensecraft-missionpack.seeed.cn/solution/sensecraft-voice-service:retail-voice-20260910-local-whisper` |
| voice-web | `sha256:3563ed994c0bc02e704b4970c73fd63d58dbecb39d38e1f79754d18a57e9de81` | `sensecraft-missionpack.seeed.cn/solution/sensecraft-voice-web:retail-voice-20260910-recordings-layout` |

上述目标标签、旧归档和 registry 504 均为首轮历史记录。当前发布使用新构建并已由 root 根据 Spark 原始 push 日志核验成功：`/home/harvest/spark-build/retail-voice-speaker-v6-20260910/service-push.log` 与 `web-push.log` 均 exit 0。

归档内容核对：OCI index 记录的源镜像 ID 为 `72463e94c6cf9d3476643f3af91af17dae4f3b80412ddb3d8f3c331f62922bde` 和 `3563ed994c0bc02e704b4970c73fd63d58dbecb39d38e1f79754d18a57e9de81`；归档 `manifest.json` 的 Config 及 Spark `docker load` 后镜像 ID 为 `552bd92041f82670c6f1cab87fe0a8edf2ef796c2a2459214908995e65b8dc1f` 和 `3bca61b3cace3ca5207301dd95c493c4656c8219f2e78a99b904fa324696c875`，均为 `linux/arm64`。该差异是 Docker 归档的 index/manifest 表示，不表示加载了错误版本。

## 范围与运行约束

两种模式（server transcription 与 local client transcription）都必须先有零售后台；server 模式要求后台与 ASR 在同一台主机，local 模式通过后台地址与 key 自动接线。

本次未做全平台硬件端到端测试。Wiki/RD 内容仍是本地审核稿，尚未发布。

## 当前发布状态（2026-09-10）

当前五份 compose（`backend`、`cloud-r2000-cpu`、`cloud-r2000`、`cloud-rk`、`jetson-cloud`）均固定以下已发布镜像：

| 产物 | 发布镜像 digest | config digest |
|---|---|---|
| voice-service v6 | `sha256:28283325afdfbe7a698f7b2eaf7a2af6c601d3acc012aa662851a01dfcd92817` | `sha256:7abfcd1f286c937471ef22be0be48d40b43b2dccfc6aec16d2ad4053595dc56a` |
| voice-web v2 | `sha256:0706c600928f1d2289934f38d09dee888f92f55c54e4ea0d0058cbf70663c01b` | `sha256:45723aab011d27d3f46286159c24b475fd856b1a92ad329afe289ad963baf21b` |

v6 backend 源 artifact `/tmp/sensecraft-release-20260910/server-final-v6-arm64.gz` SHA256 为 `1c4f6f9a7de00eafed45f4c952340e9a6ac693e8f55567bd47d2ea930a50d588`；v2 frontend 源 archive `/tmp/sensecraft-release-20260910/web-speaker-final-v2.tar.gz` SHA256 为 `3afc04f3512fb699ce4e7bbe8e8c836582b6c01c6bdd22685e10fe98e4119fc0`。

Gateway 副本与上游实现字节一致，当前 19 项回归通过；此前文档中的“18 项、本人未重跑”表述已过时。配置复跑原始输出为 `/tmp/retail_voice_platform_check-20260910-rerun-v4-pinned.out`，fixture 仅用于 compose 渲染和字段断言，不构成真实设备启动证据。Jetson 继续使用已发布 ASR image `4d8470906d2ff3ae494c94b9107c09f42f4849b429d98a2b6a5bc1afcc5e7929`，普通 text-only 路径开启，speaker 默认关闭。

## 最新业务候选边界（2026-09-10）

当前已发布业务版本为 v6 backend 与 v2 frontend：

- `/tmp/sensecraft-release-20260910/server-final-v6-arm64.gz` SHA256 `1c4f6f9a7de00eafed45f4c952340e9a6ac693e8f55567bd47d2ea930a50d588`；解压后二进制 SHA256 `fbbcf264a2f27e4aab896197e57752b226c306ad63961f43d9da5cf20cc307e9`。
- `/tmp/sensecraft-release-20260910/web-speaker-final-v2.tar.gz` SHA256 `3afc04f3512fb699ce4e7bbe8e8c836582b6c01c6bdd22685e10fe98e4119fc0`。
- Jetson compose 继续使用已发布 ASR image `seeed-local-voice@sha256:4d8470906d2ff3ae494c94b9107c09f42f4849b429d98a2b6a5bc1afcc5e7929`；普通 text-only ASR 路径开启，speaker diarization 默认关闭。本轮不把 RK3576 speaker patch 移植到 Jetson。
- UI 的 `requestId` fallback、AI toolbar/mode 和 dashboard created-time 排序已有单测或浏览器 mock 证据；这些证据不等同于本轮 Jetson 真实页面验收。speaker candidate 的真实 diarization 仍存在空文本 segment，保持 partial/unknown 边界。

本轮方案包配置复跑原始输出保存在 `/tmp/retail_voice_platform_check-20260910-rerun-v2.out`，四份 compose 的 upstream/model 字段和六份 cloud descriptor 的 env 约定均通过。原先文档所述完整 first/repeat/reupload/missingcfg 脚本在当前工作区不可读取；本次复跑脚本对 descriptor action 源码做了对应静态检查，不能把该检查写成真实设备初始化或发布成功。

Wiki/RD 的部署说明已核对：两种模式共用零售后台；服务端模式在同一主机部署后台与 ASR，设备本地模式由客户端使用后台地址和 operator key 上传最终文本。部署页面的步骤与该边界一致（`seeed-solutions-hub/content/reference-designs/retail_voice/wiki/{en.md,zh-CN.md}`）。Wiki/RD 中的容量数字是其注明的历史 bench 结果；J3011 SenseVoice 当前表值为 p50 167 ms / p95 293 ms，来源为 `sensecraft-solutions/solutions/retail_voice/docs/asr-concurrency.md:20` 引用的 OpenVoiceStream `bench/asr_bench/results/concurrency-orin-nano-ceiling.md`，未在本轮重新压测。

### 第五轮 NX 实机验收状态

部署 ID `a2bd437f-88f0-4793-8437-483632f6ba6e` 执行结果为 `exit 0`。本轮确认 5 个 Docker healthcheck 为 healthy，gateway 正在运行；设备上原有 3 个容器仍在运行，剩余磁盘空间为 24 GB。`/v1/models` 返回 HTTP 200，模型为 `sensevoice`。

合成 sample 上传返回 HTTP 200 并完成持久化：管理端返回 HTTP 200、`status=completed`、`material_complete=true`、`uploads=1`；重传返回 `reused=true`。首个本地项目生成的 espeak 测试音频 smoke 仍为 `exit 1`，因为实际识别文本 `This an unemployment and` 与期望 `This is a deployment test` 不匹配。

第二个本地项目生成测试音频已用正确 EXPECT 复核通过。最终真实 tee 记录 `/tmp/retail-voice-orin-nx-public-fixture-smoke-20260910.log`：`TRANSCRIPT='Risk begins with subtle change'`、`TRANSCRIPT_MATCH=True`、`UPLOAD_HTTP_STATUS=200`、`UPLOAD_PERSISTENCE=persisted`、`UPLOAD_REUSED=True`、`MODELS_HTTP_STATUS=200`、`CAPTURES_HTTP_STATUS=200`、`CAPTURE_MATCH_COUNT=1`、`CAPTURE_DETAIL_HTTP_STATUS=200`、`CAPTURE_STATUS=completed`、`CAPTURE_MATERIAL_COMPLETE=True`、`CAPTURE_COMPLETED_UPLOADS=1`。该结果只证明此指定生成样本的转写、持久化和幂等重传；不能外推为全局准确率。此前 `/tmp/retail-voice-orin-nx-public-fixture-smoke-20260910-raw.log` 与 `/tmp/retail-voice-orin-nx-smoke-20260910-raw.log` 是人工整理摘要，不能称为原始输出；首个 espeak 偏差保留。真实手机尚未操作，全平台硬件验收未完成，Wiki/RD 仍是本地审核稿。
