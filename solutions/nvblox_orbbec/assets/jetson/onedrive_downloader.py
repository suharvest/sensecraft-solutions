#!/usr/bin/env python3
"""Download public OneDrive/SharePoint share links with resume support."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

import requests

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - exercised via behavior tests
    tqdm = None


CHUNK_SIZE = 1024 * 1024
MIN_VALID_SIZE = 1024 * 1024
PROBE_CHUNK_SIZE = 4096
REQUEST_TIMEOUT = (15, 600)
DEFAULT_BACKEND = "auto"
DEFAULT_ARIA2_SPLIT = 8
DEFAULT_ARIA2_MAX_CONNECTION_PER_SERVER = 8
DEFAULT_ARIA2_MIN_SPLIT_SIZE = "32M"
PROGRESS_SPEED_WINDOW_SECONDS = 30.0
LEGACY_PARTIAL_RESTART_FRACTION = 0.05
LEGACY_PARTIAL_RESTART_MAX_BYTES = 1024 * 1024 * 1024
DEFAULT_SHARE_URL = (
    "https://seeedstudio88-my.sharepoint.com/:u:/g/personal/"
    "youjiang_yu_seeedstudio88_onmicrosoft_com/"
    "IQCCDToomY6WSaRZdfsTs9vXAengb-SCEvNfSUgq0cipP6w?e=z9axor"
)
DEFAULT_FILENAME = "nvblox_images.tar"
DEFAULT_OUTPUT_DIR = Path.home() / ".cache" / "jetson-examples" / "nvblox"
SUPPORTED_DOMAINS = ("sharepoint.com", "sharepoint.cn")
SHARE_LINK_RE = re.compile(r"^/:[a-z]:/", re.IGNORECASE)
TEXT_ERROR_MARKERS = (
    "forbidden",
    "access denied",
    "sign in",
    "login",
    "not found",
    "permission",
)


class DownloadError(Exception):
    """Raised when the download cannot proceed safely."""


@dataclass(frozen=True)
class ProbeResult:
    resolved_url: str
    filename: str
    total_size: int | None
    supports_range_requests: bool
    cookie_header: str | None


@dataclass(frozen=True)
class DownloadPlan:
    backend: str
    reason: str
    restart_partial: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a public Microsoft 365 OneDrive/SharePoint share link."
    )
    parser.add_argument(
        "share_url",
        nargs="?",
        default=DEFAULT_SHARE_URL,
        help="Public sharepoint.com/sharepoint.cn share link",
    )
    parser.add_argument(
        "legacy_filename",
        nargs="?",
        help="Legacy positional filename override",
    )
    parser.add_argument(
        "--output-dir",
        "--download-dir",
        dest="output_dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save the file (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--filename",
        help="Override the detected filename. Only the final path component is used.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload even if the target file already exists.",
    )
    parser.add_argument(
        "--aria2c",
        action="store_true",
        help="Print an aria2c command for the resolved direct download URL",
    )
    parser.add_argument(
        "--progress-mode",
        choices=("auto", "tqdm", "line"),
        default="auto",
        help="Progress rendering mode. 'line' is best for remote non-interactive logs.",
    )
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=5.0,
        help="Seconds between line-based progress updates.",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "requests", "aria2c"),
        default=DEFAULT_BACKEND,
        help="Download backend. 'auto' prefers aria2c multi-connection download when safe.",
    )
    parser.add_argument(
        "--aria2-split",
        type=int,
        default=DEFAULT_ARIA2_SPLIT,
        help="Number of parallel segments aria2c should use when the aria2c backend is selected.",
    )
    parser.add_argument(
        "--aria2-max-connection-per-server",
        type=int,
        default=DEFAULT_ARIA2_MAX_CONNECTION_PER_SERVER,
        help="Maximum parallel aria2c connections to the same server.",
    )
    parser.add_argument(
        "--aria2-min-split-size",
        default=DEFAULT_ARIA2_MIN_SPLIT_SIZE,
        help="Minimum segment size aria2c should use when splitting the download.",
    )
    return parser.parse_args()


def is_supported_host(hostname: str) -> bool:
    hostname = hostname.lower()
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in SUPPORTED_DOMAINS
    )


def sanitize_filename(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip().strip("\"'")
    if not candidate:
        return None
    candidate = candidate.replace("\\", "/")
    candidate = Path(candidate).name
    if candidate in {"", ".", ".."}:
        return None
    return candidate


def validate_source_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise DownloadError("share_url is required.")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise DownloadError("URL must start with http:// or https://.")

    hostname = parsed.hostname or ""
    is_sharepoint_host = is_supported_host(hostname)

    lower_path = (parsed.path or "").lower()
    if is_sharepoint_host and "/_layouts/15/onedrive.aspx" in lower_path:
        raise DownloadError(
            "Unsupported page-style OneDrive URL. Use a public share link instead of "
            "a /_layouts/15/onedrive.aspx page or a login-protected page."
        )

    if not parsed.path:
        raise DownloadError("URL path is empty.")

    return url


def needs_download_flag(parsed_url) -> bool:
    return bool(SHARE_LINK_RE.match(parsed_url.path or ""))


def with_download_flag(url: str) -> str:
    parsed = urlparse(url)
    if not needs_download_flag(parsed):
        return url

    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "download"
    ]
    query_items.append(("download", "1"))
    return urlunparse(parsed._replace(query=urlencode(query_items, doseq=True)))


def looks_like_landing_page(content_type: str, first_chunk: bytes) -> bool:
    content_type = (content_type or "").lower()
    first = (first_chunk or b"").lstrip()
    first_lower = first.lower()

    if "text/html" in content_type or "application/xhtml" in content_type:
        return True

    if first_lower.startswith(b"<!doctype html") or first_lower.startswith(b"<html"):
        return True

    if content_type.startswith("text/plain"):
        snippet = first[:512].decode("utf-8", errors="ignore").lower()
        if any(marker in snippet for marker in TEXT_ERROR_MARKERS):
            return True

    return False


def filename_from_content_disposition(header_value: str | None) -> str | None:
    if not header_value:
        return None

    match = re.search(
        r"filename\*\s*=\s*(?:[A-Za-z0-9!#$&+\-.^_`|~]+'[^']*')?([^;]+)",
        header_value,
        flags=re.IGNORECASE,
    )
    if match:
        return sanitize_filename(unquote(match.group(1).strip().strip("\"'")))

    match = re.search(r'filename\s*=\s*"([^"]+)"', header_value, flags=re.IGNORECASE)
    if match:
        return sanitize_filename(match.group(1))

    match = re.search(r"filename\s*=\s*([^;]+)", header_value, flags=re.IGNORECASE)
    if match:
        return sanitize_filename(match.group(1))

    return None


def filename_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    return sanitize_filename(unquote(Path(parsed.path or "").name))


def cookie_header_from_jar(cookie_jar) -> str | None:
    pairs = []
    for cookie in cookie_jar:
        if not cookie.name:
            continue
        pairs.append(f"{cookie.name}={cookie.value}")
    if not pairs:
        return None
    return "; ".join(pairs)


def parse_total_size(response: requests.Response) -> int | None:
    content_range = response.headers.get("content-range", "")
    match = re.search(r"/(\d+)\s*$", content_range)
    if match:
        return int(match.group(1))

    content_length = response.headers.get("content-length")
    if content_length and content_length.isdigit():
        return int(content_length)

    return None


def probe_supports_range_requests(response: requests.Response) -> bool:
    accept_ranges = (response.headers.get("accept-ranges") or "").lower()
    content_range = response.headers.get("content-range") or ""
    return (
        response.status_code == 206
        or accept_ranges == "bytes"
        or content_range.lower().startswith("bytes ")
    )


def probe_remote_target(url: str, filename_override: str | None) -> ProbeResult:
    headers = {"Range": "bytes=0-0"}
    session = requests.Session()
    response = None
    try:
        response = session.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers=headers,
        )
    except requests.RequestException as exc:
        raise DownloadError(f"Failed to resolve the download target: {exc}") from exc

    try:
        response.raise_for_status()
        first_chunk = next(response.iter_content(chunk_size=PROBE_CHUNK_SIZE), b"")
        if looks_like_landing_page(response.headers.get("content-type", ""), first_chunk):
            raise DownloadError(
                "The link resolved to an HTML/text page instead of a downloadable file."
            )

        filename = (
            sanitize_filename(filename_override)
            or filename_from_content_disposition(
                response.headers.get("content-disposition")
            )
            or filename_from_url(response.url)
        )
        if not filename:
            raise DownloadError(
                "Could not infer a filename from the response. Pass --filename."
            )

        return ProbeResult(
            resolved_url=response.url,
            filename=filename,
            total_size=parse_total_size(response),
            supports_range_requests=probe_supports_range_requests(response),
            cookie_header=cookie_header_from_jar(session.cookies),
        )
    except requests.RequestException as exc:
        raise DownloadError(f"Failed to resolve the download target: {exc}") from exc
    finally:
        if response is not None:
            response.close()
        session.close()


def prepare_target_paths(
    output_dir: Path, filename: str, force: bool
) -> tuple[Path, Path, bool]:
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename
    tmp_path = filepath.with_suffix(filepath.suffix + ".part")

    if force:
        if filepath.exists():
            print(f"Removing cached file: {filepath}", flush=True)
            filepath.unlink()
        if tmp_path.exists():
            print(f"Removing partial download: {tmp_path}", flush=True)
            tmp_path.unlink()
        return filepath, tmp_path, False

    if filepath.exists():
        size = filepath.stat().st_size
        if size > MIN_VALID_SIZE:
            print(f"File already exists: {filepath}", flush=True)
            return filepath, tmp_path, True
        print(
            f"Existing file is too small ({size} bytes), redownloading: {filepath}",
            flush=True,
        )
        filepath.unlink()
        if tmp_path.exists():
            tmp_path.unlink()

    return filepath, tmp_path, False


def format_bytes(num_bytes: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(num_bytes)
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PiB"


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "unknown"

    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def resolve_progress_mode(progress_mode: str) -> str:
    if progress_mode == "tqdm" and tqdm is None:
        return "line"
    if progress_mode != "auto":
        return progress_mode
    return "tqdm" if tqdm is not None and sys.stdout.isatty() else "line"


class LineProgressReporter:
    def __init__(
        self,
        filename: str,
        total_size: int | None,
        initial_size: int = 0,
        interval_seconds: float = 5.0,
    ):
        self.filename = filename
        self.total_size = total_size if total_size and total_size > 0 else None
        self.current_size = initial_size
        self.initial_size = initial_size
        self.interval_seconds = max(interval_seconds, 0.2)
        self.started_at = time.monotonic()
        self.last_report_at = 0.0
        self.speed_window_seconds = max(
            PROGRESS_SPEED_WINDOW_SECONDS,
            self.interval_seconds * 2.0,
        )
        self.samples = deque([(self.started_at, self.current_size)], maxlen=256)

    def update(self, bytes_written: int) -> None:
        self.current_size += bytes_written
        now = time.monotonic()
        if now - self.last_report_at >= self.interval_seconds:
            self.report()

    def set_current_size(self, current_size: int) -> None:
        self.current_size = max(current_size, self.initial_size)

    def _calculate_speed(self, now: float) -> float:
        self.samples.append((now, self.current_size))
        cutoff = now - self.speed_window_seconds
        while len(self.samples) > 2 and self.samples[0][0] < cutoff:
            self.samples.popleft()

        if len(self.samples) >= 2:
            oldest_time, oldest_size = self.samples[0]
            newest_time, newest_size = self.samples[-1]
            window_elapsed = max(newest_time - oldest_time, 1e-6)
            window_bytes = max(newest_size - oldest_size, 0)
            if window_bytes > 0:
                return window_bytes / window_elapsed

        elapsed = max(now - self.started_at, 1e-6)
        return max(self.current_size - self.initial_size, 0) / elapsed

    def report(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last_report_at < self.interval_seconds:
            return

        downloaded = self.current_size
        speed = self._calculate_speed(now)

        if self.total_size:
            percent = min(100.0, (downloaded / self.total_size) * 100.0)
            remaining = max(self.total_size - downloaded, 0)
            eta = remaining / speed if speed > 0 else None
            message = (
                f"Download progress: {self.filename} | {percent:5.1f}% "
                f"({format_bytes(downloaded)} / {format_bytes(self.total_size)}) "
                f"| {format_bytes(speed)}/s | ETA {format_duration(eta)}"
            )
        else:
            message = (
                f"Download progress: {self.filename} | "
                f"{format_bytes(downloaded)} downloaded | {format_bytes(speed)}/s"
            )

        print(message, flush=True)
        self.last_report_at = now


def progress_stream():
    try:
        return open("/dev/tty", "w", encoding="utf-8", buffering=1)
    except OSError:
        return sys.stdout


def aria2_control_path(target_path: Path) -> Path:
    return Path(f"{target_path}.aria2")


def choose_download_plan(
    requested_backend: str,
    total_size: int | None,
    supports_range_requests: bool,
    tmp_path: Path,
) -> DownloadPlan:
    if requested_backend == "requests":
        return DownloadPlan("requests", "requests backend forced by CLI.")

    aria2_path = shutil.which("aria2c")
    if not aria2_path:
        if requested_backend == "aria2c":
            raise DownloadError(
                "aria2c backend was requested, but aria2c is not installed on this device."
            )
        return DownloadPlan("requests", "aria2c is not installed; falling back to requests.")

    if not supports_range_requests or not total_size:
        if requested_backend == "aria2c":
            raise DownloadError(
                "aria2c backend was requested, but the server does not expose a parallelizable byte-range download."
            )
        return DownloadPlan(
            "requests",
            "Server does not advertise ranged downloads; falling back to requests.",
        )

    if tmp_path.exists() and not aria2_control_path(tmp_path).exists():
        partial_size = tmp_path.stat().st_size
        restart_budget = min(
            int(total_size * LEGACY_PARTIAL_RESTART_FRACTION),
            LEGACY_PARTIAL_RESTART_MAX_BYTES,
        )
        if partial_size > 0 and partial_size <= restart_budget:
            return DownloadPlan(
                "aria2c",
                (
                    "Discarding a small legacy partial download to switch to faster "
                    "aria2c multi-connection mode."
                ),
                restart_partial=True,
            )

        if requested_backend == "aria2c":
            raise DownloadError(
                "A legacy partial download already exists without aria2 control metadata. "
                "Delete the .part file to force a fresh aria2c download."
            )

        return DownloadPlan(
            "requests",
            (
                "Existing partial download was created by the legacy backend; "
                "preserving resume support with requests."
            ),
        )

    return DownloadPlan(
        "aria2c",
        f"Using aria2c multi-connection mode via {aria2_path}.",
    )


def download_file_with_aria2c(
    url: str,
    filepath: Path,
    filename: str,
    total_size: int,
    progress_interval: float,
    aria2_split: int,
    aria2_max_connection_per_server: int,
    aria2_min_split_size: str,
    headers: dict[str, str] | None = None,
) -> None:
    tmp_path = filepath.with_suffix(filepath.suffix + ".part")
    control_path = aria2_control_path(tmp_path)
    initial_size = tmp_path.stat().st_size if tmp_path.exists() else 0
    reporter = LineProgressReporter(
        filename=filename,
        total_size=total_size,
        initial_size=initial_size,
        interval_seconds=progress_interval,
    )

    command = [
        "aria2c",
        "--continue=true",
        "--auto-file-renaming=false",
        "--allow-overwrite=false",
        "--file-allocation=none",
        f"--split={max(1, aria2_split)}",
        f"--max-connection-per-server={max(1, aria2_max_connection_per_server)}",
        f"--min-split-size={aria2_min_split_size}",
        "--summary-interval=0",
        "--download-result=hide",
        "--console-log-level=warn",
        "--dir",
        str(filepath.parent),
        "--out",
        tmp_path.name,
    ]
    if headers:
        for header_name, header_value in headers.items():
            if header_value:
                command.extend(["--header", f"{header_name}: {header_value}"])
    command.append(url)

    process = None
    with tempfile.NamedTemporaryFile(
        prefix="aria2c-nvblox-",
        suffix=".log",
        delete=False,
        mode="w",
        encoding="utf-8",
    ) as log_handle:
        log_path = Path(log_handle.name)
        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

    try:
        reporter.report(force=True)
        while process and process.poll() is None:
            current_size = tmp_path.stat().st_size if tmp_path.exists() else initial_size
            reporter.set_current_size(current_size)
            reporter.report()
            time.sleep(min(max(progress_interval, 0.2), 1.0))

        reporter.set_current_size(tmp_path.stat().st_size if tmp_path.exists() else initial_size)
        reporter.report(force=True)

        if not process:
            raise DownloadError("aria2c process did not start.")

        if process.returncode != 0:
            log_tail = ""
            if log_path.exists():
                log_tail = "\n".join(
                    log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-10:]
                )
            raise DownloadError(
                "aria2c download failed"
                f" (exit code {process.returncode})."
                + (f" Last log lines:\n{log_tail}" if log_tail else "")
            )

        if not tmp_path.exists():
            raise DownloadError("aria2c finished without producing the target file.")

        written = tmp_path.stat().st_size
        if written < MIN_VALID_SIZE:
            tmp_path.unlink(missing_ok=True)
            raise DownloadError(
                f"Downloaded file is unexpectedly small after aria2c: {written} bytes."
            )

        tmp_path.replace(filepath)
        control_path.unlink(missing_ok=True)
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        log_path.unlink(missing_ok=True)


def download_file_with_requests(
    url: str,
    filepath: Path,
    filename: str,
    progress_mode: str = "auto",
    progress_interval: float = 5.0,
) -> None:
    tmp_path = filepath.with_suffix(filepath.suffix + ".part")
    resolved_progress_mode = resolve_progress_mode(progress_mode)

    while True:
        resume_pos = tmp_path.stat().st_size if tmp_path.exists() else 0
        headers = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"
            print(f"Resuming download from byte {resume_pos}", flush=True)

        try:
            response = requests.get(
                url,
                stream=True,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                headers=headers,
            )
        except requests.RequestException as exc:
            raise DownloadError(f"Failed to start download: {exc}") from exc

        try:
            if resume_pos > 0 and response.status_code == 200:
                print(
                    "Server ignored the resume request, restarting from byte 0.",
                    flush=True,
                )
                response.close()
                tmp_path.unlink(missing_ok=True)
                continue

            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0) or 0)
            if total_size and resume_pos:
                total_size += resume_pos

            chunks = response.iter_content(chunk_size=CHUNK_SIZE)
            first_chunk = next((chunk for chunk in chunks if chunk), b"")
            if not first_chunk:
                raise DownloadError("Downloaded content is empty.")

            if resume_pos == 0 and looks_like_landing_page(
                response.headers.get("content-type", ""), first_chunk
            ):
                raise DownloadError(
                    "The link resolved to an HTML/text page instead of a downloadable file."
                )

            written = resume_pos + len(first_chunk)
            mode = "ab" if resume_pos > 0 else "wb"

            if resolved_progress_mode == "tqdm":
                progress_file = progress_stream()
                progress_bar = tqdm(
                    desc=filename,
                    initial=resume_pos,
                    total=total_size if total_size > 0 else None,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    file=progress_file,
                    dynamic_ncols=True,
                    ascii=True,
                    leave=False,
                    mininterval=0.2,
                    smoothing=0.1,
                )
                try:
                    with open(tmp_path, mode) as handle:
                        handle.write(first_chunk)
                        progress_bar.update(len(first_chunk))

                        for chunk in chunks:
                            if not chunk:
                                continue
                            handle.write(chunk)
                            written += len(chunk)
                            progress_bar.update(len(chunk))
                finally:
                    progress_bar.close()
                    if progress_file not in (sys.stdout, sys.stderr):
                        progress_file.write("\n")
                        progress_file.close()
            else:
                reporter = LineProgressReporter(
                    filename=filename,
                    total_size=total_size if total_size > 0 else None,
                    initial_size=resume_pos,
                    interval_seconds=progress_interval,
                )
                reporter.report(force=True)
                with open(tmp_path, mode) as handle:
                    handle.write(first_chunk)
                    reporter.update(len(first_chunk))

                    for chunk in chunks:
                        if not chunk:
                            continue
                        handle.write(chunk)
                        written += len(chunk)
                        reporter.update(len(chunk))
                reporter.report(force=True)

            if written < MIN_VALID_SIZE:
                tmp_path.unlink(missing_ok=True)
                raise DownloadError(
                    f"Downloaded file is unexpectedly small: {written} bytes."
                )

            tmp_path.replace(filepath)
            return
        except requests.RequestException as exc:
            raise DownloadError(
                f"Download interrupted by a network/protocol error: {exc}"
            ) from exc
        finally:
            response.close()


def download_file(
    url: str,
    filepath: Path,
    filename: str,
    progress_mode: str = "auto",
    progress_interval: float = 5.0,
    backend: str = DEFAULT_BACKEND,
    total_size: int | None = None,
    supports_range_requests: bool = False,
    aria2_split: int = DEFAULT_ARIA2_SPLIT,
    aria2_max_connection_per_server: int = DEFAULT_ARIA2_MAX_CONNECTION_PER_SERVER,
    aria2_min_split_size: str = DEFAULT_ARIA2_MIN_SPLIT_SIZE,
    resolved_url: str | None = None,
    share_url: str | None = None,
    aria2_headers: dict[str, str] | None = None,
) -> None:
    tmp_path = filepath.with_suffix(filepath.suffix + ".part")
    plan = choose_download_plan(
        requested_backend=backend,
        total_size=total_size,
        supports_range_requests=supports_range_requests,
        tmp_path=tmp_path,
    )

    print(plan.reason, flush=True)

    if plan.restart_partial:
        print(f"Removing legacy partial file: {tmp_path}", flush=True)
        tmp_path.unlink(missing_ok=True)
        aria2_control_path(tmp_path).unlink(missing_ok=True)

    if plan.backend == "aria2c":
        aria2_url = resolved_url or share_url or url
        try:
            download_file_with_aria2c(
                url=aria2_url,
                filepath=filepath,
                filename=filename,
                total_size=total_size or 0,
                progress_interval=progress_interval,
                aria2_split=aria2_split,
                aria2_max_connection_per_server=aria2_max_connection_per_server,
                aria2_min_split_size=aria2_min_split_size,
                headers=aria2_headers,
            )
            return
        except DownloadError as exc:
            if backend == "aria2c":
                raise
            print(
                "aria2c acceleration failed; falling back to the built-in requests downloader. "
                f"Reason: {exc}",
                flush=True,
            )
            tmp_path.unlink(missing_ok=True)
            aria2_control_path(tmp_path).unlink(missing_ok=True)

    download_file_with_requests(
        url=url,
        filepath=filepath,
        filename=filename,
        progress_mode=progress_mode,
        progress_interval=progress_interval,
    )


def main() -> int:
    args = parse_args()

    try:
        validated_url = validate_source_url(args.share_url)
        normalized_url = with_download_flag(validated_url)
        output_dir = args.output_dir.expanduser()

        filename_override = sanitize_filename(args.filename or args.legacy_filename)
        if (args.filename or args.legacy_filename) and not filename_override:
            raise DownloadError("Invalid filename value.")

        print(f"Resolving download target: {normalized_url}", flush=True)
        probe = probe_remote_target(
            normalized_url, filename_override
        )
        filename = filename_override or probe.filename or DEFAULT_FILENAME

        filepath, _tmp_path, already_exists = prepare_target_paths(
            output_dir, filename, args.force
        )
        if already_exists:
            return 0

        if probe.resolved_url != normalized_url:
            print(f"Resolved file URL: {probe.resolved_url}", flush=True)

        print(f"Download URL: {normalized_url}", flush=True)
        print(f"Saving to: {filepath}", flush=True)
        if probe.total_size:
            print(f"Remote size: {format_bytes(probe.total_size)}", flush=True)
        print(
            "Range support: "
            + ("enabled" if probe.supports_range_requests else "not advertised"),
            flush=True,
        )

        if args.aria2c:
            print(
                " ".join(
                    [
                        "aria2c",
                        f"--split={max(1, args.aria2_split)}",
                        f"--max-connection-per-server={max(1, args.aria2_max_connection_per_server)}",
                        f"--min-split-size={args.aria2_min_split_size}",
                        f"'{normalized_url}'",
                        f"-d '{output_dir}'",
                        f"-o '{filename}'",
                    ]
                ),
                flush=True,
            )
            return 0

        download_file(
            normalized_url,
            filepath,
            filename,
            progress_mode=args.progress_mode,
            progress_interval=args.progress_interval,
            backend=args.backend,
            total_size=probe.total_size,
            supports_range_requests=probe.supports_range_requests,
            aria2_split=args.aria2_split,
            aria2_max_connection_per_server=args.aria2_max_connection_per_server,
            aria2_min_split_size=args.aria2_min_split_size,
            resolved_url=probe.resolved_url,
            share_url=normalized_url,
            aria2_headers={"Cookie": probe.cookie_header} if probe.cookie_header else None,
        )
        print(f"Download complete: {filepath}", flush=True)
        return 0
    except DownloadError as exc:
        print(f"Error: {exc}", flush=True)
        return 1
    except OSError as exc:
        print(f"Error: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
