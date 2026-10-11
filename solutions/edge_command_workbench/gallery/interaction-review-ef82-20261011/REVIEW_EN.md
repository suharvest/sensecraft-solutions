# ef82 Independent Runtime Review

Review time: 2026-10-11 12:20–12:25 (Asia/Shanghai)
Runtime URL: <http://100.77.150.16:18772/>
Deployment status: still d870; no container update or UI publication was performed.

## Version and route limitation

- Source file: `/tmp/edge-workbench-web-ef82f83/app.js`
- SHA-256: `02c44a4da2b0a9e298aec9ef9154a5c5488e29875aff729fd0f26348dda0ed9e`
- Only the isolated review browser routed `/app.js` to this file.
- Real `/api/models`, `/api/decide`, and `/api/health/remote` calls remained on port 18772.
- This report verifies the route-replaced browser behavior. It does not prove that the d870 container contains ef82.

## Candidate build association

- Local candidate source commit: `ef82f8360c2b787f97c958f89c92fe569c62ecb1`.
- Candidate image: `edge-command-workbench:rockchip-rkllm-0.3.1-review`; image/config blob SHA-256: `d7a81c4f8ef3eaa2c21560b2d37939c6088357ec0c1d41c3089ff5fbc3836de9`.
- Candidate archive SHA-256: `251cb7fef080f489bf311b37c5bddbba1cd72e887e71f10ce12fc25a1fe64f77`.
- The real API review calls in this report still used the d870 deployment on port 18772; the candidate was not deployed.

## Confirmed

- ZH/EN result labels switch correctly. Existing results remain visible and language switching does not add a history entry. Evidence: [ef82-zh-result.yaml](./ef82-zh-result.yaml), [ef82-en-result.yaml](./ef82-en-result.yaml).
- Both real models completed decisions: `model.rknn → laya` (90 tokens) and `model.rkllm → kev` (8192 tokens). Evidence: [ef82-zh-result.yaml](./ef82-zh-result.yaml), [ef82-rkllm-result-en.yaml](./ef82-rkllm-result-en.yaml).
- Test and connect shows failure for an unreachable address; clearing it and retrying restores the connected state. Evidence: [ef82-connect-fail.yaml](./ef82-connect-fail.yaml), [ef82-connect-recovered.yaml](./ef82-connect-recovered.yaml).
- Mouse double-click protection was re-tested: the first click disables the button, the second is rejected, and request count is 1. The previous mouse duplicate-click finding is withdrawn. Evidence: [ef82-mouse-click-repro.txt](./ef82-mouse-click-repro.txt).
- Two consecutive Ctrl+Enter submissions produce only one `/api/decide` request. Evidence: [ef82-ctrl-enter-repro.txt](./ef82-ctrl-enter-repro.txt).
- During rapid model switching, stale health requests are aborted and final metadata matches the last selection. Evidence: [ef82-modelhealth-race-network.log](./ef82-modelhealth-race-network.log), [ef82-modelhealth-race.txt](./ef82-modelhealth-race.txt).

## Coverage boundary

- No real voice service was configured. The recording entry remained disabled. This review did not treat a synthetic WebSocket final message as real ASR evidence; real ASR requires a connected service.
- The 502 Console entry after connection recovery was produced by the intentionally unreachable test address and is diagnostic evidence, not a release-state claim.

## Evidence artifacts

- Full-page completed-result screenshots (Kev / rkllm / 8192): [ef82-completed-zh.png](./ef82-completed-zh.png), [ef82-completed-en.png](./ef82-completed-en.png)
- Two-frame completed-result language-switch GIF, non-realtime: [ef82-completed-zh-en.gif](./ef82-completed-zh-en.gif)
- Completed response, result text, and history counts: [ef82-completed-zh-runtime.txt](./ef82-completed-zh-runtime.txt), [ef82-completed-en-runtime.txt](./ef82-completed-en-runtime.txt)
- Raw request payload: [ef82-request-payload.txt](./ef82-request-payload.txt)
- Console: [ef82-console-latest.log](./ef82-console-latest.log)

SHA-256:

```text
ef82-completed-zh.png  fc330da7cbb79a1e219a1199551aa2a3f531e2552210c5c26a382e52a082f16b
ef82-completed-en.png  9ae42e4d7b0ba2390426f47639482426474531003ac5d272d97cd8d8efdee958
ef82-completed-zh-en.gif  324c79531ad390f01888756aee950ce830fdda186629cda424da516c124e5696
```
