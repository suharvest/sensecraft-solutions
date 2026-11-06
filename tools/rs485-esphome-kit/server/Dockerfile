FROM ghcr.io/esphome/esphome:latest AS warmup

# Copy warmup seeds and pre-warm ESPHome toolchain (downloads riscv32-esp-elf & ESP-IDF framework)
COPY warmup_seeds /tmp/warmup
RUN esphome compile /tmp/warmup/warmup_seed_c3.yaml \
    && rm -rf /tmp/warmup/.esphome/build \
    && rm -rf /root/.cache/esphome/idf/ccache \
    && rm -rf /root/.cache/esphome/idf/frameworks/5.5.6/docs \
    && rm -rf /root/.cache/esphome/idf/frameworks/5.5.6/examples \
    && rm -rf /root/.cache/uv

# Reorganize cache into granular layers to stay well within reverse proxy upload limits (Tengine 413)
RUN RPATH=/root/.cache/esphome/idf/tools/riscv32-esp-elf/esp-14.2.0_20260121/riscv32-esp-elf \
    && mkdir -p /layers/1/root/.cache/esphome/idf \
                /layers/2/root/.cache/esphome/idf/tools \
                /layers/3${RPATH} \
                /layers/4a${RPATH}/riscv32-esp-elf/lib \
                /layers/4b${RPATH}/riscv32-esp-elf/lib \
                /layers/4c${RPATH} \
                /layers/4d${RPATH} \
                /layers/5${RPATH} \
    && mv /root/.cache/esphome/idf/frameworks /layers/1/root/.cache/esphome/idf/ \
    && mv /root/.cache/esphome/idf/idf-env.json /layers/1/root/.cache/esphome/idf/ \
    && mv /root/.cache/esphome/idf/component_mirror /layers/1/root/.cache/esphome/idf/ \
    && mv /root/.cache/esphome/idf/penvs /layers/2/root/.cache/esphome/idf/ \
    && mv /root/.cache/esphome/idf/tools/cmake /layers/2/root/.cache/esphome/idf/tools/ \
    && mv /root/.cache/esphome/idf/tools/esp-rom-elfs /layers/2/root/.cache/esphome/idf/tools/ \
    && mv ${RPATH}/bin ${RPATH}/libexec ${RPATH}/lib ${RPATH}/include ${RPATH}/package.json /layers/3${RPATH}/ \
    && mv ${RPATH}/riscv32-esp-elf/lib/rv32i_* ${RPATH}/riscv32-esp-elf/lib/rv32imac_* /layers/4a${RPATH}/riscv32-esp-elf/lib/ \
    && mv ${RPATH}/riscv32-esp-elf/lib/rv32imafc_* /layers/4b${RPATH}/riscv32-esp-elf/lib/ \
    && mv ${RPATH}/riscv32-esp-elf /layers/4c${RPATH}/ \
    && mv ${RPATH}/picolibc /layers/4d${RPATH}/ \
    && mv ${RPATH}/share /layers/5${RPATH}/

FROM ghcr.io/esphome/esphome:latest

RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy pre-warmed ESPHome toolchains in granular layers (< 500MB each)
COPY --from=warmup /layers/1/ /
COPY --from=warmup /layers/2/ /
COPY --from=warmup /layers/3/ /
COPY --from=warmup /layers/4a/ /
COPY --from=warmup /layers/4b/ /
COPY --from=warmup /layers/4c/ /
COPY --from=warmup /layers/4d/ /
COPY --from=warmup /layers/5/ /

WORKDIR /app
COPY server/app.py /app/app.py
COPY warmup_seeds /tmp/warmup

# Replace upstream entrypoint which forced `esphome` prefix
RUN printf '#!/bin/sh\nset -e\nif [ "$#" -eq 0 ]; then\n    exec uvicorn app:app --host 0.0.0.0 --port 6052\nfi\nif [ "${1#-}" != "$1" ]; then\n    exec uvicorn app:app --host 0.0.0.0 --port 6052 "$@"\nfi\nexec "$@"\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

EXPOSE 6052

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "6052"]
