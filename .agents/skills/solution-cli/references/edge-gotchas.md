# Seeed Studio 边缘计算硬件排障与通用排坑卡库 (Seeed Edge Gotchas & Troubleshooting Cards)

> **定位**：供 AI Agent 在用户处于 **硬件/算法排障（GOTCHAS_DEBUG）**、**跨平台移植** 或 **边缘编译报错** 时查阅。
> **官方产品归属声明**：
> - **Seeed Studio reComputer 系列**：包含基于 NVIDIA Jetson 平台的 **reComputer J 系列**（J4012, J4011, J2012, J1010 等）、基于 Rockchip 芯片的 **reComputer RK 系列**（RK3588, RK3576）以及基于树莓派的 **reComputer R 系列**，均为 Seeed Studio 官方标准硬件产品与官方 SKU。
> - **Seeed Studio reCamera 系列**：包含 **reCamera**（SG2002 RISC-V/ARM 双核）与 **reCamera Pro**（RV1126B 视觉 SoC），为 Seeed Studio 自研的模块化智能视觉相机产品线。
> - **Seeed Studio SenseCAP 系列**：包含 **SenseCAP Watcher**、工业级环境感知节点及 LoRaWAN 网关，为 Seeed Studio 工业级 IoT 与实体 AI 产品线。
>
> **排卡原则**：
> 1. **官方产品权威背书**：优先对齐 Seeed Studio 官方发布固件、BSP、载板接口与官方配件库（如 J 系列拓展板、CSI 摄像头转接板等）。
> 2. **剥离外部第三方硬件噪音**：完全剔除非 Seeed 公司的外部第三方硬件品牌（如前期评测涉及的外部竞品板卡名称），将经验沉淀为 Seeed 产品体系与底层芯片级的通用排障指南。

---

## 目录索引
- [Card 1: Seeed Studio reComputer RK 系列 / 通用 Rockchip SBC (RK3576 / RK3588) 排障卡](#card-1-seeed-studio-recomputer-rk-系列--通用-rockchip-sbc-rk3576--rk3588-排障卡)
- [Card 2: Seeed Studio reCamera (SG2002 / RISC-V / ARM) 排障卡](#card-2-seeed-studio-recamera-sg2002--risc-v--arm-排障卡)
- [Card 3: Seeed Studio reCamera Pro (RV1126B / Buildroot) 排障卡](#card-3-seeed-studio-recamera-pro-rv1126b--buildroot-排障卡)
- [Card 4: Seeed Studio SenseCAP Watcher / MCU 设备 (ESP32) 排障卡](#card-4-seeed-studio-sensecap-watcher--mcu-设备-esp32-排障卡)

---

## Card 1: Seeed Studio reComputer RK 系列 / 通用 Rockchip SBC (RK3576 / RK3588) 排障卡

适用于 Seeed Studio reComputer RK 系列主机及通用 Rockchip aarch64 Linux 系统（运行 Debian 12 / Ubuntu 22.04+ 内核 6.1.x）。

### 1.1 Docker 启动失败 `iptables: Failed to initialize nft` ⚠️ CRITICAL
- **症状**：
  ```text
  iptables: Failed to initialize nft: Protocol not supported
  docker info 报错 Cannot connect to the Docker daemon
  ```
- **根因**：部分 Linux 6.1.x BSP 内核编译时未开启 `CONFIG_NFT_COMPAT`，不支持 nftables backend。而现代 Docker 默认使用 nftables 初始化网络桥接。
- **修复**：在 Docker 启动前切换为 iptables-legacy：
  ```bash
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
  sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
  sudo systemctl reset-failed docker
  sudo systemctl restart docker
  ```

### 1.2 网络镜像源国内阻断
- **症状**：`docker compose pull`、`pip install`、`huggingface-cli download` 频繁超时。
- **修复**：
  - Docker：配置国内镜像或重写 compose 文件的 image 地址；
  - Python：`export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`；
  - HuggingFace：`export HF_ENDPOINT=https://hf-mirror.com`；
  - APT：使用清华/阿里源替换 `/etc/apt/sources.list`。

### 1.3 RKNN WSL2/x86 仿真正常但真机推理异常 / FP16 数值溢出
- **症状**：ONNX 转 RKNN 在主机端 simulator 能跑通，但在 RK3588/RK3576 真机推理时输出 NaN/Inf，或模型中间层计算溢出（特别是语音 ASR Paraformer 等包含深层 FFN 的模型）。
- **根因**：
  - RKNN NPU 硬件不支持标准的 IEEE 754 完整动态范围 FP32，全图 FP16 在后段高动态层可能越界溢出；
  - Simulator 与真机 `librknnrt` 在动态 Shape、CPU fallback 算子支持度上存在差异。
- **修复（Hybrid Split 混合切分）**：
  - 将易溢出的前置主干网保留在 NPU 跑 FP16；
  - 将后段易越界计算层（如 Block 30 之后或 Decoder 采样层）保留在 CPU 走 ONNX Runtime 运行；
  - 务必上真机测试精度与各层输出张量的 L2 范数差距（`rel_l2 < 0.05`）。

### 1.4 NPU 多核调度与设备节点权限
- **RK3588（3 核 NPU，6 TOPS）**：
  - 核心分配掩码 `rknn_core_mask`：
    - `0x1`（Core 0）、`0x2`（Core 1）、`0x4`（Core 2）、`0x7`（Core 0+1+2 聚合运行大模型）；
  - 多路视频流推理推荐各通道绑定单独立核心（`RKNN_NPU_CORE_0`、`1`、`2`），吞吐量远高于抢占单核。
- **设备权限保底**：
  ```bash
  ls -l /dev/rknn*
  # 若非 root 用户无权访问，添加 udev 规则：
  echo 'KERNEL=="rknn*", MODE="0666", GROUP="users"' | sudo tee /etc/udev/rules.d/99-rknn.rules
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```

### 1.5 板端多核编译防 OOM 崩溃
- **症状**：在板端执行 `make -j8` 或 `ninja` 时，系统突然死机、卡死或报错 `c++: fatal error: Killed signal terminated program cc1plus`。
- **根因**：编译 C++ 大型模板或神经网络库时单个编译线程耗费 1.5GB+ 内存，并发数超标直接触发 Linux 内核 OOM Killer 杀掉编译器甚至内核崩溃。
- **修复**：
  - 严格限制并发线程数：`MAX_JOBS = min(nproc, RAM_GB / 1.5)`；
  - 创建 4GB+ 临时 Swap 避免爆内存：
    ```bash
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    ```

---

## Card 2: reCamera (SG2002 / RISC-V / ARM) 通用排障卡

适用于轻量多核视觉设备（运行定制 Linux/Buildroot，集成单核/多核 NPU 与 ISP）。

### 2.1 内核 VPSS FIFO Overflow 崩溃 ⚠️ CRITICAL
- **症状**：
  - `dmesg` 报错：
    ```text
    isp_err_chk: CSIBDG_A fifo overflow
    vpss_sbm_err_handle: img(1) grp(0) vi err
    Unable to handle kernel paging request at virtual address ...
    Oops [#1]
    ```
  - 网络 `ping` 能通，但 `ssh`、`http`、`mqtt` 全部无响应。
- **根因**：内核底层 `cv181x_vpss` 驱动在处理高频抢占或未释放的 VI 视频通道时存在溢出 Bug。如果频繁启停摄像头服务或在自动化评测中无限循环 A/B 测试，极易耗尽 FIFO。
- **处置与预防**：
  1. 一旦发生，**必须拔掉电源进行物理断电重启**（纯软重启 `reboot` 无法复位挂死的硬件 ISP 寄存器）；
  2. 严格限制切换频率：不同模型或方案切换必须保证前一进程已彻底退出，并 `sleep 3` 秒再开启新实例；
  3. 同一时间只允许单实例占用相机节点。

### 2.2 动态库 `libsns_*.so` 报错为非致命噪音（红鲱鱼）
- **症状**：
  ```text
  Error loading shared library libsns_gc2053.so: No such file or directory
  Error relocating ... g_aeGc2053_MirrorFip: symbol not found
  ```
- **根因**：视觉组件在初始化时会尝试枚举匹配所有可能支持的 Sensor（如 OV5647、GC2053 等）。固件中只包含实际配备的 Sensor 驱动，musl loader 会打印缺失警告，但随后会成功匹配实际存在的 Sensor。
- **判别标准**：检查后续日志是否正常输出 `MQTT topic` 或 `Inference result`。若有，则此报错为纯日志噪音，切勿浪费时间到处寻找该 so。

### 2.3 `sscma-micro` 子模块升级冲掉本地模型注册
- **症状**：拉取或更新上游代码后，启动报 `ModelFactory::create returned nullptr - model format not recognized`。
- **根因**：上游原厂库通常未包含本地扩展的单输出模型类（如 `YoloSingle`），直接拉取上游会导致本地派生类被覆盖删除。
- **修复**：维护本地补丁分支，升级时显式保留 `ma_model_yolo_single.{cpp,h}` 并保证在 Factory 注册链中优先于通用宽泛的匹配项注册。

### 2.4 SSH Host Key 频繁变动
- **症状**：设备恢复出厂、重刷或多台设备共用同一调试 IP 时，报错 `REMOTE HOST IDENTIFICATION HAS CHANGED!`。
- **修复**：
  ```bash
  ssh-keygen -R <device_ip>
  ssh -o StrictHostKeyChecking=accept-new <user>@<device_ip>
  ```
  不要使用 `StrictHostKeyChecking=no` 彻底关闭安全保护，推荐使用 `accept-new` 自动接受新设备公钥。

---

## Card 3: reCamera Pro (RV1126B / Buildroot) 通用排障卡

适用于高帧率视觉 SoC（Buildroot Linux + rkipc 管道框架 + 独立 NPU）。

### 3.1 ⛔ 严禁 `while true` 死循环拉起进程（Fork 风暴致死）⚠️ CRITICAL
- **症状**：
  - 用 `while true; do rkipc; sleep 1; done` 做进程保活；
  - 一旦应用遇到语法错误或参数不匹配快速闪退，循环会以极高频率不断尝试 fork 新进程；
  - **严重后果**：整机进程 PID 资源耗尽。内核 ICMP 网络栈仍能极快响应 `ping`（<0.5ms），但 `ssh`、`adb`、`http` 全部由于无法 `fork()` 会话而瞬间拒绝连接。整机用户态瘫痪，**只能拔掉供电物理断电重启**。
- **预防与守则**：
  1. 调试阶段严禁使用死循环脚本拉起进程；
  2. 守护必须使用系统自带的 SysVinit 或受控守护进程，配置最大重启失败次数阈值；
  3. 热替换调试采用单次调试启动，前台监控日志。

### 3.2 `killall` 漏杀与双实例抢相机触发内核崩溃
- **症状**：`killall rkipc` 成功返回，但启动新版本时仍报 `Device or resource busy`，甚至导致内核 Oops。
- **根因**：`killall` 仅匹配精确进程名。如果自编译版本名为 `rkipc.new` 或带有路径，`killall` 会静默漏杀旧进程，造成两个实例同时抢占 VI/VPSS 通道。
- **修复规范**：
  ```bash
  # 必须使用 pgrep -f 匹配完整命令行
  for p in $(pgrep -f rkipc); do kill -9 $p; done
  sleep 3 # 关键：必须等待 3 秒释放视频通道硬件资源
  ```

### 3.3 adbd 退出时 Reap 掉 detach 子进程
- **症状**：通过 `adb shell 'setsid rkipc &'` 后台拉起进程，断开 adb 终端后进程直接消失。
- **根因**：adbd 会在会话断开时主动收割（reap）该会话树下的所有孤儿/子进程。
- **修复**：
  1. 将常驻服务交由系统的服务管理器托管（例如通过 `/etc/init.d/` 或 `/userdata/init.d/` 启动脚本注册），由 init/systemd/procd 统一管理生命周期，脱离交互式 adb 会话；
  2. 若排障临时脱离终端，通过 `daemon` 或服务守护命令拉起，重定向所有标准输入输出并脱离控制终端，避免随 adbd 会话断开被 reap。

### 3.4 OSD Overlay Layer 图层优先级与色彩倒置
- **症状**：
  - RGN API 显示创建成功、绑定成功，但在 RTSP/VENC 编码流画面中完全看不到标注框；
  - 标注框颜色异常（例如指定红色变成了青色）。
- **根因**：
  1. 硬件 VENC 编码器通常仅合成特定的低图层（如 Layer 1/5 可见，Layer 3/7 属于不可见的旁路）；
  2. OSD 颜色字节序为 ARGB 与 BGRA 的差异，若未显式翻转通道会导致颜色互补反转。
- **排查顺位**：画框不显示时**优先检查 Layer 层级值**，而非怀疑坐标计算或画框失败。

---

## Card 4: MCU / 纯固件设备 (Watcher / ESP32) 通用排障卡

适用于单片机与纯固件设备（FreeRTOS / 裸机）。

### 4.1 串口权限与烧录模式
- **症状**：`esptool` 或烧录工具报错 `Permission denied: /dev/ttyUSB0` 或 `Failed to connect to ESP32: Timed out waiting for packet header`。
- **排障**：
  - 检查权限：`sudo usermod -aG dialout $USER`；
  - 检查 Flash 模式：高频板建议使用 `DIO` 模式（40MHz/80MHz），严禁在不支持的 Flash 上强开 `QIO`；
  - 烧录前拉低 GPIO0（或按住 BOOT 键插入 USB）。

### 4.2 NVS 空间损坏与出厂分区对齐
- **症状**：固件烧录成功，但每次重启后配置丢失，报 `nvs_flash_init failed (ESP_ERR_NVS_NO_FREE_PAGES)`。
- **修复**：
  ```bash
  esptool.py --chip <chip> erase_flash # 全量擦除坏块与残留 NVS
  # 重新烧录完整分区表与固件
  ```

---

## 快速自检对照表

| 遇到此类症状 | 快速诊断命令 | 对应排障卡 |
|---|---|---|
| Docker 启动报 nft 协议错误 | `dmesg \| grep -i nft` | [Card 1 §1.1](#11-docker-启动失败-iptables-failed-to-initialize-nft--critical) |
| 板端编译卡死 / OOM | `dmesg \| grep -i oom` / `free -h` | [Card 1 §1.5](#15-板端多核编译防-oom-崩溃) |
| ping 通但 SSH/HTTP 全瘫痪 (Userspace 耗尽) | **停止重连，物理断电重启** | [Card 3 §3.1](#31--严禁-while-true-死循环拉起进程fork-风暴致死--critical) |
| 摄像头启动报 FIFO overflow | `dmesg \| grep -i fifo` | [Card 2 §2.1](#21-内核-vpss-fifo-overflow-崩溃--critical) |
| 模型画框不显示在视频流中 | 检查 RGN Layer 编号（使用低层如 1/5） | [Card 3 §3.4](#34-osd-overlay-layer-图层优先级与色彩倒置) |
| `libsns_*.so` 缺失警告 | 若推理正常则属于正常 Sensor 枚举噪音 | [Card 2 §2.2](#22-动态库-libsns_so-报错为非致命噪音红鲱鱼) |
