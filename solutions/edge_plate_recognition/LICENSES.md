# LICENSES.md — edge_plate_recognition

依据 `seeed-solutions-hub/docs/rd-specs/NRD-3-edge-plate-recognition.md` §7（数据与模型，2026-09-25 核实结论）与 §13（独立审阅补充，2026-09-27）逐行登记。凡未锁定的一律标 **「待核实」**，不写「可商用」。

原则：**代码许可证不等于权重 / 训练数据许可证**（§13）。在训练数据来源链与权重许可锁定之前，本方案整体不得标注为可商用分发。

## 1. 代码

| 组件 | 版本 / 地址 | 许可证 | 原文链接 | 允许商用 | 署名要求 |
|---|---|---|---|---|---|
| YOLOX（检测模型代码 / 训练框架） | github.com/Megvii-BaseDetection/YOLOX | Apache-2.0 | https://github.com/Megvii-BaseDetection/YOLOX/blob/main/LICENSE | 是（按 Apache-2.0 条款） | 保留 LICENSE 与 NOTICE；修改需标注 |
| PlateRecNet（识别模型，本仓库自写） | 本方案 training/ 与 core_parking 内自写代码 | Apache-2.0（随所属仓库） | — | 代码本身是 | **仅覆盖代码**；不含训练图像与初始化权重（§13） |
| PaddleOCR（仅基线评测用代码） | github.com/PaddlePaddle/PaddleOCR | Apache-2.0 | https://github.com/PaddlePaddle/PaddleOCR | 是 | 保留 LICENSE/NOTICE |
| nlohmann/json（gate 插件头文件） | v3.11.3 | MIT | https://github.com/nlohmann/json/blob/develop/LICENSE.MIT | 是 | 在副本中保留版权与许可声明（§13 注明 2026-09-26 HEAD 200 已核实） |
| vision-base（运行时基座，含 MQTT/取帧等） | 仓库 `sensecraft-solutions` vision-base solution，tag 待回填 | 随仓库许可 | 待核实（tag 回填后补链接） | 待核实 | 待核实 |
| ONNX Runtime（jetson/rk3576/rk3588 推理运行时） | 版本以运行镜像为准（tag 待回填） | MIT | https://github.com/microsoft/onnxruntime/blob/main/LICENSE | 是 | 保留版权与许可声明；第三方组件见其 THIRD-PARTY-NOTICES |
| rknn-toolkit2 / RKNPU 运行时（RK3588/RK3576） | 版本以镜像为准 | 待核实（Rockchip 许可按发行包内 LICENSE 为准） | 待核实 | 待核实 | 待核实 |
| HailoRT / Hailo TAPPAS 相关（Hailo-8） | 版本以镜像为准 | 待核实（Hailo 发行文件按包内许可为准） | 待核实 | 待核实 | 待核实 |

## 2. 模型与权重

| 权重 | 来源链 | 许可证 | 允许商用 | 备注 |
|---|---|---|---|---|
| `plate_det_*`（自训检测权重） | YOLOX 代码（Apache-2.0）+ 训练数据（CCPD + 自研合成，见 §3） | **待核实** | **待核实** | 代码 Apache-2.0 不能推断权重许可；取决于训练数据权利链与 selfie 数据授权（§13）。来源链：YOLOX 初始化权重（COCO 预训练，Apache-2.0）→ 在 CCPD2019 base 5 万张 + CCPD2020 全部 + 合成 DE 2 万整图上微调 |
| `plate_rec_cn_*`（本期交付；DE 权重不在本期） | 本仓库自写模型结构 + 随机初始化 + 训练数据（同上） | **待核实** | **待核实** | 自写结构（Apache-2.0）；训练含 CCPD 图像，权利链未锁定前不得写可商用 |
| PP-OCRv5_mobile_rec（基线评测用权重） | https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_rec | Apache-2.0（模型卡 `license: apache-2.0`） | 是 | **仅基线评测，不随交付分发**；运行镜像与资产包不含该权重 |
| fast-plate-ocr 预训练权重 | github.com/ankandrew/fast-plate-ocr | 代码 MIT；权重训练数据未说明 | **不使用** | 附录候选，明确不用其预训练权重 |

## 3. 数据集

| 数据集 | 版本 / 下载 | 许可证 | 原文链接 | 允许商用 | 署名 / 限制 |
|---|---|---|---|---|---|
| CCPD（CCPD2019 + CCPD2020 绿牌） | 官方 README 提供的 Google Drive / 百度网盘，人工下载 | MIT | https://github.com/detectRecog/CCPD/blob/master/LICENSE | 是 | LICENSE 原文 "MIT License, Copyright (c) 2017 CCPD"；README 写明 "This dataset is open-source under MIT license"。**CCPD 图片含真实车牌：只用于训练，不随交付分发**；gallery 例外：2026-10-08 负责人决定 gallery 使用 3 张 CCPD 输入的真机预览截图（见 `gallery/ATTRIBUTION.md`） |
| 自拍测试集（CN/DE 过车） | 自有车辆 + 已获书面同意的同事车辆 | 自有 | — | 是 | 仅自有或已获书面同意的车辆；发布截图全部打码 |
| 合成数据（`training/plate_synth.py` 生成） | 本仓库自写生成器 + 下方两款字体 + 自有背景图 | 随方案许可（代码 Apache-2.0；含字体许可义务，见 §4） | — | 待核实（受字体许可约束） | 模板用 PIL 程序绘制，不用第三方车牌图片/模板文件；不用 COCO 图片合成，避免再分发问题 |

## 4. 字体（`training/plate_synth.py` 合成用，不随运行时分发）

| 字体 | 版本 / 下载地址 | 许可证 | 原文链接 | 允许商用 | 署名要求 |
|---|---|---|---|---|---|
| Noto Sans CJK SC（Bold，中文省份字符） | github.com/notofonts/noto-cjk | SIL OFL-1.1 | https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE | 是（字体不单独出售，OFL 条款） | **待核实**：下载包内 LICENSE 原文存档；OFL 要求随字体保留保留名与许可文本 |
| Alte DIN 1451 Mittelschrift（字母数字，CN/DE 共用） | https://www.1001fonts.com/alte-din-1451-mittelschrift-font.html | **待核实**：来源矛盾，OFL-1.1 或 CC BY 3.0 DE，以字体压缩包内自带许可文件为准 | 同上页面 | 两者均允许商用 | 若为 CC BY 3.0 DE，须署名 Peter Wiegel。注意：该字体与真实 GA 36 / FE-Schrift 字形不同，不构成对官方字体字形的复制 |
