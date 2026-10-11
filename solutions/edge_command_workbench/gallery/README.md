# Gallery

Existing gallery chapters:

- [Workbench demo](./demo/README.md)
- [Kev final QA](./kev-final/README.md)
- [Kev / Laya switch evidence](./kev-final-switch/README.md)

## ef82 interaction review · 2026-10-11

独立审查素材位于 [`interaction-review-ef82-20261011/`](./interaction-review-ef82-20261011/)。审查浏览器只在本地 review 会话中将 `/app.js` 路由替换为候选 ef82 文件，真实 `/api/models`、`/api/decide`、`/api/health/remote` 仍请求 `http://192.0.2.16:18772`；候选版本截至审查时**尚未部署**，当前服务仍为 d870。

The review browser routed `/app.js` to the ef82 candidate only inside the isolated review session. Real model, decision, and health APIs remained on `http://192.0.2.16:18772`. The candidate was **not deployed**; the running service remained d870.

The completed-result screenshots and the two-frame language GIF show captured UI states; the GIF is a non-realtime montage. Voice was optional in the review and real ASR was not validated.

- [中文审查记录](./interaction-review-ef82-20261011/REVIEW.md)
- [English review record](./interaction-review-ef82-20261011/REVIEW_EN.md)
- [Completed ZH result](./interaction-review-ef82-20261011/ef82-completed-zh.png)
- [Completed EN result](./interaction-review-ef82-20261011/ef82-completed-en.png)
- [Completed ZH → EN montage](./interaction-review-ef82-20261011/ef82-completed-zh-en.gif)

## Direct browser ef82 QA review · 2026-10-11

本节是实际 QA 容器 `http://192.0.2.16:18775/` 的新浏览器复测，未使用 route 替换；实际 `app.js` SHA-256 为 `02c44a4da2b0a9e298aec9ef9154a5c5488e29875aff729fd0f26348dda0ed9e`。候选只在当前 QA 容器复测，尚未 HF 发布；真实 ASR 未配置/未验证。GIF 是两张完成状态截图的非实时拼接。

This section records a fresh direct-browser re-test against the QA container at `http://192.0.2.16:18775/`, with no route replacement. The actual `app.js` SHA-256 is `02c44a4da2b0a9e298aec9ef9154a5c5488e29875aff729fd0f26348dda0ed9e`. The candidate was tested only in this QA container and was not published to HF; real ASR was not configured or validated. The GIF is a non-realtime montage of two completed screenshots.

- [Direct browser evidence](./interaction-review-ef82-20261011/direct-browser/REVIEW.md)
- [Direct Kev ZH completed result](./interaction-review-ef82-20261011/direct-browser/03-kev-zh-completed.png)
- [Direct Kev EN completed result](./interaction-review-ef82-20261011/direct-browser/04-kev-en-completed.png)
- [Direct ZH → EN non-realtime montage](./interaction-review-ef82-20261011/direct-browser/kev-zh-en-container-review.gif)

Public copies of the browser review records use RFC 5737 documentation addresses in place of private Fleet addresses. The raw private originals and their SHA-256 manifest are retained outside the repository for authorized review; the public copies are sanitized and are not byte-identical to those originals.

公开浏览器审查记录使用 RFC 5737 文档地址替代 Fleet 私有地址。原始私有文件及其 SHA-256 manifest 保存在仓库外供授权审查；公开副本已脱敏，因此与原始文件的字节内容不同。
