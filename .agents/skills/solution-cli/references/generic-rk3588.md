# Rockchip RK3588 开发、编译与故障排查指南 (RK3588 & Seeed reComputer RK Guide)

> **定位**：供 AI Agent 在用户基于 **Seeed Studio reComputer RK 系列** 或通用 Rockchip RK3588 (aarch64 Linux) 主机进行 **模型编译、Docker 部署、NPU 驱动调试或二次开发** 时查阅。
> **官方产品背书与原则**：
> 1. **Seeed 官方产品**：Seeed Studio 官方提供基于 Rockchip 高算力平台的 **reComputer RK 系列**（如 RK3588、RK3576 等硬件 SKU），出厂配备官方标准 BSP、散热外壳与外设接口。
> 2. **剥离外部第三方硬件噪音**：完全剔除前期技术验证中涉及的外部第三方竞品开发板名称，提炼为统一的 Seeed 硬件体系与芯片级通用工程排障指南。

---

## 1. RK3588 硬件与 NPU 基础架构

Rockchip RK3588 是一颗八核 64 位处理器（4×Cortex-A76 + 4×Cortex-A55），内置 3 个独立的 NPU 核心（每个核心提供 2 TOPS 算力，峰值算力 6 TOPS INT8）。

### 1.1 关键硬件节点与驱动文件
在任何标准 RK3588 Linux 系统中，NPU 与多媒体加速依赖以下底层设备节点：
- `/dev/rknn`（或 `/dev/rknpu*`）：NPU 驱动设备节点；
- `/dev/mpp_service`：Rockchip 硬件多媒体编解码（MPP）设备节点；
- `/dev/rga`：2D 图形与格式转换（RGA）硬件加速设备节点；
- `/dev/dma_heap/`：用于 NPU 与 MPP 之间零拷贝（Zero-Copy）的连续物理内存管理。

---

## 2. 常见系统级故障与通用排查 (Common Gotchas)

### 2.1 Docker 启动报错：Failed to initialize nft / Protocol not supported
- **根因**：多数针对 RK3588 的 Linux 5.10 内核在编译时未开启 `CONFIG_NF_TABLES`，而较新版本的 iptables 默认采用 `nf_tables` 后端。
- **通用修复命令**（板端执行一次即可）：
  ```bash
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
  sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
  sudo systemctl restart docker
  ```

### 2.2 容器内 NPU 访问被拒绝：cannot open /dev/rknn 或 Permission Denied
- **根因 1：Docker 未挂载 NPU 设备节点**
  在 `docker run` 或 `docker-compose.yml` 中必须显式透传设备：
  ```yaml
  services:
    my-app:
      devices:
        - /dev/rknn:/dev/rknn
        - /dev/mpp_service:/dev/mpp_service
        - /dev/rga:/dev/rga
        - /dev/dma_heap:/dev/dma_heap
  ```
- **根因 2：非 root 用户缺少 udev 访问权限**
  在宿主机配置 udev 规则赋予权限：
  ```bash
  echo 'KERNEL=="rknn*", MODE="0666"' | sudo tee /etc/udev/rules.d/99-rknn.rules
  echo 'KERNEL=="mpp_service*", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-rknn.rules
  echo 'KERNEL=="rga*", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-rknn.rules
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```

### 2.3 NPU 驱动版本与 Runtime 运行时不兼容 (RKNN Version Mismatch)
- **排查命令**：
  ```bash
  # 检查宿主机内核 NPU 驱动版本
  dmesg | grep -i rknpu
  ```
- **关键规则**：
  - RK3588 必须使用 **RKNN-Toolkit2**（对应 `librknnrt.so` 版本通常为 v1.5.x, v1.6.x 或 v2.x），绝对不能使用针对上一代 RK1808/RV1109 的 RKNN-Toolkit1；
  - 容器内的 `librknnrt.so` 版本必须 **大于或等于** 宿主机内核中的驱动驱动版本。若报错 `RKNN_ERR_DEVICE_UNMATCH`，需升级宿主机内核驱动固件或降级镜像内的 runtime。

---

## 3. 板端编译与构建最佳实践 (Building on Device)

### 3.1 限制多线程并发编译，防止内存耗尽 (OOM Kill)
- **痛点**：RK3588 具备 8 个核心，开发者习惯敲 `make -j8`，但在编译 OpenCV、ONNX Runtime 或 PyTorch 扩展时，每个编译进程会占用 1~1.5GB 内存，直接触发内核 OOM killer 杀死进程。
- **推荐做法**：
  ```bash
  # 8GB 内存设备推荐最大并发为 4
  make -j4
  # 或者增加 8GB 虚拟内存 Swap 分区
  sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  ```

### 3.2 CMake 关键参数标准配置
在编写或修改 `CMakeLists.txt` 构建 C++ 推理应用时：
```cmake
# 显式启用 RKNPU2 目标后端
set(CMAKE_CXX_STANDARD 14)
target_include_directories(my_app PRIVATE ${RKNN_API_PATH}/include)
target_link_libraries(my_app PRIVATE ${RKNN_API_PATH}/lib/librknnrt.so dl pthread)
```

---

## 4. RK3588 算力调优：三核 NPU 调度与硬件零拷贝

### 4.1 多核心分流调度 (Multi-core NPU Balancing)
RK3588 的 3 个 NPU 核心可以通过 `rknn_core_mask` 手动绑定，避免多线程挤占同一核心导致上下文频繁切换：
- `RKNN_NPU_CORE_0`：绑定核心 0（适合处理主视频流）；
- `RKNN_NPU_CORE_1`：绑定核心 1（适合处理次级任务或特征比对）；
- `RKNN_NPU_CORE_2`：绑定核心 2；
- `RKNN_NPU_CORE_0_1_2` / `AUTO`：单模型跨核并发加速（大模型降低单帧延迟）。

### 4.2 全链路硬件加速防 CPU 占满
- **反模式**：使用纯 Python OpenCV `cv2.VideoCapture` 软解 RTSP H.264/H.265 流，CPU 占用率飙到 300%~500%，系统发热降频。
- **推荐架构**：
  `RTSP H.264/H.265` ➔ **Rockchip MPP 硬件解码** ➔ 输出 NV12 格式
  NV12 ➔ **RGA 硬件缩放 & BGR 转换** ➔ 直接输入内存缓冲区
  内存缓冲区 ➔ **NPU 执行推理**（Zero-Copy DMA 共享）
  整个流水线 CPU 占用率通常不足 20%。
