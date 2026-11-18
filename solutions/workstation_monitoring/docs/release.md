# 生产工位工时与物料监测：候选镜像与离线交付

发布日期：2026-11-17。版本：`0.1.0-rc1-jp62-r36.4.3`。

当前 Solution ID 为 `workstation_monitoring`。方案改名继续复用下列已发布镜像和离线归档，运行标识与原部署目录的对应关系见[运维说明](operations.md#solution-naming)。

公开仓库：[chenduola6/jetson-worktime](https://hub.docker.com/r/chenduola6/jetson-worktime)。

```sh
docker pull --platform=linux/arm64 chenduola6/jetson-worktime:0.1.0-rc1-jp62-r36.4.3
```

固定内容的镜像引用：

```text
chenduola6/jetson-worktime@sha256:19d0ad6e354d1d21c8a6e34c7ef37e5a0f1e21e6ddcac7449639ea4fdc211069
```

离线归档 `jetson-worktime-0.1.0-rc1-jp62-r36.4.3-arm64.tar.gz` 为 2,934,038,936 字节，包含镜像、Compose、初始化与恢复脚本。SHA256：

```text
9fc3449479f33adf6747065895264f90a4ae63a91a250079d93266d415881416
```

归档中的 `image_id` 与已发布镜像索引摘要一致；归档在发布前生成，因此内置清单未包含发布后追加的 `registry_digest` 字段。离线安装使用归档 SHA256、内部镜像 SHA256 与解压镜像层摘要验证，不依赖网络访问。

在线一键部署使用本方案 guide 中的入口；完整离线包可通过运维文档中的 `package.py install` 安装。首次部署不安装 Python 包或编译源码。兼容条件、数据备份、端口设置和故障恢复见 [运维文档](operations.md)；已验证范围与待补齐测试见 [验证记录](validation.md)。当前仍为 RC，不应将目标设备列表视为已经逐台验收。
