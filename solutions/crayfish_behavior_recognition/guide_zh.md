# 部署指南：水产螯虾打斗与行为识别方案

在 Seeed reCamera 边缘相机上一键部署澳洲淡水龙虾实时打斗检测、公母性别鉴别与蜕壳残食风险预警。

---

## 预设：reCamera Pro {#recamera_pro}

在 reCamera Pro（RV1126B 3 TOPS NPU）上运行完整的端侧 4 级漏斗视觉流水线，支持 8 帧时序拼接验证与公母性别多帧投票。

## 第 1 步：部署螯虾行为监测应用 {#deploy_recamera_pro_crayfish type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

安装部署器会自动检查 reCamera Pro 上的 App Center，自动下载并部署官方固件离线包（`crayfish-fight-v0.1.2-core.tar.gz`），配置并激活推理应用。

### 部署目标 {#recamera_pro_device type=remote device_name="reCamera Pro" config=devices/recamera_pro.yaml}

---

## 预设：reCamera 2002 {#recamera_2002}

超紧凑型 RISC-V 边缘相机，运行 SG2002 原生 TPU BF16 模型，实现端侧目标检测与打斗粗筛报警。

## 第 1 步：部署螯虾检测器 {#deploy_recamera_2002_crayfish type=recamera_app required=true config=devices/recamera_2002.yaml}

安装原生 TPU 硬件加速模型 `crayfish_det_cv181x_bf16.cvimodel` 与 `crayfish_behavior_cv181x_bf16.cvimodel`，并启动 C++ 推理报警守护进程。

### 部署目标 {#recamera_2002_device type=remote device_name="reCamera 2002" config=devices/recamera_2002.yaml}
