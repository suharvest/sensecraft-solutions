import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="ESPHome Compile Microservice")
compile_lock = asyncio.Lock()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/compile")
async def compile_firmware(file: Optional[UploadFile] = File(None), request: Request = None):
    content: bytes = b""

    if file is not None:
        content = await file.read()
    elif request is not None:
        content = await request.body()

    if not content or not content.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Missing YAML configuration", "output": "No YAML content provided"},
        )

    # Use a global queue lock to serialize compilation requests.
    # Prevents OOM crashes on resource-constrained edge hardware and eliminates PlatformIO cache races.
    async with compile_lock:
        temp_dir = tempfile.mkdtemp(prefix="esphome_build_")
        try:
            yaml_path = Path(temp_dir) / "config.yaml"
            yaml_path.write_bytes(content)

            cmd = ["esphome", "compile", str(yaml_path)]

            def _run_compile():
                try:
                    return subprocess.run(
                        cmd,
                        cwd=temp_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=600,
                    )
                except FileNotFoundError:
                    return None

            res = await asyncio.to_thread(_run_compile)
            if res is None:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Compilation failed", "output": "esphome executable not found"},
                )

            if res.returncode != 0:
                err_output = (res.stderr or "") + "\n" + (res.stdout or "")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Compilation failed", "output": err_output.strip()},
                )

            # Search for compiled binary
            build_dir = Path(temp_dir) / ".esphome" / "build"
            bin_file: Optional[Path] = None

            if build_dir.exists():
                for candidate in build_dir.rglob("*.bin"):
                    if candidate.name.endswith(".factory.bin"):
                        bin_file = candidate
                        break
                    if candidate.name == "firmware.bin" and bin_file is None:
                        bin_file = candidate
                    elif bin_file is None:
                        bin_file = candidate

            if bin_file is None:
                for candidate in Path(temp_dir).rglob("*.bin"):
                    bin_file = candidate
                    break

            if bin_file is None or not bin_file.is_file():
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Binary not found",
                        "output": "Compilation succeeded but no binary (.bin) was generated.",
                    },
                )

            bin_bytes = bin_file.read_bytes()
            out_name = bin_file.name

            return Response(
                content=bin_bytes,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
