# 跨平台测量协议

SKILL.md 讲原则，这里给可直接抄的命令与判据。所有示例来自本仓库 fall_detection 的实测。

---

## 1. 加速器推理（各平台命令）

同一个模型、同一输入尺寸、同一量化。空闲板卡，停掉占用同一加速器的业务。

```bash
# Jetson —— 与既有基线同参数
/usr/src/tensorrt/bin/trtexec --loadEngine=X.engine \
  --useCudaGraph --noDataTransfers --infStreams=N --duration=10 --warmUp=2000
# 注意：--version 在 TensorRT 10.3 上退出码为 1，不能用它 gate 构建

# Rockchip
python3 platforms/rknn/benchmark.py --postprocess-backend cpp   # 空白 640 输入

# Hailo
hailortcli benchmark --time-to-run 15 model.hef                 # 给出 FPS 与 HW latency
hailortcli parse-hef model.hef                                  # 看 context 数，多 context 会显著掉速

# reCamera 系列
# 从应用自己的计时字段取，但必须先确认该字段的范围（见下）
```

## 2. 确认计时字段的范围

**不要看字段名猜。** 找到赋值处，看计时起止卡在哪：

```bash
grep -rn "inference_time_ms\s*=\|inference_ms\s*=" <platform-dir>/
```

判断要点：
- 起点在取帧之前还是之后？（含不含采集）
- 终点在后处理之前还是之后？（含不含解码/NMS）
- 跟踪、时序、消息发布在里面吗？

本项目结论：Jetson 的 `inference_time_ms` 是 pipeline 范围；reCamera Pro 的是纯 NPU；
reCamera 2002 只有一个 detectAll 计时器且是整数毫秒，**分不出加速器**。

## 3. CPU 占用：用 cgroup，不要用 docker stats

`docker stats` 对突发负载不可用——实测同一组样本在 60%–352% 之间跳。

```bash
id=$(docker inspect -f '{{.Id}}' "$C")
cf=/sys/fs/cgroup/system.slice/docker-$id.scope/cpu.stat
t0=$(awk '/usage_usec/{print $2}' "$cf"); s0=$(date +%s)
# ... 观测窗口 ...
t1=$(awk '/usage_usec/{print $2}' "$cf"); s1=$(date +%s)
awk -v t0=$t0 -v t1=$t1 -v s0=$s0 -v s1=$s1 \
  'BEGIN{printf "cores=%.2f\n", (t1-t0)/1e6/(s1-s0)}'
```

**比较 CPU 前必须对齐吞吐。** 处理帧数不同的两组，绝对 CPU 没有可比性；要么限速到同一 fps，
要么同时给出「单帧 CPU」。

## 4. 频率与共存负载

```bash
# NPU（Rockchip / reCamera Pro）
cat /sys/class/devfreq/*npu*/{governor,cur_freq,max_freq,available_frequencies}
# 采样确认是否稳定在顶档，而不是只看一次
for i in $(seq 40); do cat /sys/class/devfreq/*npu*/cur_freq; sleep 0.5; done | sort | uniq -c

# 锁频（需 root；reCamera Pro 无 sudo，走 adb）
echo <max> > /sys/class/devfreq/<npu>/min_freq
for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $c; done
# 测完还原

# Jetson
nvpmodel -q && jetson_clocks --show
```

**共存负载**只有在占用同一加速器时才需要停。判断方法：停掉前后各测一次，数值不变说明无关。

## 5. 真实画面 pipeline

用真实 RTSP 源，记录：帧数、其中有人的帧数、mean/median/p95。

注意事项：
- **循环播放的测试源会在循环点重置 PTS**，可能触发解码器丢帧，与真实摄像头行为不同
- **启动阶段会有一次性丢帧**（清积压追实时），预热足够时间再开始计数
- `gst-launch ... fakesink num-buffers=N` 会在收满后停止消费，**产生大量"丢帧"假象**，
  测吞吐不要加 `num-buffers`

## 6. 准确率：只读一次的测试集

协议（以 GMDCSA-24 为例）：
- 按人划分：Subject 1–2 训练时序模型，Subject 3 选阈值并冻结配置，**Subject 4 只读一次**
- 视频统一重采样到目标帧率，每段开始前重置跟踪与时序状态
- 比标注起点早 0.5 秒以上的报警计为误报
- **每个平台用自己真实的姿态输出重新抽取轨迹、重训并冻结权重**，不跨平台借用

报告方式：给测试方法 + 平均值 + 区间。27 段片段的分辨率是 3.7 个百分点，**不要做平台排名表**。

### 鲁棒性测试（可选但有用）

想验证某个工程变更（如丢帧）对准确率的影响，不要重搭实时评测——**在已冻结的轨迹上注入该变量
重跑冻结门限**，这样它是唯一变量。前提是**先复现基线**，跑不出冻结值就说明环境不一致，
后续对比无效。

## 7. 报告模板

每个数字旁边要能回答：**测的什么口径、什么条件、多少样本。**

```
| 平台 | 模型/量化 | 加速器推理 | 真实画面 pipeline | 前后处理增量 |
|---|---|---:|---:|---:|
```

配套说明必须包含：输入是什么（合成/真实）、样本量、是否锁频、是否停共存业务、
某列为空的原因。
