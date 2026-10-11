# Gallery

Existing gallery chapters:

- [Workbench demo](./demo/README.md)
- [Kev final QA](./kev-final/README.md)
- [Kev / Laya switch evidence](./kev-final-switch/README.md)

## ef82 interaction review · 2026-10-11

独立审查素材位于 [`interaction-review-ef82-20261011/`](./interaction-review-ef82-20261011/)。审查浏览器只在本地 review 会话中将 `/app.js` 路由替换为候选 ef82 文件，真实 `/api/models`、`/api/decide`、`/api/health/remote` 仍请求 `http://100.77.150.16:18772`；候选版本截至审查时**尚未部署**，当前服务仍为 d870。

The review browser routed `/app.js` to the ef82 candidate only inside the isolated review session. Real model, decision, and health APIs remained on `http://100.77.150.16:18772`. The candidate was **not deployed**; the running service remained d870.

The completed-result screenshots and the two-frame language GIF show captured UI states; the GIF is a non-realtime montage. Voice was optional in the review and real ASR was not validated.

- [中文审查记录](./interaction-review-ef82-20261011/REVIEW.md)
- [English review record](./interaction-review-ef82-20261011/REVIEW_EN.md)
- [Completed ZH result](./interaction-review-ef82-20261011/ef82-completed-zh.png)
- [Completed EN result](./interaction-review-ef82-20261011/ef82-completed-en.png)
- [Completed ZH → EN montage](./interaction-review-ef82-20261011/ef82-completed-zh-en.gif)
