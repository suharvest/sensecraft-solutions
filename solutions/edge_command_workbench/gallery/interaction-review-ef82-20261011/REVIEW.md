# ef82 独立实际审查

审查时间：2026-10-11 12:20–12:25（Asia/Shanghai）
实际地址：<http://100.77.150.16:18772/>
部署状态：仍为 d870；本轮没有更新容器或发布 UI。

## 复测版本与限制

- 源文件：`/tmp/edge-workbench-web-ef82f83/app.js`
- SHA-256：`02c44a4da2b0a9e298aec9ef9154a5c5488e29875aff729fd0f26348dda0ed9e`
- 仅在独立浏览器 review 会话中将 `/app.js` 路由替换为上述文件。
- `/api/models`、`/api/decide`、`/api/health/remote` 等真实 API 仍请求 18772。
- 因此本报告证明的是 route 替换后的浏览器行为，不证明 d870 容器已包含 ef82。

## 候选构建关联

- 本地 candidate source commit：`ef82f8360c2b787f97c958f89c92fe569c62ecb1`。
- candidate image：`edge-command-workbench:rockchip-rkllm-0.3.1-review`，image/config blob SHA-256：`d7a81c4f8ef3eaa2c21560b2d37939c6088357ec0c1d41c3089ff5fbc3836de9`。
- candidate archive SHA-256：`251cb7fef080f489bf311b37c5bddbba1cd72e887e71f10ce12fc25a1fe64f77`。
- 本报告的真实 API 复测仍连接 18772 的 d870 部署；candidate 未部署。

## 已确认

- ZH/EN 结果标签随语言切换正确更新；已有结果保留，切换语言没有新增历史记录。证据：[ef82-zh-result.yaml](./ef82-zh-result.yaml)、[ef82-en-result.yaml](./ef82-en-result.yaml)。
- 两个真实模型均完成判断：`model.rknn → laya`（90 tokens），`model.rkllm → kev`（8192 tokens）。证据：[ef82-zh-result.yaml](./ef82-zh-result.yaml)、[ef82-rkllm-result-en.yaml](./ef82-rkllm-result-en.yaml)。
- Test and connect 失败后显示错误；清空地址后重新测试恢复连接。证据：[ef82-connect-fail.yaml](./ef82-connect-fail.yaml)、[ef82-connect-recovered.yaml](./ef82-connect-recovered.yaml)。
- 鼠标重复点击已复测为受保护：第一次后按钮 disabled，第二次被拒绝，request 数为 1。旧的“鼠标重复点击会重复请求” finding 撤回。证据：[ef82-mouse-click-repro.txt](./ef82-mouse-click-repro.txt)。
- Ctrl+Enter 连续两次只产生 1 个 `/api/decide` 请求。证据：[ef82-ctrl-enter-repro.txt](./ef82-ctrl-enter-repro.txt)。
- 快速切换模型时旧 health 请求被 abort，最终 metadata 对齐最后选择。证据：[ef82-modelhealth-race-network.log](./ef82-modelhealth-race-network.log)、[ef82-modelhealth-race.txt](./ef82-modelhealth-race.txt)。

## 边界

- 未配置真实语音服务；录音入口保持 disabled。本轮没有把合成 WebSocket final 消息当作真实 ASR 证据，真实 ASR 仍需连接实际服务后验证。
- `/api/health/remote` 失败恢复会在 Console 留下 502 记录，这是本轮故意输入不可达地址产生的诊断证据，不是发布状态。

## 证据产物

- 完成结果全页截图（Kev / rkllm / 8192）：[ef82-completed-zh.png](./ef82-completed-zh.png)、[ef82-completed-en.png](./ef82-completed-en.png)
- 两帧完成结果语言切换 GIF（非实时演示）：[ef82-completed-zh-en.gif](./ef82-completed-zh-en.gif)
- 完成结果响应、文本和 history 计数：[ef82-completed-zh-runtime.txt](./ef82-completed-zh-runtime.txt)、[ef82-completed-en-runtime.txt](./ef82-completed-en-runtime.txt)
- 请求 payload：[ef82-request-payload.txt](./ef82-request-payload.txt)
- Console：[ef82-console-latest.log](./ef82-console-latest.log)

SHA-256：

```text
ef82-completed-zh.png  fc330da7cbb79a1e219a1199551aa2a3f531e2552210c5c26a382e52a082f16b
ef82-completed-en.png  9ae42e4d7b0ba2390426f47639482426474531003ac5d272d97cd8d8efdee958
ef82-completed-zh-en.gif  324c79531ad390f01888756aee950ce830fdda186629cda424da516c124e5696
```
