# ATTRIBUTION — gallery 素材说明

**当前状态（如实声明）：截至本文件写入时，本方案没有任何实拍图。**

- 真机验收（NRD-3 spec §8.3 的 P10/P11 评测与 §10 验收，即 Y1–Y6 各平台实测）完成之前，`cover_image` 与 `gallery[]` **均为空，待实拍后回填**。
- 本目录下不存在任何截图或占位图；`solution.yaml` 中亦未登记任何 `cover_image` / `gallery` 条目。不得将演示脚本渲染图、合成图或网络图片当作真实截图使用。

## 回填要求（实拍后逐张登记）

每张图必须写明：

1. 拍摄平台（reCamera Pro / 2002 / Jetson / RK3588 / RK3576 / Hailo-8 / 主机形态）与光照（白天 / 夜间）。
2. 车辆归属：**自有车辆，或已获书面同意的同事车辆**（spec §7 评测集同源）。
3. 打码情况：非自有车辆车牌一律打码；页面与 gallery 不出现他人完整车牌（spec §10 隐私项）。
4. 来源：现场实拍，注明拍摄时间与拍摄者；不接受任何来源不明的图片。

CCPD 等含真实车牌的公开数据集图片原则上不进入 gallery、不随交付分发（见 `../LICENSES.md` §3）；例外见下方 2026-10-08 决定。

## Update 2026-10-08

`cover-20261008.jpg` is a generated illustration, not a screenshot. It is the only image registered for this package.

Real preview screenshots from the Jetson Orin Nano Super run of 2026-10-08 exist (`panel-preview-plate-1..3`), but they show CCPD2020 green-plate stills with full plate numbers of real vehicles (CCPD, MIT License, Copyright (c) 2017 CCPD; Xu, Z. et al., ECCV 2018). This file's rules and `../LICENSES.md` section 3 prohibit CCPD images and other people's full plate numbers in the gallery, so those screenshots are not published here. A gallery needs screenshots of own or consented vehicles, or masked plates.

## Decision 2026-10-08 (gallery uses CCPD screenshots)

The project owner decided on 2026-10-08 to publish `panel-preview-plate-{1,2,3}-20261008.jpg` unmasked.

- Content: real `/preview` screenshots of the package dashboard on Jetson Orin Nano Super (2026-10-08 ~05:11 UTC). Input frames are CCPD2020 green-plate stills streamed over RTSP; the page draws the detected plate box.
- Source and licence: CCPD (Xu, Z. et al., ECCV 2018), MIT License, Copyright (c) 2017 CCPD — https://github.com/detectRecog/CCPD/blob/master/LICENSE. The dataset README states "This dataset is open-source under MIT license."
- The images show plate numbers of real vehicles from the public dataset. This supersedes the earlier "no CCPD in gallery" rule for these three files only; other images still follow the rules above.

## Update 2026-10-09 (gallery v2)

`panel-preview-plate-{1,2,3}-20261008.jpg` were removed and replaced by three v2 screenshots. `cover-20261008.jpg` (generated illustration) is unchanged.

| File | Device | Input (CCPD test split) | Read / ground truth |
|---|---|---|---|
| `panel-plate-1-jetson-blue-oblique-20261009.jpg` | Jetson Orin Nano Super | CCPD2019 `ccpd_tilt/0483-19_24-196&575_428&749-…-38-44.jpg` (blue, front, oblique) | 皖A62599 0.98 / 皖A62599 |
| `panel-plate-2-jetson-green-front-20261009.jpg` | Jetson Orin Nano Super | CCPD2020 `ccpd_green/test/04353208812260537-87_261-…-143-154.jpg` (green, front) | 皖AF10528 0.87 / 皖AF10528 |
| `panel-plate-3-rk3588-blue-rear-20261009.jpg` | Radxa RK3588 | CCPD2019 `ccpd_challenge/0337-7_0-194&393_423&516-…-107-29.jpg` (blue, rear) | 皖ALY625 0.90 / 皖ALY625 |

- Content: browser screenshots (Playwright Chromium, 1440 px viewport, DPR 1) of the app's own `/preview` page, 2026-10-08 09:18–09:33 UTC. Page code: edge-parking-vision `d38901c`; the same page ships in `nrd-parking-{jetson,rk}:20261009` (built from `e5f9dec`).
- Input: `plate-ccpd8-v2-1080p-96s.mp4` (8 CCPD test-split stills, 10 s each, 2 s dark gap) over RTSP. Each label value is the app's `parking.plate/1` event for that track; ground truth is decoded from the CCPD file name.
- Processing for the gallery: PNG → JPEG quality 85, 1440 px wide, no other edits. Full evidence: `acceptance-20261008/visuals/edge_plate_recognition/v2/` (ATTRIBUTION.md, captions.yaml, `_evidence/`).
- Source and licence: CCPD (Xu, Z. et al., "Towards End-to-End License Plate Detection and Recognition: A Large Dataset and Baseline", ECCV 2018), https://github.com/detectRecog/CCPD — MIT License, Copyright (c) 2017 CCPD. The MIT notice travels with these images. The plates belong to real vehicles photographed on public streets; the owner decision of 2026-10-08 above covers these three files.
- The recognition models were trained on CCPD data; whether training excluded every test-split image used here is 需核实.
