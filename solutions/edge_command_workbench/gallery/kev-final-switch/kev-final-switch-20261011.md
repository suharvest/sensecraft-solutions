# Kev / Laya 实机切换证据（2026-10-11）

最终 Radxa UI 地址：`http://192.0.2.16:18772/?lang=en&qa=dual-model-final2-20261011`。
served `app.js` SHA-256：`52abe5f783b2b6eed767bf63d69fe7ddc638271ae97a011233f8584a69757206`。

使用同一英文短指令 `Reduce conveyor 3 speed to 60%` 和同一 3 个候选项，通过 Decision model 下拉分别选择 Laya 与 Kev。两张截图都同时包含顶部状态 chip 和结果卡片：

| Profile | Screenshot | SHA-256 | Top chip | Result identity | Displayed result |
|---|---|---|---|---|---|
| Laya | `kev-final-switch-laya-20261011.png` | `f3fff601ed0fce8e1a00aabe6afb95021cd77055210e6aada5e6391efaf3bbea` | `model.rknn · 90 tokens` | `laya / rknn / 90` | score `17.328`, total `374.2 ms` |
| Kev | `kev-final-switch-kev-20261011.png` | `7b9a6da80ee26e0eba68c997e498d4100eccf5b0bc5a98ea9feeab488d30b0d5` | `model.rkllm · 8192 tokens` | `kev / rkllm / 8192` | score `0.924`, total `478.8 ms` |

`kev-final-switch-20261011.gif` 是上述两张完成态截图的两帧 montage，SHA-256：`3599505f116bfc3268e7bb6a9db1d8ad9331c4bc130dac7335f48d79ce9e12fb`。

最终页面控制台没有 error 或 warning。切换到 Kev 后点击 `Test and connect`，页面显示 `Model service connected`；同一操作路径在 staging shadow 已观察到真实 `GET /api/models` 请求并返回 HTTP 200。完整操作和 API 样本见 [`kev-final-switch-evidence-20261011.json`](kev-final-switch-evidence-20261011.json)。

API 样本保留 raw `request_id`、score、backend、model_id、context 和 timing。浏览器控制工具提供了完成态 DOM 与截图，但不提供该次浏览器请求的 response body；JSON 中的 API 样本使用相同 payload、候选项和 model_id 通过服务端点单独采集，并明确标注这一边界。
