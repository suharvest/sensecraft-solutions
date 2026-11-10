## 这套可部署方案是什么

**一台 reCamera 兼具眼睛与大脑，机械臂免外挂工控机，手机连热点即控，AI 智能体直接接管。**

装载 B4 CAN 底板的标准版 reCamera（SG2002，RISC-V）通过 SocketCAN 直驱 reBot B601-DM 机械臂的 7 个达妙伺服电机。无需外挂工控机或额外主控板。

控制守护进程 `armd` 静态二进制 **4.1 MB**，内存占用 **3.7 MB**，在 7 轴 50 Hz 闭环控制下单核 CPU 占用为 **7.0 %**。端侧 TPU 运行 YOLOv11 目标检测耗时 **47 ms**，CPU 实时解算 ArUco 标记 3D 位姿。

开机自建 Wi-Fi 热点，手机直连 8765 端口 Web 驾驶舱即可触控双摇杆与笛卡尔点动。通过一张 A4 纸打印的 ArUco 标记在浏览器内完成眼在手上（Eye-in-Hand）标定。提供 14 个原生 MCP 工具无缝接入 Claude Desktop 与 Claude Code。

**限制：** 需搭配 reCamera B4 CAN 底板，不支持 reCamera Pro；目前只原生验证 reBot B601-DM（达妙电机）；点选抓取目前仅在仿真中完整闭环，现场使用须确保物理急停可用。
