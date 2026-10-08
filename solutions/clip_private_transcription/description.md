# Private Clip Transcription

> **Draft.** M7/M8 software gates and a local wheel exist, but no
> physical Clip/BLE/Wi-Fi or host acceptance has passed. The clip-pt image,
> the Jetson OVS image, and the Jetson ASR model bundle are published
> (2026-10-08); RK SLV artifacts and model licenses are not supplied.

The intended flow synchronizes recordings locally, performs diarization and
ASR through local services, and exposes transcript results through an
authenticated HTTP API and MQTT. LLM requests use the shared OpenAI-compatible
endpoint fields in the config (`base_url`, `model_name`, `api_key`, `timeout_s`).
The endpoint may be a cloud service or a user-managed RK1828/Jetson service; no
No LLM runtime is deployed by this package. Recordings are processed and stored locally; when cloud summarization is selected, transcript text is sent to the configured endpoint. A local RK1828 or Jetson endpoint can keep that processing on site.
The package does not claim Voice PE, BLE, AP, MT7921, or offline E2E evidence.
