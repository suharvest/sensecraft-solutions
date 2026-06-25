---
name: New capability request / 新能力需求
about: Request a brand-new verify/deploy interaction type when built-in types and fallbacks don't fit. 内置类型和兜底都不够、需要一个全新交互形态时用这个。
title: "[capability] "
labels: ["capability-request"]
---

> 提交前请先确认你确实需要一个**全新类型** —— 先读
> [`skills/author-solution/SKILL.md`](../../skills/author-solution/SKILL.md) 的「能力不够怎么拓展」决策树。
> 90% 的「没有合适类型」用 `http_debug` / `web_dashboard` / `actions` 兜底就能解决。
> Before filing, confirm you really need a *new* type — most "no fitting type" cases are
> solved by the generic fallbacks. See the decision tree in `skills/author-solution/SKILL.md`.

## 1. 你部署的是什么 / What gets deployed
<!-- 一句话描述部署产物：一个服务？一个设备？一个模型？暴露了什么接口？ -->


## 2. 用户需要怎样的交互来验证 / Desired verify interaction
<!-- 用户要点什么、看什么、操作什么才能确认「部署成功、能用」？越具体越好。
     例如：实时观测机械臂关节角度、上传一段音频看转写、扫码触发设备动作…… -->


## 3. 为什么现有方式不够 / Why fallbacks don't fit
<!-- 逐条说明为什么这些都不行： -->
- [ ] `web_dashboard`（打开任意 URL）不够，因为：
- [ ] `http_debug`（任意 HTTP 请求/响应）不够，因为：
- [ ] `actions.before/after` 自定义脚本不够，因为：
- [ ] 现有内置交互类型（`image_predict` / `text_chat` / `voice_chat` / `robot_inspect` …）不够，因为：


## 4. 你希望怎么解决 / Preferred resolution
<!-- 勾一个 -->
- [ ] 给我**插件 SDK**，我自己写（原型化，方案先在私有环境用）—— 见 [`docs/plugin-development.md`](../../docs/plugin-development.md)
- [ ] 做成**官方内置类型**（这样方案能进公开 catalog）
- [ ] 还不确定，想先讨论


## 5. 关联方案 / Related solution(s)
<!-- 哪个 solution 目录会用到？贴路径或 PR 链接。 -->
