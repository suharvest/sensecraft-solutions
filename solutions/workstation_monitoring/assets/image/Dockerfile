ARG CUDA_BASE=jetson-worktime-cuda:12.6-r36.4.3
FROM ${CUDA_BASE} AS dependencies
USER root
COPY resources/uv /usr/local/bin/uv
COPY app/pyproject.toml app/uv.lock /opt/build/
COPY resources/wheels/ /opt/build/vendor/wheels/
WORKDIR /opt/build
RUN sed -i 's/ main$/ main universe/' /etc/apt/sources.list \
    && apt-get update && apt-get install -y --no-install-recommends python3-venv libopenblas0 libgomp1 libjpeg-turbo8 libpng16-16
RUN --mount=type=cache,target=/root/.cache/uv uv venv --python /usr/bin/python3.10 --system-site-packages /opt/venv \
    && UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --locked --no-dev \
    && /opt/venv/bin/python -c 'import torch, torchvision; assert torch.__version__.startswith("2.7.0"); assert torchvision.__version__.startswith("0.22.0")'

FROM ${CUDA_BASE} AS runtime
ARG RELEASE_VERSION=0.1.0-rc1-jp62-r36.4.3
USER root
LABEL org.opencontainers.image.title="Jetson Worktime" \
      org.opencontainers.image.version="${RELEASE_VERSION}" \
      org.opencontainers.image.description="Worktime, material counting and local training for Jetson Orin, Ubuntu 22.04, L4T 36.4.3"
RUN sed -i 's/ main$/ main universe/' /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get install -y --no-install-recommends \
       python3-gi python3-gst-1.0 python3.10 libpython3.10 libopenblas0 \
       gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-tools \
       gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
       gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-rtsp \
       fonts-noto-cjk fonts-dejavu-core libgl1 libglib2.0-0 libgomp1 hostname \
       python3-libnvinfer=10.3.0.30-1+cuda12.5 \
       libnvinfer10=10.3.0.30-1+cuda12.5 libnvinfer-plugin10=10.3.0.30-1+cuda12.5 \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb
COPY --from=dependencies /opt/venv /opt/venv
COPY resources/models/ /opt/jetson-worktime/models/
COPY resources/pretrained/ /opt/jetson-worktime/pretrained/
COPY resources/mediamtx/mediamtx /opt/jetson-worktime/vendor/mediamtx/mediamtx
COPY app/ /opt/jetson-worktime/
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/opt/jetson-worktime/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKTIME_CONTAINER=1 \
    WORKTIME_DIAGNOSTICS=0 \
    YOLO_AUTOINSTALL=False \
    YOLO_CONFIG_DIR=/opt/jetson-worktime/data/ultralytics \
    MPLCONFIGDIR=/opt/jetson-worktime/data/cache/matplotlib \
    XDG_CACHE_HOME=/opt/jetson-worktime/data/cache \
    TORCH_HOME=/opt/jetson-worktime/data/cache/torch \
    HOME=/opt/jetson-worktime/data/home
WORKDIR /opt/jetson-worktime
STOPSIGNAL SIGTERM
ENTRYPOINT ["/opt/venv/bin/python", "/opt/jetson-worktime/scripts/container_entry.py"]
CMD ["web"]
