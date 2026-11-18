FROM ubuntu:22.04@sha256:74b12b11ffa550fba1929ad4d8d16533c34f6612728469671afba1b03b66881c

ARG UBUNTU_MIRROR=http://mirrors.aliyun.com/ubuntu-ports

LABEL org.opencontainers.image.title="Jetson Worktime CUDA Runtime" \
      org.opencontainers.image.description="ARM64 CUDA 12.6 and cuDNN 9.3 runtime, verified on L4T 36.4.3" \
      com.seeed.cuda.version="12.6.68" \
      com.seeed.cudnn.version="9.3.0.75" \
      com.seeed.l4t.verified="36.4.3"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    CUDA_HOME=/usr/local/cuda-12.6 \
    LD_LIBRARY_PATH=/usr/local/cuda-12.6/targets/aarch64-linux/lib:/usr/lib/aarch64-linux-gnu/nvidia \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,video \
    CUDA_MODULE_LOADING=LAZY

COPY jetson-ota-public.asc /usr/share/keyrings/jetson-ota-public.asc
COPY runtime-packages.lock /opt/jetson-cuda/runtime-packages.lock

RUN printf 'deb %s jammy main\ndeb %s jammy-updates main\ndeb %s jammy-security main\n' \
       "$UBUNTU_MIRROR" "$UBUNTU_MIRROR" "$UBUNTU_MIRROR" > /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get install -y --no-install-recommends ca-certificates python3 libstdc++6 \
    && printf '%s\n' \
       'deb [arch=arm64 signed-by=/usr/share/keyrings/jetson-ota-public.asc] https://repo.download.nvidia.cn/jetson/common r36.4 main' \
       > /etc/apt/sources.list.d/jetson-cuda.list \
    && apt-get -o Acquire::Retries=3 update \
    && xargs apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
       < /opt/jetson-cuda/runtime-packages.lock \
    && printf '%s\n' '/usr/local/cuda-12.6/targets/aarch64-linux/lib' \
       > /etc/ld.so.conf.d/jetson-cuda.conf \
    && ldconfig \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb

COPY verify_cuda.py /opt/jetson-cuda/verify_cuda.py

CMD ["/bin/bash"]
