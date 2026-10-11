# ef82 container runtime review

Review time: 2026-10-11 12:35–12:37 Asia/Shanghai  
URL: `http://100.77.150.16:18775/`  
Container endpoint: direct browser session; no Playwright route replacement and no server/source mutation.

## Actual assets

- `index.html` SHA-256: `75f2779f55ba3b2af3030e3739986b8217af7e69c7bc691e2a4f99795e4676ff`
- `app.js?v=20261011-qa3` SHA-256: `02c44a4da2b0a9e298aec9ef9154a5c5488e29875aff729fd0f26348dda0ed9e`
- Browser used the direct 18775 asset and real APIs.

## Confirmed runtime behavior

- Kev Chinese completed decision: HTTP 200 `/api/decide`, actual model `kev`, backend `rkllm`, max context `8192`; result selected `降低输送带速度`.
- Switching only the UI to EN preserved the completed result and history text exactly (`historyUnchanged: true`).
- Laya real decision: HTTP 200 `/api/decide`, actual model `laya`, backend `rknn`, max context `90`; result selected `Reduce conveyor speed`.
- Ctrl+Enter pending guard: badge was `Running · 0s`, button disabled after the first keypress, second keypress remained disabled, request count was `1`.
- Recording entry was disabled because no voice service was configured. Real ASR was not validated.

## Evidence

- [Kev ZH completed PNG](./03-kev-zh-completed.png)
- [Kev EN completed PNG](./04-kev-en-completed.png)
- [Non-realtime ZH→EN GIF](./kev-zh-en-container-review.gif)
- [Initial snapshot](./01-initial.yaml)
- [Ready snapshot](./02-ready.yaml)
- [Kev ZH completed snapshot](./03-kev-zh-completed.yaml)
- [Kev response and history](./03-kev-zh-runtime.txt)
- [Kev EN completed snapshot](./04-kev-en-completed.yaml)
- [Kev EN history check](./04-kev-en-runtime.txt)
- [Laya snapshot](./09-laya-en-completed.yaml)
- [Laya response and result](./07-laya-en-runtime.txt)
- [Ctrl+Enter pending guard](./08-ctrl-enter-pending-guard.txt)
- [Laya request payload](./09-laya-request-payload.txt)
- [Network log](./network.log)
- [Console log](./console.log)

The GIF is a two-frame screenshot montage and does not represent realtime latency or recording. The Console contains one favicon 404 from the direct container.

SHA-256:

```text
03-kev-zh-completed.png  f675a07a7a3fc629229728579cd66e3211e2c8788709ded9be77446dd6b9067d
04-kev-en-completed.png  c2e3120949777aaa8bf024b41bcf42c090920d33a610eb71dd1035df1ad6534e
kev-zh-en-container-review.gif  6591ac8f4224873f6a980e78c47211710101b0baf3503eeb623e57e634905108
```
