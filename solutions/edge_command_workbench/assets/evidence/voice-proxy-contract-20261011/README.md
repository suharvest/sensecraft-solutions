# Voice proxy contract test evidence

- Test commit: `1ca14e4e62a20d61c6781e2a384f98ca36995c5c` (`test: cover optional voice proxy contract`).
- `pytest-voice-proxy.log`: 4 voice proxy contract tests passed.
- `pytest-full-suite.log`: full app suite passed, 43 tests.
- The fake ASR is a controlled protocol peer. It verifies URL selection, HTTP-to-WebSocket target mapping, binary PCM and empty end-frame forwarding, JSON transcript forwarding, and upstream failure handling.
- This evidence does not test a physical microphone, a real ASR service, an NPU runtime, or model accuracy.
- The tests do not change product runtime code or image contents.
