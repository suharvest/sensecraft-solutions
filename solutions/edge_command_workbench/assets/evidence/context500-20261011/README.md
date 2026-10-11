# Kev context-500 benchmark

This benchmark measures the Kev RKLLM command-selection path with a fixed assembled context of exactly 500 tokens. It extends each frozen semantic request with fixed, neutral synthetic industrial-document metadata sentences. The added text does not describe an action, device state, sensor state, or operating condition, and the original input, prompt meaning, candidates, expected label, language, and category remain unchanged. The extension is a length-control method; it is not a claim about accuracy on naturally occurring long tasks. The 500-token count covers the complete Kev assembly: official delimiters, input, prompt/context, and every option. The service returns a selected option ID; this benchmark is not text generation and does not report tokens/second.

The corpus contains 120 language samples arranged as 60 paired English/Chinese semantic groups across direct, paraphrase, negation, ambiguous, and out-of-scope categories. Each language sample is sent twice, with the original option order and with the option order reversed, for 240 scored requests per device. Five warmup requests are sent before scoring and are excluded from the 240-request denominator. A warmup failure stops the run. Candidate counts in the frozen corpus are 4 options for 22 cases, 5 for 20 cases, 6 for 52 cases, and 7 for 26 cases (range 4–7; the runtime limit of 16 is not the dataset candidate count). Baseline assembled contexts range from 71 to 110 tokens. `clarify` and `reject` each have 20 semantic cases, hence 40 requests per label after both order passes.

## Reproducible inputs

- [`context500-cases.jsonl`](context500-cases.jsonl) contains the request bodies, expected labels, order variants, exact token counts, and per-request SHA256 values. Expected fields are metadata and are not sent in the HTTP body.
- [`context500-metadata.json`](context500-metadata.json) records the frozen source corpus SHA, deployed tokenizer SHA, Kev codec source SHA, delimiter IDs, target length, and generator/runner hashes.
- [`tokenizer.fe000.json`](tokenizer.fe000.json) is the tokenizer copied from the deployed Radxa release and verified as SHA256 `fe000e3ed39ed12b8d2481d527d44f93c65d37e87645d2dcc80d1bf9d50d2927`.
- [`generate_context500.py`](generate_context500.py) calls the application `KevCodec.encode` for every generated request and rejects any mismatch with its independent token-count check.
- [`run_context500.py`](run_context500.py) runs sequential loopback HTTP requests, supports hash-checked resume, performs no automatic retry, and writes one raw JSONL record per scored request plus a generated summary.

The deployed image, model, tokenizer, runtime, and Hugging Face revision must be recorded with each device result. The release pin and artifact evidence are maintained in the corresponding release evidence directory; this benchmark does not download or replace deployment artifacts.

## Completed device results

Both stable-v2 device runs completed with exit code 0. Each run sent 240 scored requests: 60 paired English/Chinese semantic groups provide 120 language samples, and each sample was sent with original and reversed option order. Accuracy is exact `selected_option_id` match; it is not HTTP success rate or a safety certification. False-action means an incorrect selection of an execution candidate for an expected `clarify` or `reject`; this benchmark sent decision requests and did not execute industrial commands.

| device | model identity | HTTP | correct | accuracy | original | reverse | English | Chinese |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RK3576 | `kev`, `rkllm`, W4A16 g128, max 2048 | 240/240 | 189/240 | 78.75% | 95/120 | 94/120 | 93/120 | 96/120 |
| RK3588 | `kev`, `rkllm`, W8A8, max 8192 | 240/240 | 189/240 | 78.75% | 92/120 | 97/120 | 94/120 | 95/120 |

Category accuracy is: RK3576 direct 80/80, paraphrase 39/40, negation 37/40, ambiguous 14/40, out-of-scope 19/40; RK3588 direct 80/80, paraphrase 38/40, negation 38/40, ambiguous 12/40, out-of-scope 21/40. False-action rates are RK3576 `clarify` 16/40 (40.00%) and `reject` 3/40 (7.50%); RK3588 `clarify` 22/40 (55.00%) and `reject` 2/40 (5.00%). Invalid selected IDs were zero on both devices. Reversing options changed selected ID in 5/120 RK3576 pairs and 9/120 RK3588 pairs; correctness changed in 3 and 5 pairs respectively.

| device | timing | n | mean ms | min ms | p50 ms | p95 ms | max ms |
|---|---|---:|---:|---:|---:|---:|---:|
| RK3576 | client end-to-end | 240 | 7220.982 | 7067.254 | 7115.307 | 7574.560 | 7773.237 |
| RK3576 | server inference | 240 | 7217.131 | 7063.492 | 7111.639 | 7570.440 | 7769.592 |
| RK3576 | server total | 240 | 7217.305 | 7063.657 | 7111.868 | 7570.654 | 7769.754 |
| RK3588 | client end-to-end | 240 | 3958.615 | 3479.071 | 3946.517 | 4770.961 | 5371.268 |
| RK3588 | server inference | 240 | 3955.264 | 3475.535 | 3943.280 | 4767.696 | 5368.083 |
| RK3588 | server total | 240 | 3955.432 | 3475.699 | 3943.448 | 4767.862 | 5368.251 |

p50 is the median; p95 uses the nearest-rank index `ceil(0.95*n)`. All 480 scored responses had complete timing objects and zero HTTP errors. `encoding_ms` is emitted as `0.0` by the current Kev native instrumentation; it is not measured tokenizer wall time and is not a claim of zero-cost encoding. KevCodec encoding, RKLLM hidden-state inference, and FP32 head scoring occur inside the measured inference path. The two boards use different chip, quantization, and deployment context-guard configurations; these results do not isolate quantization as the cause of any difference.

The runtime/model identity observed in the responses was `model_id=kev`, `backend=rkllm`, `model_ready=true`; both engines were exported for 8K context, while deployment caps were RK3576 `max_sequence_tokens=2048` and RK3588 `8192`, with `max_options=16`. The recorded quantization modes are RK3576 Kev W4A16 g128 and RK3588 Kev W8A8. Both runs reuse image `edge-command-workbench:rockchip-rkllm-0.3.1-review` and Hugging Face revision `db0545065d4da3598d009407fc3bd0c7632ca199` from the existing release evidence ([RK3576 release evidence](../../../docs/interaction-review-ef82-20261011/rk3576-final-release/), [RK3588 release evidence](../../../docs/interaction-review-ef82-20261011/rk3588-final-release/)); this benchmark report does not claim a second artifact revalidation. The benchmark tokenizer and Kev codec hashes remain in [`context500-metadata.json`](context500-metadata.json).

Evidence is linked by device: [RK3576 raw results](rk3576/stable-v2/results-v2.jsonl), [RK3576 summary](rk3576/stable-v2/results-v2.summary.json), [RK3576 analysis](rk3576/stable-v2/analysis.json), [RK3576 exit](rk3576/stable-v2/results-v2.exit), [RK3588 raw results](rk3588/stable-v2/results-v2.jsonl), [RK3588 summary](rk3588/stable-v2/results-v2.summary.json), [RK3588 analysis](rk3588/stable-v2/analysis.json), [RK3588 exit](rk3588/stable-v2/results-v2.exit). SHA256 values are: RK3576 results `7ed7869b43e562ae31ebc9d2c0a4fa72cf1a73a65066f93bd0525cc12e049f7f`, summary `2f687c7366d5ae09078ab9899757b9e3dc92a11e5b180a816348b70041647463`, analysis `aa1a66773f969f70eea9fa91c11bee9243163aac743a3d715af92eda0f44f544`; RK3588 results `5b49681b5e093202d9b184ac2fb94e471bde503669ba07c1f9573f665a73e782`, summary `fa0a3dbaed58a2c94f818bc4ee67a4007b6f47b956bd1dfe3829f986ada6cf5f`, analysis `86d64fce7b14988c77d7a78582456002a0dec20b3e91688d4ec61f47890e1e4a`. Both datasets match `e9d77a3c96a1d0645bc9561cdf9ead06cbd57d8ef081906c2d5094d55e54ba6e`.

Runner reproduction uses the standard library plus the frozen dataset and metadata; it does not require `app/` or the tokenizer fixture: `uv run --no-project python experiments/jev-20261011/context500/run_context500.py --dataset experiments/jev-20261011/context500/context500-cases.jsonl --out /tmp/context500-results.jsonl --timeout 120 --warmup 5 --base-url http://127.0.0.1:18771/api/decide`. Run this loopback example on the cat device; use port `18768` for Radxa. If running from Spark or Mac against a device IP, client timing includes LAN time and is not directly comparable with the loopback table. Generator reproduction additionally requires the complete source checkout, application package, and tokenizer fixture; the small delivery copy contains result evidence only.

## Measurement scope

Client elapsed time is measured around each loopback HTTP request. Server timing fields are reported separately as `encoding_ms`, `inference_ms`, and `total_ms`. The summary reports `n`, mean, minimum, p50, p95, and maximum for client end-to-end timing and for each available server timing field. HTTP errors, timeouts, and responses missing any server timing field are listed separately; missing timing data is not treated as a zero.

Accuracy is reported over the same 240 scored requests used for performance: overall, by language, by category, and by option-order pass. The summary includes the complete error list and the `wrong_predictions` list for HTTP 200 responses whose selected option differs from the expected label. The five warmups are not part of either accuracy or performance denominators. The service clears its KV cache for each request and does not share request history; the runner sends requests serially.

The completed raw per-request JSONL, generated summaries, analyses, exit codes, and artifact/hash evidence are stored under `rk3576/` and `rk3588/`. The report records the measured results above; the small delivery copy contains result evidence and omits the 12.8 MB tokenizer fixture.
