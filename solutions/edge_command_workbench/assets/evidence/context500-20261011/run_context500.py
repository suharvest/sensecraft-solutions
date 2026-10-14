#!/usr/bin/env python3
"""Run the frozen 120-case context-500 corpus in original/reverse order."""
from __future__ import annotations
import argparse, hashlib, json, math, statistics, time, urllib.error, urllib.request
from pathlib import Path

def digest(obj: object) -> str:
    value = hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(); assert len(value) == 64; return value

def file_sha(path: Path) -> str:
    value = hashlib.sha256(path.read_bytes()).hexdigest(); assert len(value) == 64; return value

def stats(rows: list[float]) -> dict | None:
    if not rows: return None
    ordered = sorted(rows); p95 = ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]
    return {"n": len(rows), "mean_ms": statistics.fmean(rows), "min_ms": min(rows), "p50_ms": statistics.median(rows), "p95_ms": p95, "max_ms": max(rows)}

def timing_complete(t: object) -> bool:
    return isinstance(t, dict) and all(isinstance(t.get(k), (int, float)) and math.isfinite(float(t[k])) for k in ("encoding_ms", "inference_ms", "total_ms"))

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--base-url", default="http://127.0.0.1:18771/api/decide"); ap.add_argument("--dataset", required=True); ap.add_argument("--out", required=True); ap.add_argument("--timeout", type=float, default=180.0); ap.add_argument("--warmup", type=int, default=5); args = ap.parse_args()
    dataset_path = Path(args.dataset); out_path = Path(args.out); meta_path = dataset_path.with_name("context500-metadata.json")
    rows = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 120 or len({r["id"] for r in rows}) != 120: raise SystemExit("dataset must contain exactly 120 unique cases")
    source_sha = file_sha(dataset_path); metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    for key in ("dataset_sha256", "source_cases_sha256", "tokenizer_sha256", "kev_codec_source_sha256", "generator_sha256", "runner_sha256"):
        if not isinstance(metadata.get(key), str) or len(metadata[key]) != 64: raise SystemExit(f"metadata {key} must be a 64-char SHA256")
    if metadata["dataset_sha256"] != source_sha: raise SystemExit("dataset SHA does not match metadata; refusing resume")
    expected: dict[tuple[str, str], tuple[dict, str]] = {}
    for row in rows:
        expected[("original", row["id"])] = (row, row["request_500_sha256"])
        expected[("reverse", row["id"])] = (row, row["reverse_request_500_sha256"])
    completed: set[tuple[str, str]] = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            rec = json.loads(line); key = (rec.get("pass"), rec.get("id"))
            if key not in expected: raise SystemExit(f"unknown existing case: {key}")
            if key in completed: raise SystemExit(f"duplicate existing case: {key}")
            row, request_sha = expected[key]
            if rec.get("dataset_sha256") != source_sha or rec.get("request_sha256") != request_sha or rec.get("assembled_tokens") != 500: raise SystemExit(f"existing row hash/invariant mismatch: {key}")
            completed.add(key)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    def call(body: dict) -> tuple[dict | None, int, float, str | None]:
        req = urllib.request.Request(args.base_url, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"}); started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as response: return json.loads(response.read()), response.status, (time.perf_counter() - started) * 1000, None
        except urllib.error.HTTPError as exc: return None, exc.code, (time.perf_counter() - started) * 1000, exc.read().decode(errors="replace")
        except Exception as exc: return None, 0, (time.perf_counter() - started) * 1000, repr(exc)
    warmups = []; warm_body = rows[0]["request_500"]
    for i in range(args.warmup):
        data, status, elapsed, error = call(warm_body); warmups.append({"index": i, "status": status, "client_elapsed_ms": elapsed, "error": error, "server_timings": (data or {}).get("timings") if isinstance(data, dict) else None})
        if status != 200 or not isinstance(data, dict): raise SystemExit(f"warmup failed at index {i}: status={status} error={error}")
    with out_path.open("a", encoding="utf-8") as handle:
        for pass_name, field in (("original", "request_500"), ("reverse", "reverse_request_500")):
            for row in rows:
                key = (pass_name, row["id"])
                if key in completed: continue
                body = row[field]; request_sha = digest(body)
                if request_sha != expected[key][1] or row["assembled_tokens"] != 500 or row["reverse_assembled_tokens"] != 500: raise SystemExit(f"dataset request invariant failed: {key}")
                data, status, client_ms, error = call(body); server = (data or {}).get("timings") if isinstance(data, dict) else None; selected = (data or {}).get("selected_option_id") if isinstance(data, dict) else None
                rec = {"dataset_sha256": source_sha, "pass": pass_name, "id": row["id"], "language": row["language"], "category": row["category"], "expected_id": row["expected_id"], "selected_option_id": selected, "correct": bool(status == 200 and selected == row["expected_id"]), "status": status, "error": error, "assembled_tokens": 500, "request_sha256": request_sha, "client_elapsed_ms": client_ms, "server_timings": server, "model": (data or {}).get("model") if isinstance(data, dict) else None}
                handle.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"); handle.flush(); completed.add(key); print(json.dumps({"pass": pass_name, "id": row["id"], "status": status, "correct": rec["correct"], "client_elapsed_ms": client_ms}, ensure_ascii=False), flush=True)
    result_rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(result_rows) != 240 or len({(r.get("pass"), r.get("id")) for r in result_rows}) != 240: raise SystemExit("result must contain exactly 240 unique scored rows")
    http_success = [r for r in result_rows if r.get("status") == 200]; complete = [r for r in http_success if timing_complete(r.get("server_timings"))]; missing = [r for r in http_success if not timing_complete(r.get("server_timings"))]
    client = [float(r["client_elapsed_ms"]) for r in http_success]; server_encoding = [float(r["server_timings"]["encoding_ms"]) for r in complete]; server_total = [float(r["server_timings"]["total_ms"]) for r in complete]; server_infer = [float(r["server_timings"]["inference_ms"]) for r in complete]
    def partition(field, value): return [r for r in result_rows if r[field] == value]
    def part_summary(sub): return {"rows": len(sub), "success": sum(r["status"] == 200 for r in sub), "errors": sum(r["status"] != 200 for r in sub), "correct": sum(r["correct"] for r in sub), "accuracy_over_rows": sum(r["correct"] for r in sub) / len(sub) if sub else None}
    summary = {"dataset_sha256": source_sha, "base_url": args.base_url, "timeout_seconds": args.timeout, "warmup_count": args.warmup, "warmups": warmups, "scored_total": 240, "success_count": len(http_success), "error_count": 240 - len(http_success), "timings_complete_count": len(complete), "timings_missing_count": len(missing), "correct_count": sum(r["correct"] for r in result_rows), "accuracy_over_240_rows": sum(r["correct"] for r in result_rows) / 240, "client_e2e_ms_success": stats(client), "server_encoding_ms_success": stats(server_encoding), "server_total_ms_success": stats(server_total), "server_inference_ms_success": stats(server_infer), "by_pass": {p: part_summary(partition("pass", p)) for p in ("original", "reverse")}, "by_language": {p: part_summary(partition("language", p)) for p in sorted({r["language"] for r in result_rows})}, "by_category": {p: part_summary(partition("category", p)) for p in sorted({r["category"] for r in result_rows})}, "errors": [{k: r[k] for k in ("pass", "id", "language", "category", "status", "error")} for r in result_rows if r["status"] != 200], "wrong_predictions": [{k: r[k] for k in ("pass", "id", "language", "category", "expected_id", "selected_option_id", "status")} for r in result_rows if r["status"] == 200 and not r["correct"]], "raw_jsonl": str(out_path), "request_contract": "expected/gold fields are excluded from HTTP body; each request contains input_text,prompt,options only", "cache_contract": "service-side Kev infer clears RKLLM KV cache per request and keep_history=0; runner sends sequential requests without retries", "synthetic_context": "fixed natural documentation metadata sentences appended to original prompt; exact assembled token count 500, not a natural long-task accuracy claim"}
    summary_path = out_path.with_suffix(".summary.json"); summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n"); print(json.dumps(summary, ensure_ascii=False, indent=2))
if __name__ == "__main__": main()
