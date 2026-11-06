FROM ghcr.io/esphome/esphome:latest

RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy warmup seeds and pre-warm ESPHome toolchain (downloads riscv32-esp-elf & ESP-IDF framework)
COPY warmup_seeds /tmp/warmup
RUN esphome compile /tmp/warmup/warmup_seed_c3.yaml \
    && rm -rf /tmp/warmup/.esphome/build

WORKDIR /app
COPY server/app.py /app/app.py

# Replace upstream entrypoint which forced `esphome` prefix
RUN printf '#!/bin/sh\nset -e\nif [ "$#" -eq 0 ]; then\n    exec uvicorn app:app --host 0.0.0.0 --port 6052\nfi\nif [ "${1#-}" != "$1" ]; then\n    exec uvicorn app:app --host 0.0.0.0 --port 6052 "$@"\nfi\nexec "$@"\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

EXPOSE 6052

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "6052"]

