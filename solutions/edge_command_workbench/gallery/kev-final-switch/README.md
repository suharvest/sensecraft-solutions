# Kev / Laya real-device switch evidence

These assets were captured on the Radxa staging shadow at `http://192.0.2.16:18772/` using the same English request and candidate options. The final browser-tested source served `app.js` SHA256 `52abe5f783b2b6eed767bf63d69fe7ddc638271ae97a011233f8584a69757206`.

| Profile | Screenshot SHA256 | Visible chip and result identity |
|---|---|---|
| Laya | `f3fff601ed0fce8e1a00aabe6afb95021cd77055210e6aada5e6391efaf3bbea` | `model.rknn · 90 tokens`; `laya / rknn / 90` |
| Kev | `7b9a6da80ee26e0eba68c997e498d4100eccf5b0bc5a98ea9feeab488d30b0d5` | `model.rkllm · 8192 tokens`; `kev / rkllm / 8192` |

The two-frame GIF SHA256 is `3599505f116bfc3268e7bb6a9db1d8ad9331c4bc130dac7335f48d79ce9e12fb`. The browser console had no errors or warnings. The `Test and connect` path made a real `GET /api/models` request and received HTTP 200. The evidence JSON records raw request IDs, scores, backend, model ID, context, and timing; its API response-body provenance boundary is explicit.

The displayed score and timing use the final UI's readability rounding (score to three decimals, milliseconds to one decimal). The raw API values remain in the evidence JSON and API responses. These screenshots supersede no existing `gallery/demo` Laya materials; they are an additional switch evidence set. Voice remains optional and was not tested.
