# Kev final QA evidence

这些素材来自 2026-10-11 的 Radxa RK3588 shadow QA 服务，服务端口为 `18769`；它们用于记录候选版本的真实页面与 API 验证，不覆盖既有 `gallery/demo/` 的 RK3576/Laya 素材。

| File | SHA256 | Meaning |
|---|---|---|
| `kev-final-zh-result-20261011.png` | `1a78b98d392bf2b1c175f0fcf3fc75b44e8021f3cc95457be7cc1055af141e89` | Chinese Kev result page |
| `kev-final-en-result-20261011.png` | `f574485d31c02750904aab42807f38a382337921d3505e22dcaf4efa740911cb` | English Kev result page |
| `kev-final-en-pending-20261011.png` | `abe18a89512700cf46c742d6a495643f70a59661badbde6b360c052082654741` | English pending state |
| [`kev-final-qa-20261011.gif`](https://files.seeedstudio.com/Solution/landpage_asset/edge-command-workbench/kev-final-qa-20261011-800c70a6.gif) | `308b3d77b5030b83b95d4277d9b7183c5b30fb69c004f8c4409b8809b1803748` | Screenshot montage of the QA flow (hosted on Seeed CDN) |
| `kev-final-evidence-20261011.json` | `e6d496da79d2d4119849b202e9b9faa6a19392e9ad86137a0dde570b4122cda6` | URLs, health response, request metadata |

The montage is assembled from screenshots and does not represent model duration, a live recording, or an accuracy measurement. The captured page served `app.js` SHA256 `7a72b7e63dc1bf1bde94fa7ecb4b60230da99308e6f21e83cdadda0032cfa923` and `index.html` SHA256 `75f2779f55ba3b2af3030e3739986b8217af7e69c7bc691e2a4f99795e4676ff`; the later final candidate image uses the separately recorded current UI hashes in the artifact inventory.

Voice was configured as optional only and was not tested in this evidence set.
