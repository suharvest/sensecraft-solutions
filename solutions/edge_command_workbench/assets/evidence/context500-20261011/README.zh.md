# Kev 500-token 上下文基准

本基准测量 Kev RKLLM 命令选择路径在固定 500 个 assembled tokens 上下文中的行为。每条冻结语义请求后追加固定的、中性的合成工业文档元信息句子。追加内容不描述动作、设备状态、传感器状态或运行条件；原始 input、prompt 语义、候选项、期望标签、语言和类别保持不变。该追加只用于控制长度，不代表自然长任务的准确率结论。500-token 统计覆盖完整 Kev assembly：官方 delimiter、input、prompt/context 以及全部候选项。服务返回的是 selected option ID；本基准不是文本生成，也不报告 tokens/second。

数据集包含 120 条语言样本，组织为 60 组中英文配对语义 case，覆盖 direct、paraphrase、negation、ambiguous、out-of-scope。每条语言样本按原候选顺序和反转候选顺序各发送一次，每台设备共 240 条计分请求。计分前发送 5 条 warmup，warmup 不计入 240 的分母；warmup 失败时立即停止本轮。 冻结数据的候选数实际为：4 项 22 条 case、5 项 20 条、6 项 52 条、7 项 26 条，范围为 4–7；运行时上限 16 项不是本数据集的候选数。baseline assembled context 为 71–110 tokens。`clarify` 和 `reject` 各有 20 个语义 case，经过两种顺序后各为 40 条请求分母。

## 可复现输入

- [`context500-cases.jsonl`](context500-cases.jsonl) 保存请求体、期望标签、两种顺序、精确 token 数和逐请求 SHA256。期望字段只存在于元数据，不会发送到 HTTP body。
- [`context500-metadata.json`](context500-metadata.json) 保存冻结源数据 SHA、部署 tokenizer SHA、Kev codec 源 SHA、delimiter ID、目标长度以及 generator/runner SHA。
- [`tokenizer.fe000.json`](tokenizer.fe000.json) 是从 Radxa 发布部署复制并校验的 tokenizer，SHA256 为 `fe000e3ed39ed12b8d2481d527d44f93c65d37e87645d2dcc80d1bf9d50d2927`。
- [`generate_context500.py`](generate_context500.py) 对每条生成请求调用应用内 `KevCodec.encode`，并与独立 token 计数交叉校验；不一致时拒绝生成。
- [`run_context500.py`](run_context500.py) 通过 loopback 顺序发送 HTTP 请求，恢复已有结果前校验 dataset/request SHA，不自动重试，每条计分请求写一条原始 JSONL 并生成 summary。

每台设备的结果必须记录实际 image、model、tokenizer、runtime 和 Hugging Face revision。发布 pin 与 artifact 证据位于对应 release evidence 目录；本基准不下载或替换部署 artifact。

## 已完成的设备结果

两台设备的 stable-v2 均以 exit code 0 完成。每台设备发送 240 条计分请求：60 组中英文配对语义 case 共 120 条语言样本，每条按原候选顺序和反转候选顺序各发送一次。准确率是 `selected_option_id` exact match，不是 HTTP 成功率或安全性认证。误动作表示期望为 `clarify` 或 `reject` 时误选执行类候选；本基准只发送决策请求，不执行工业命令。

| 设备 | model identity | HTTP | 正确 | 准确率 | 原顺序 | 反转顺序 | 英文 | 中文 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RK3576 | `kev`、`rkllm`、W4A16 g128、max 2048 | 240/240 | 189/240 | 78.75% | 95/120 | 94/120 | 93/120 | 96/120 |
| RK3588 | `kev`、`rkllm`、W8A8、max 8192 | 240/240 | 189/240 | 78.75% | 92/120 | 97/120 | 94/120 | 95/120 |

类别准确率：RK3576 direct 80/80、paraphrase 39/40、negation 37/40、ambiguous 14/40、范围外 19/40；RK3588 direct 80/80、paraphrase 38/40、negation 38/40、ambiguous 12/40、范围外 21/40。误动作比例：RK3576 `clarify` 为 16/40（40.00%）、`reject` 为 3/40（7.50%）；RK3588 `clarify` 为 22/40（55.00%）、`reject` 为 2/40（5.00%）。两台设备的无效 selected ID 均为 0。候选顺序反转后，RK3576 有 5/120 对 selected ID 改变、3 对正确性改变；RK3588 有 9/120 对 selected ID 改变、5 对正确性改变。

| 设备 | 计时 | n | mean ms | min ms | p50 ms | p95 ms | max ms |
|---|---|---:|---:|---:|---:|---:|---:|
| RK3576 | client 端到端 | 240 | 7220.982 | 7067.254 | 7115.307 | 7574.560 | 7773.237 |
| RK3576 | server inference | 240 | 7217.131 | 7063.492 | 7111.639 | 7570.440 | 7769.592 |
| RK3576 | server total | 240 | 7217.305 | 7063.657 | 7111.868 | 7570.654 | 7769.754 |
| RK3588 | client 端到端 | 240 | 3958.615 | 3479.071 | 3946.517 | 4770.961 | 5371.268 |
| RK3588 | server inference | 240 | 3955.264 | 3475.535 | 3943.280 | 4767.696 | 5368.083 |
| RK3588 | server total | 240 | 3955.432 | 3475.699 | 3943.448 | 4767.862 | 5368.251 |

p50 使用 median；p95 使用 nearest-rank 索引 `ceil(0.95*n)`。480 条计分响应全部有完整 timing 对象且无 HTTP 错误。当前 Kev native instrumentation 将 `encoding_ms` 写为 `0.0`；它不是 tokenizer wall time 的实测值，也不表示编码真实耗时为零。KevCodec 编码、RKLLM hidden-state 推理和 FP32 head 打分都位于 inference 计时路径内。两板使用不同芯片、量化和部署 context guard，本结果不单独归因量化差异。

响应中观察到的 runtime/model identity 为 `model_id=kev`、`backend=rkllm`、`model_ready=true`；两个 engine 都按 8K context 导出，部署 cap 分别为 RK3576 `max_sequence_tokens=2048`、RK3588 `8192`，两者 `max_options=16`。量化方式为 RK3576 Kev W4A16 g128、RK3588 Kev W8A8。两轮复用已有 release evidence 中的 image `edge-command-workbench:rockchip-rkllm-0.3.1-review` 和 Hugging Face revision `db0545065d4da3598d009407fc3bd0c7632ca199`（[RK3576 release evidence](../../../docs/interaction-review-ef82-20261011/rk3576-final-release/)、[RK3588 release evidence](../../../docs/interaction-review-ef82-20261011/rk3588-final-release/)）；本报告不宣称重新进行了第二次 artifact SHA 验证。benchmark tokenizer 和 Kev codec SHA 仍记录在 [`context500-metadata.json`](context500-metadata.json)。

按设备链接证据：[RK3576 raw results](rk3576/stable-v2/results-v2.jsonl)、[RK3576 summary](rk3576/stable-v2/results-v2.summary.json)、[RK3576 analysis](rk3576/stable-v2/analysis.json)、[RK3576 exit](rk3576/stable-v2/results-v2.exit)、[RK3588 raw results](rk3588/stable-v2/results-v2.jsonl)、[RK3588 summary](rk3588/stable-v2/results-v2.summary.json)、[RK3588 analysis](rk3588/stable-v2/analysis.json)、[RK3588 exit](rk3588/stable-v2/results-v2.exit)。SHA256：RK3576 results `7ed7869b43e562ae31ebc9d2c0a4fa72cf1a73a65066f93bd0525cc12e049f7f`，summary `2f687c7366d5ae09078ab9899757b9e3dc92a11e5b180a816348b70041647463`，analysis `aa1a66773f969f70eea9fa91c11bee9243163aac743a3d715af92eda0f44f544`；RK3588 results `5b49681b5e093202d9b184ac2fb94e471bde503669ba07c1f9573f665a73e782`，summary `fa0a3dbaed58a2c94f818bc4ee67a4007b6f47b956bd1dfe3829f986ada6cf5f`，analysis `86d64fce7b14988c77d7a78582456002a0dec20b3e91688d4ec61f47890e1e4a`。两份 dataset 均匹配 `e9d77a3c96a1d0645bc9561cdf9ead06cbd57d8ef081906c2d5094d55e54ba6e`。

runner 复现只需要标准库、冻结 dataset 和 metadata，不需要 `app/` 或 tokenizer fixture：`uv run --no-project python experiments/jev-20261011/context500/run_context500.py --dataset experiments/jev-20261011/context500/context500-cases.jsonl --out /tmp/context500-results.jsonl --timeout 120 --warmup 5 --base-url http://127.0.0.1:18771/api/decide`。该 loopback 示例在 cat 设备上执行；Radxa 使用端口 `18768`。如果从 Spark 或 Mac 使用设备 IP，client 时间会包含 LAN，不应直接与表中的 loopback 数字比较。重新生成 dataset 才需要完整源仓库、应用包和 tokenizer fixture；小型交付副本只包含结果证据。

## 测量范围

client elapsed 是 loopback HTTP 请求外层的计时；服务端 `encoding_ms`、`inference_ms`、`total_ms` 单独统计。summary 对 client 端到端时间及每个可用的服务端时间字段分别报告 n、mean、minimum、p50、p95、maximum。HTTP 错误、超时和缺少任一服务端时间字段的响应单独列出；缺失时间不会按零计入。

准确率使用同一批 240 条计分请求，分别报告总体、语言、类别和候选顺序。summary 包含完整错误清单，以及 HTTP 200 但选中项不同于期望标签的 `wrong_predictions`。5 条 warmup 不进入准确率或性能分母。服务端每次请求清理 KV cache，不共享请求历史；runner 串行发送请求。

逐请求原始 JSONL、程序 summary、analysis、exit code 与 artifact/hash 证据已分别保存在 `rk3576/` 与 `rk3588/`。上文记录的是已测结果；小型交付副本包含结果证据，不重复复制 12.8 MB tokenizer fixture。
