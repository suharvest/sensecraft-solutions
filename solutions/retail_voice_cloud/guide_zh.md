## 套餐: 服务端栈 + 手机 App {#app_capture}

一台主机跑完整链路。你已有的手机 App 负责录音并上传到这套栈对外提供的 ASR 端点；
转写、脱敏、入库、导出与删除都发生在这里。

| 设备 | 用途 |
|--------|---------|
| 栈主机（reComputer RK3576，或其他 arm64 Linux 主机） | ASR、voice-service、MySQL、MinIO、管理后台 |
| 手机 App（你的，不在本包内） | 采集音频并上传到 ASR 端点 |

**重要：** 这不是合规认证。脱敏只覆盖文本——音频在保留期内是未脱敏的。
本套餐对外提供的端点由声纹容器提供，其镜像仍待构建验证且未 push；
在它出来之前，本套餐做到栈起来为止。
脱敏在 114 条金标准集上的成绩是 precision 0.98 / recall 0.95，也就是会漏；
低置信实体是标记复核而不是遮蔽。

## 步骤 1: 部署语音服务端栈 {#cloud_stack type=docker_deploy required=true config=devices/cloud_stack.yaml}

拉取冻结镜像，在设备上写 `.env` 与服务配置，启动 MySQL、MinIO、ASR 后端、
voice-service 与管理后台。

### 前置条件

1. 一台装了 Docker、SSH 可达、至少 20 GB 可用空间的 arm64 Linux 主机。
2. 开始前先生成四个密钥——各执行一次 `openssl rand -hex 32`——分别用于
   JWT key、operator 令牌、admin 令牌、MinIO 私有密钥。
3. 现在就定下保留期。原音频默认 24 小时，部署表单还提供 6 小时与 1 小时；
   之后再改要编辑设备上的 `config/voice-service.yaml` 并重启 voice-service。
4. 首次部署要拉好几 GB 镜像，其中大部分是语音容器。网络慢的话，
   部署里耗时最长的是这一段，不是启动。
5. 主机必须是 arm64。冻结镜像没有 amd64 变体，随包的 ASR 镜像是 RK3576 NPU 构建。
6. 其中三个镜像还没进 registry。`docker manifest inspect` 对 voice-service、voice-web
   和声纹镜像返回 "artifact not found"，而语音、MySQL、MinIO 三个能解析出来。
   先把它们推上去，并用 `docker buildx imagetools inspect` 复核 digest，
   这一步才拉得到东西。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `up -d` 停在 ASR 镜像上 | 镜像很大、registry 可能慢；重跑部署，已拉到的层会续上 |
| voice-service 一直不健康 | `docker logs c4-voice-service`——常见原因是 `config/voice-service.yaml` 里还留着 `CHANGE_ME_` 占位符，或 `.env` 与配置文件里的 MySQL 口令不一致 |
| 所有 API 调用都 401 | 你发的令牌不在 `VOICE_API_TOKENS` 里；格式是 `name:role:token`，逗号分隔 |
| 返回的是 403 而不是 401 | 凭据有效但角色档位不够——删除与导出需要 admin |
| 别的机器连不上 MySQL | 有意为之：MySQL 与 MinIO 只绑 127.0.0.1。要远程连走 SSH 隧道 |
| 8080 上的 `/ws` 连不上 | 声纹容器在 `voiceprint` profile 里默认不启动；它的镜像仍待构建验证 |
| 拉 voice-service 或 voice-web 报 "not found" | 这两个镜像还没推到 registry——先构建并推送，再确认 compose 里的 digest 与 registry 返回的一致 |
| 莫名出现云端分析容器 | 它只在 `--profile cloud-analytics` 时启动；如果在跑，说明有人开了它，文本正在离开这台主机 |

### 部署目标: {#cloud_stack_remote type=remote device=stack_host device_name="栈主机" config=devices/cloud_stack.yaml default=true}

通过 SSH 部署到网络上的一台主机。这是常规路径。

### 部署目标: {#cloud_stack_local type=local device=stack_host device_name="栈主机" config=devices/cloud_stack.yaml}

部署到本机，适用于栈就跑在你操作的这台机器上。同一份 compose、同样的输入，不需要 SSH 凭据。

---

## 步骤 2: 在手机 App 里配置 ASR 端点 {#asr_endpoint type=manual required=true config=devices/asr_endpoint.yaml}

把端点和 operator 令牌交给 App，然后自己连一次确认端点会应答。

### 前置条件

1. 先让 App 侧告诉你三件事：它的 ASR 客户端拼出来的 WebSocket 路径与查询参数格式、
   它怎么传凭据（自定义头、`Authorization: Bearer`，还是查询参数）、
   它上传的音频格式。App 配置页里有本页没有对应项的字段，按 App 配置页的说明填写。
2. 本端点这三条凭据通道都收，音频要求原始 PCM 二进制帧：16 kHz、单声道、
   有符号 16 位小端，单条消息不超过 2 MiB。不是这个格式就要在 App 侧转换。
3. 端点地址是 `ws://<栈主机>:8080/ws?token=<operator 令牌>`。
   交出去的是 operator 令牌，绝不是 admin 令牌。
4. 连上之后服务端会先发
   `{"type":"connection","message":"WebSocket connected, ready for audio","session_id":"..."}`；
   采集过程中发 `{"type":"vad","status":"speech_detected"|"silence",...}`，
   每句话一条 `{"type":"final","text":...,"speaker":{...}}`。
5. 出了局域网就在前面终结 TLS，交给 App 的换成 `wss://`——令牌是走查询参数的。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 还没升级连接就以 HTTP 401 断开 | 令牌没带或不对——鉴权发生在 WebSocket 升级之前，这是设计如此 |
| 返回的是 HTTP 403 | 令牌有效，但是 viewer 档；`/ws` 要 operator |
| 连上了但永远等不到 `final` | 音频不是 16 kHz 单声道 16 位 PCM，或者 App 发的是编码格式（带 WAV 头、Opus、AAC）——本端点收的是原始采样 |
| 静音约 20 s 后连接断开 | 读超时；客户端要持续发帧或重连 |
| 帧因过大被拒 | 单条消息上限 2 MiB——发小一点，链路按 4 KB 左右调过 |
| `speaker.identified` 恒为 false | 声纹容器没跑时属预期 |

---

## 步骤 3: 打开管理后台 {#admin_web type=web_dashboard required=false config=devices/admin_web.yaml}

打开 `http://<栈主机>:3000/`——录音、关键词、设备、导出与删除都在这里。

### 前置条件

1. 第一个账号用 admin API 令牌创建：
   `curl -X POST -H "X-API-Token: <admin 令牌>" -H "Content-Type: application/json" -d '{"username":"ops","password":"<口令>"}' http://<栈主机>:8081/api/v1/users/register`。
2. 这个账号建出来是 **viewer**——能读，不能删除或导出。用改角色接口把它提到
   admin（调用本身也要 admin 凭据）：
   `curl -X PATCH -H "X-API-Token: <admin 令牌>" -H "Content-Type: application/json" -d '{"role":"admin"}' http://<栈主机>:8081/api/v1/users/<id>/role`。
   `<id>` 用同一个 admin 令牌调 `GET /api/v1/users?username=ops` 查，然后重新
   登录拿带新角色的令牌。服务本身不允许把最后一个 admin 降级（返回
   409），所以这条路径不会把账号锁在角色接口外面。
3. 后台展示的全部是脱敏之后的内容。任何地方都看不到原文，因为它从来没被存过。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 登录返回服务端错误 | `jwt_key` 还是占位符——签不出登录令牌，服务选择报错而不是回一个空 token |
| 登录成功但删除、导出按钮 403 | 账号是 viewer；按上面的办法在 `users` 表里提权 |
| 后台能打开但列表为空 | 还没有任何上报，或者浏览器指向的主机与设备上报的不是同一台 |

---

## 步骤 4: 验收转写与删除 {#verify_cloud type=manual required=true verify=true config=devices/verify_cloud.yaml}

说一句话，确认落库的是脱敏后的内容，删掉它，再证明删干净了。

### 前置条件

1. 说一句带电话号码的话：「我叫张伟，手机号是 13812345678」。
2. 看最新一条——号码必须显示为 `[[PHONE]]`、姓名显示为 `[[NAME]]`，
   且 `pii_masked_count` 大于 0。
3. 用 admin 令牌调 `POST /api/v1/privacy/erase` 删掉它。返回里必须是
   `"status": "complete"`、`"residue_count": 0`，且没有 `failed_steps`。
   级联步骤失败时接口仍返回 HTTP 200——判断这次删除算不算数看的是 `status`。
   `status: partial` 表示有东西没删掉（MinIO 对象、声纹、或墓碑），
   此时 `residue_count` 会把它们一并计入，不会是 0。
4. 把 `assets/tools/delete_proof.sh` 拷进 `sensecraft-voice-service` 仓库再跑
   （脚本往上找到第一个 `go.mod` 作为仓库根，放 `tools/` 或 `assets/tools/` 都行；
   也可以显式指定 `REPO_ROOT=`）。
   它自己起 MySQL 与 MinIO（容器名前缀 `c4-proof-`，不碰既有编排），
   造数据、删一个主体、再核三处。通过条件是 `RESIDUE_COUNT=0` 且 `RESIDUE_DB_REPORTED=0`。
5. 这个脚本证明的是代码路径，不是你现场的数据。两项检查都要做。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 数据库里能看到原始手机号 | 脱敏被关了——检查 `config/voice-service.yaml` 里的 `privacy.redaction_enabled`，然后停下来重查已入库的全部内容 |
| 有个姓名没被遮蔽 | 金标准集上的 recall 是 0.95；低置信实体是标记而不是遮蔽。先看 `pii_review_count` 再判定是 bug |
| 残留数不为 0 | 数据库之外有东西没删掉——MinIO 对象或声纹。读 `failed_steps` 与 `errors`，按删除失败处理 |
| `status` 是 `partial` | 至少有一个级联步骤失败。`voiceprint_delete` 是声纹服务不可达，`object_delete` 是 MinIO，`tombstone_write` 是删了但没留下凭证。修掉原因后重跑 erase，该接口是幂等的 |
| 删除成功但声纹还在 | 声纹服务没跑（未开 `voiceprint` profile）时属预期——级联没有可调用的对象，此时响应会给出 `status: partial` 与非零残留，而不是一个干净的 0 |
| `voiceprint_delete` 报 `connection refused` | `config/voice-service.yaml` 的 `asr.base_url` 必须写 compose 服务名 `http://asr-voiceprint:8080`，不能写 `127.0.0.1`——voice-service 在自己的网络命名空间里，`127.0.0.1` 指的是它自己 |
| 一口气念出的手机号没被遮蔽 | ASR 把它转写成中文数字词（「幺三八幺二三四五六七八」）而不是阿拉伯数字。`cn_mobile_spoken` 规则覆盖 11 位手机号形态；这样念出的身份证号、座机号仍未覆盖——见方案描述里的「已知限制」 |
| `delete_proof.sh` 报 `go.mod file not found` | 脚本不在 `sensecraft-voice-service` 检出目录里。拷进去，或用 `REPO_ROOT=/path/to/sensecraft-voice-service` 运行 |
| `delete_proof.sh` 连不上 Go 模块代理 | 它默认传 `GOPROXY=https://goproxy.cn,direct`；网络有别的要求就覆盖 `GOPROXY` |

### 部署完成

栈已经在跑，并且有一个主体走完了上报、脱敏、删除、证明删干净的全过程。
文本上报与查询在 `http://<栈主机>:8081/api/v1/recordings`，
删除与导出在 `/api/v1/privacy/*`，后台在 3000 端口。

#### 快速验证

1. 栈主机上 `docker ps` 能看到 `c4-mysql`、`c4-minio`、`c4-ovs-asr`、
   `c4-voice-service`、`c4-voice-web` 都在跑。
2. `curl -sf http://<栈主机>:8081/healthz` 正常返回。
3. 不带令牌的请求返回 401；用 viewer 令牌调删除接口返回 403。
4. 最新一条录音里是占位符，不是原始个人信息。
5. 删除接口返回 `status: complete` 且残留数为 0（`partial` 加非零残留
   表示这次删除没有被证明）。

#### 后续步骤

1. 任何内容离开局域网之前，先在 ASR 端点前面加 TLS 终结。
2. 在真实硬件上跑边界测试——并发、连续时长、WER、落库时延目前都没测，
   所以现在不能用这套部署给出任何容量结论。
3. 构建并推送声纹镜像，然后用
   `docker compose --profile voiceprint up -d asr-voiceprint` 起它，
   再在有声纹的情况下重跑一次删除检查。
4. 和现场隐私告知的负责人一起定保留期；24 小时是默认值，不是建议值。

---

## 套餐: 服务端栈 + 边缘采集端 {#edge_capture}

不涉及 App。边缘盒子上的麦克风阵列采音、经 OpenVoiceStream 本地转写，
再上报进同一套栈，而这套栈就跑在同一个盒子上。

| 设备 | 用途 |
|--------|---------|
| reComputer RK3576 或 reRouter CM4 | 采集、本地转写，以及整套服务端栈 |
| reSpeaker XVF3800 | 4 麦克风阵列——降噪、回声消除、波束成形 |

**重要：** 这不是合规认证。只有文本做了脱敏；音频在保留期内保持未脱敏状态，
并被删除流程覆盖。说话人识别是关的，因为声纹镜像仍待构建验证。
RK3576 上 ASR 跑在 NPU；reRouter CM4 上跑在 CPU，本包没有为这条路径固定镜像，
需要你自己提供一个，而且这条路径没有在真实硬件上跑过。

## 步骤 1: 部署采集端 {#collector_rk3576 type=docker_deploy required=true config=devices/collector_rk3576.yaml}

与另一个套餐相同的冻结栈，外加绑定到本机麦克风阵列的采集客户端。

### 接线

1. 部署之前先把 reSpeaker XVF3800 插到边缘盒子的 USB 口上。
2. 执行 `cat /proc/asound/cards` 记下声卡编号——它要填进 ALSA 声卡编号字段。
   通常是 1，接了别的音频设备就会变。
3. 把阵列放在对话发生的位置：收银台或服务台，距离约 1 米。
   波束成形解决的是方向问题，不是距离问题。
4. 不要放在会传导盒子风扇振动的台面上。
5. 不要再接第二个麦克风。链路是单路采集的，多一块声卡只会让声卡编号变得不确定。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| voice-client 反复重启 | ALSA 声卡编号不对；在设备上 `cat /proc/asound/cards`，用正确的编号重新部署 |
| 容器在跑但没有转写 | `docker logs c4-voice-client`——看它是否连上了 8621 的 ASR 后端，以及令牌是不是 operator 那条 |
| `/data-iot/respeaker` 权限不足 | 部署会建这些目录；如果它们此前已存在且属主是 root，执行 `chmod -R 0775 /data-iot/respeaker` |
| 部署报 `set OVS_ASR_IMAGE ...` | 只会出现在 CM4 目标上：本包没有固定 CPU 版 ASR 镜像，需要你提供引用 |
| CM4 上全都在跑但转写是空的 | CM4 这条路径本包未验证，compose 里的内存上限是按 RK3576 的内存写的——4 GB 的 CM4 要调低 |

### 部署目标: {#collector_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/collector_rk3576.yaml default=true}

NPU 路径。ASR 后端是 RK3576 构建，不需要额外输入。

### 部署目标: {#collector_rerouter_remote type=remote device=rerouter device_name="reRouter CM4" config=devices/collector_rerouter.yaml}

CPU 路径。用的是 ASR 镜像必填的那份 compose 变体，因为本包没有为 CM4 固定镜像。
未在真实硬件上验证。

---

## 步骤 2: 打开管理后台 {#admin_web_edge type=web_dashboard required=false config=devices/admin_web_edge.yaml}

打开 `http://<采集端>:3000/`——同一个后台，跑在采集端上。

### 前置条件

1. 用 admin API 令牌创建第一个账号，做法与另一个套餐完全一样：
   `curl -X POST -H "X-API-Token: <admin 令牌>" -H "Content-Type: application/json" -d '{"username":"ops","password":"<口令>"}' http://<采集端>:8081/api/v1/users/register`。
2. 需要它能删除或导出就用改角色接口提权（要 admin 令牌）：
   `curl -X PATCH -H "X-API-Token: <admin 令牌>" -H "Content-Type: application/json" -d '{"role":"admin"}' http://<采集端>:8081/api/v1/users/<id>/role`。
   新账号默认是 viewer。
3. 「录音」页显示的是脱敏后的文本。采集端注册的设备会出现在「设备」里，按 MAC 标识。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 后台里没有任何设备 | 采集端还没上报过——说一句话再刷新 |
| 登录返回服务端错误 | `config/voice-service.yaml` 里的 `jwt_key` 还是占位符 |
| 后台能访问但 API 不通 | voice-web 在 3000、voice-service 在 8081，采集端上两个端口都要放开 |

---

## 步骤 3: 验收转写与删除 {#verify_edge type=manual required=true verify=true config=devices/verify_edge.yaml}

同一套验收，输入换成麦克风阵列而不是 App。

### 前置条件

1. 对着阵列说一句带电话号码的话，然后停下——语音段是靠静音结束的。
2. 看最新一条是不是显示 `[[PHONE]]` 与 `[[NAME]]`，且 `pii_masked_count` 大于 0。
3. 用 admin 令牌删掉这个会话，确认返回是 `status: complete` 且残留数为 0。
4. 在 `sensecraft-voice-service` 仓库根目录跑 `assets/tools/delete_proof.sh`，
   读 `RESIDUE_COUNT=0`。
5. 确认本地音频目录 `/data-iot/respeaker/recordings` 里已经没有被删会话的文件——
   这是三处存储里的第三处。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 完全没有转写 | 先查 ALSA 声卡编号，再看 `docker logs c4-ovs-asr` 的模型加载 |
| 有转写但被截断 | 服务端 VAD 按静音切段，单段最长 10 s |
| 行已脱敏但删除后音频文件还在盘上 | 读删除返回里的 `errors` 字段——对象删除失败就是删除失败，不是部分成功 |
| 24 小时后音频仍然在 | 保留期由服务配置执行；确认 `config/voice-service.yaml` 里的 `raw_audio_retention_hours` 与你选的一致 |

### 部署完成

采集端完成采音、本地转写、入库前脱敏，并在同一个盒子上提供后台与删除接口。
只要没人打开 cloud-analytics profile，就没有内容离开这台设备。

#### 快速验证

1. `docker ps` 能看到 `c4-ovs-asr`、`c4-voice-client`、`c4-voice-service`、
   `c4-voice-web`、`c4-mysql`、`c4-minio`。
2. `curl -sf http://<采集端>:8621/health` 正常返回。
3. 在阵列附近说话，几秒内出现一条新记录。
4. 这条记录里是占位符，不是原始个人信息。
5. 删除返回 `status: complete` 且残留数为 0，盘上的音频文件已消失。

#### 后续步骤

1. 先测再承诺：这套硬件上的并发、连续时长、WER、落库时延都还没测。
2. 现场隐私告知有要求就调短音频保留期——部署时可选 6 小时或 1 小时。
3. CM4 上先把 CPU 版 ASR 路径端到端验一遍，并调低 ASR 容器的内存上限，
   再把那个目标当作可用。
4. admin 令牌不要留在设备上；它是给跑删除与导出的运维用的。
