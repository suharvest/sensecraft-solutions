# weather_classification_recamera — RTSP + MQTT patch

> **STATUS: applied and validated on real hardware** (recamera@10.8.0.194, 2026-07-20).
> Cross-compiled clean against reCamera-OS SDK 0.2.2 + `sophgo/host-tools`'
> `riscv64-linux-musl-x86_64` toolchain. `opkg install`, RTSP (`ffprobe`-confirmed H.264
> 1280x720@15fps at `rtsp://<ip>:8554/live0`) and MQTT (`recamera/weather/results`, JSON
> matches the schema below) all verified end-to-end. See
> `packages/WEATHER_BUILD_NOTES.md` for the current artifact status.
>
> **One correction vs. the original assumption below**: `cvi_rtsp` (the prebuilt SDK
> component) only provides the low-level `CVI_RTSP_*` API (`rtsp.h`) — it does **not**
> implement `initRtsp()`/`deinitRtsp()`/`fpStreamingSendToRtsp()` themselves. Those wrapper
> functions had to be vendored as a `main/rtsp_demo.c` file (not just the `.h` declared
> below), copied verbatim from `sscma-example-sg200x`'s own `solutions/video_demo/main/rtsp_demo.c`
> — its exact content is appended after the `rtsp_demo.h` section. Add it to `main/CMakeLists.txt`'s
> `SRCS` alongside `main.cpp`/`mqtt_publisher.cpp`.

Reference patch to turn the stdout-only weather classifier into a self-contained
RTSP+MQTT binary, following the same architecture as the sibling reCamera apps
(`yolo-detector`, `face-analysis`, `detection-blur`, etc.) in
`sscma-example-sg200x/solutions/`. Apply this on top of
https://github.com/yyling0101-a11y/weather_classification_recamera and cross-compile
inside the SG200X SDK tree (`SG200X_SDK_PATH` + `riscv64-linux-musl-x86_64` toolchain —
not available in this session, so this patch is not compiled here).

## Confirmed vs. inferred

**Confirmed from actual source** (fetched 2026-07-20 via `raw.githubusercontent.com` for
the upstream repo, and via a shallow `git clone` of
`https://github.com/suharvest/sscma-example-sg200x` — a fork of
`Seeed-Studio/sscma-example-sg200x` — for the sibling apps):

- Upstream `weather_classification_recamera`: full contents of `main/main.cpp` (369
  lines), `main/engine_utils.h` (161 lines), `main/CMakeLists.txt`, root `CMakeLists.txt`,
  `labels.txt`, `README.md`.
- Sibling apps' **RTSP mechanism**: it is **not** SSCMA-Micro's own `ma::Server`/
  `ma::Transport`/`ma::Stream` API, and **not** gstreamer/live555. It's the CVITEK/Sophgo
  vendor SDK's own venc+RTSP glue:
  - `components/sophgo/video/video.h` — `initVideo()`, `setupVideo(VIDEO_CH2, &param)`
    (configures an H.264 encode channel separate from the raw-frame inference channel),
    `registerVideoFrameHandler(VIDEO_CH2, 0, fpStreamingSendToRtsp, nullptr)`,
    `deinitVideo()`.
  - Each solution vendors its own copy of `rtsp_demo.h`, declaring
    `fpStreamingSendToRtsp()`, `initRtsp(uint8_t chEnableFlag)`, `deinitRtsp()` — a thin
    wrapper around CVITEK's own `cvi_rtsp` component (`rtsp.h`, `CVI_RTSP_*` types), linked
    via `PRIVATE_REQUIREDS ... cvi_rtsp ...` in each solution's `CMakeLists.txt`.
  - Verified byte-identical `rtsp_demo.h` across `yolo-detector`, `ppocr-reader`,
    `detection-blur` (and by naming convention the rest).
  - `yolo-detector/main/main.cpp` confirms the call sequence and the exact RTSP URL
    convention: `rtsp://<device_ip>:8554/live0` (stream port/path is fixed inside the SDK's
    `cvi_rtsp` component, not a CLI flag in any sibling app).
- Sibling apps' **MQTT client**: `libmosquitto` (`<mosquitto.h>`), confirmed via
  `yolo-detector/main/mqtt_publisher.{h,cpp}` (also present, structurally identical, in
  `face-analysis`, `detection-blur`, `ppocr-reader`, `retail-vision`, `facemesh-reader`):
  `mosquitto_lib_init()`, `mosquitto_new(client_id, true, this)`,
  `mosquitto_connect_callback_set()`, `mosquitto_disconnect_callback_set()`,
  `mosquitto_username_pw_set()` (if creds given), `mosquitto_reconnect_delay_set(2, 30,
  true)`, `mosquitto_loop_start()` (background network thread), `mosquitto_connect(host,
  port, 60)`, `mosquitto_publish(client, nullptr, topic, len, payload, qos, retain)`,
  `mosquitto_disconnect()`, `mosquitto_loop_stop()`, `mosquitto_destroy()`,
  `mosquitto_lib_cleanup()`.
- **CLI flag naming**: `yolo-detector/main/main.cpp` uses `getopt_long` with long options
  `--mqtt-host` / `--mqtt-port` (defaults `"localhost"` / `1883`), exactly matching what
  this task asks for.
- **MQTT topic convention**: every sibling app uses `recamera/<app-name>/<result-word>`
  (`recamera/yolo/detections`, `recamera/face-analysis/results`,
  `recamera/detection-blur/results`, `recamera/ppocr/texts`,
  `recamera/facemesh-reader/results`) — `recamera/weather/results` (as specified in the
  task, and already referenced as the default in this solution's own
  `devices/preview_weather.yaml`) fits this convention.
- `CMakeLists.txt` dependency line, confirmed from `yolo-detector/main/CMakeLists.txt` /
  `ppocr-reader/main/CMakeLists.txt`: `PRIVATE_REQUIREDS sscma-micro sophgo cvi_rtsp
  mosquitto debug_stream mongoose` (the last two — `debug_stream`/`mongoose` — are only for
  the optional supervisor-console WebSocket debug overlay, which this patch does **not**
  add; see "Not ported" below).
- This solution's own `devices/recamera_weather.yaml` action script writes
  `/etc/weather-classifier.conf` with keys `MQTT_HOST` / `MQTT_PORT` — **inferred** (not
  found in any sibling app source) that the `.deb`'s init script
  (`S92weather-classifier`) is expected to source that conf file and pass
  `--mqtt-host "$MQTT_HOST" --mqtt-port "$MQTT_PORT"` to the binary. Confirm/implement that
  glue when writing the init script (see checklist).

**Inferred / best-practice** (not found verbatim in sibling source, but consistent with
it):

- The exact JSON field layout for weather's classification payload — the sibling apps'
  JSON builders (`buildResultJson`/`buildTrackingJson`) are hand-rolled with
  `std::ostringstream`, no JSON library, no string escaping of label text (labels are
  trusted, come from a local `labels.txt`). This patch follows the same pattern, shaped to
  the exact schema requested in the task.
- Publishing MQTT unconditionally every successfully-classified frame (not gated by
  `print_interval`), matching `yolo-detector`'s `process_frame()`, which calls
  `publishResults`/`publishTrackingResults` every iteration regardless of its own
  `verbose` console-log gate.
- Stream resolution/fps for the RTSP H.264 channel (`1280x720@15fps`) — copied from
  `yolo-detector`'s defaults since no weather-specific figure exists upstream; adjust to
  taste.
- Log style: this patch keeps the upstream app's existing plain `printf`/`fprintf`
  `[TAG]`-prefixed style rather than switching to `MA_LOGI`/`MA_LOGE` (which sibling apps
  use) — purely cosmetic, does not affect behavior.

## Not ported (out of scope for this task)

- Debug WebSocket overlay stream (`debug_stream.h` + `mongoose`) used by
  `yolo-detector`/`face-analysis` to feed the supervisor's live console — not requested,
  not added. Drop `debug_stream mongoose` from `PRIVATE_REQUIREDS` if you don't need it
  (this patch already omits them).
- Hardware privacy blur (RGN COVEREX), person tracking/dwell-state, entry-line counting —
  YOLO/face-analysis-specific features, not applicable to a whole-frame classifier.

---

## File layout after patch

```
weather_classification/
├── CMakeLists.txt              # modified (root project file)
├── labels.txt                  # unchanged
├── README.md                   # unchanged (or update run example, see checklist)
└── main/
    ├── CMakeLists.txt          # modified (component_register)
    ├── main.cpp                 # modified (this file, in full, below)
    ├── engine_utils.h           # UNCHANGED — preprocessing/quantization untouched
    ├── rtsp_demo.h              # NEW — vendored verbatim from sibling apps
    ├── mqtt_publisher.h         # NEW
    └── mqtt_publisher.cpp       # NEW
```

`engine_utils.h` requires **no changes at all** — it is copied here only for confirmation
that nothing in it was touched (bf16/fp16 conversion, `InputBuf`, `store_val`/`read_val`,
`make_input_tensor` all remain byte-identical to upstream).

---

## `main/rtsp_demo.h` (NEW — vendor verbatim from any sibling app, e.g. `yolo-detector`)

```c
#ifndef __APP_IPCAM_RTSP_H__
#define __APP_IPCAM_RTSP_H__

#include "stdint.h"
#include "stdbool.h"
#include "stddef.h"
#include <pthread.h>
#include "cvi_type.h"
#include "linux/cvi_common.h"
#include "rtsp.h"

#ifdef __cplusplus
extern "C"
{
#endif

#define MAX_RTSP_SESSION     6

#define APP_RTSP_VCODEC_CHK(S_C,D_C) do {                   \
        if (S_C == PT_H265) D_C = RTSP_VIDEO_H265;          \
        else if (S_C == PT_H264) D_C = RTSP_VIDEO_H264;     \
        else if (S_C == PT_MJPEG) D_C = RTSP_VIDEO_JPEG;    \
        else {                                              \
            D_C = RTSP_VIDEO_NONE;                          \
            printf("\033[40;31m S_Codec(%d) not match D_Codec(%d) \033[0m\n", S_C, D_C);  \
            return CVI_FAILURE;                             \
        }                                                   \
} while(0)

typedef struct APP_PARAM_RTSP_S {
    CVI_S32 session_cnt;
    CVI_S32 port;
    CVI_BOOL bStart[MAX_RTSP_SESSION];
    VENC_CHN VencChn[MAX_RTSP_SESSION];
    CVI_RTSP_SESSION *pstSession[MAX_RTSP_SESSION];
    CVI_RTSP_SESSION_ATTR SessionAttr[MAX_RTSP_SESSION];
    CVI_RTSP_STATE_LISTENER listener;
    CVI_RTSP_CTX *pstServerCtx;
    pthread_mutex_t RsRtspMutex;
} APP_PARAM_RTSP_T;

int fpStreamingSendToRtsp(void* pData, void* pArgs, void *pUserData);
int initRtsp(uint8_t chEnableFlag);
int deinitRtsp(void);

#ifdef __cplusplus
}
#endif

#endif
```

**Correction (found during the real build): `initRtsp()`/`deinitRtsp()`/`fpStreamingSendToRtsp()`
are NOT implemented by the prebuilt `cvi_rtsp` library** — that component only exposes the
low-level `CVI_RTSP_Create`/`CVI_RTSP_CreateSession`/`CVI_RTSP_WriteFrame`/... API declared
in `rtsp.h`. The wrapper functions above must be vendored as `main/rtsp_demo.c`, copied
verbatim from `sscma-example-sg200x`'s own `solutions/video_demo/main/rtsp_demo.c` (confirmed
byte-compatible — same header, same call convention already used in `init_video_streaming()`
below):

```c
#include "app_ipcam_comm.h"
#include "app_ipcam_venc.h"
#include "rtsp_demo.h"

#define PARAM_CFG_INI "/mnt/data/param_config.ini"

APP_PARAM_RTSP_T stRtspCtx;
APP_PARAM_RTSP_T *pstRtspCtx = &stRtspCtx;

static int _Load_Param_Rtsp(void)
{
    APP_PARAM_RTSP_T *Rtsp = pstRtspCtx;

    Rtsp->session_cnt = 0;
    Rtsp->port = 8554;
    for (uint8_t i = 0; i < MAX_RTSP_SESSION; i++) {
        Rtsp->VencChn[i] = i;
        Rtsp->SessionAttr[i].video.bitrate = 30720;
    }

    return CVI_SUCCESS;
}

static int app_ipcam_RtspAttr_Init(void)
{
    /* update vidoe streaming codec type from video attr */
    for (CVI_S32 i = 0; i < pstRtspCtx->session_cnt; i++) {
        APP_PARAM_VENC_CTX_S* venc = app_ipcam_Venc_Param_Get();
        APP_VENC_CHN_CFG_S *pstVencChnCfg = &venc->astVencChnCfg[pstRtspCtx->VencChn[i]];
        PAYLOAD_TYPE_E enType = pstVencChnCfg->enType;
        APP_RTSP_VCODEC_CHK(enType, pstRtspCtx->SessionAttr[i].video.codec);
#ifdef AUDIO_SUPPORT
        APP_PARAM_AUDIO_CFG_T *pstAudioCfg = app_ipcam_Audio_Param_Get();
        if (pstAudioCfg->bInit) {
            pstRtspCtx->SessionAttr[i].audio.codec = RTSP_AUDIO_PCM_L16;
            pstRtspCtx->SessionAttr[i].audio.sampleRate = pstAudioCfg->astAudioCfg.enSamplerate;
        }
#endif
        APP_PROF_LOG_PRINT(LEVEL_INFO, "VencChn_%d attach to Session_%d with CodecType=%d\n",
                pstRtspCtx->VencChn[i], i, pstRtspCtx->SessionAttr[i].video.codec);
    }

    return CVI_SUCCESS;
}

static void app_ipcam_Rtsp_Connect(const char *ip, CVI_VOID *arg)
{
    APP_PROF_LOG_PRINT(LEVEL_INFO, "rtsp client connected: %s\n", ip);
}

static void app_ipcam_Rtsp_Disconnect(const char *ip, CVI_VOID *arg)
{
    APP_PROF_LOG_PRINT(LEVEL_INFO, "rtsp client disconnected: %s\n", ip);
}

int app_ipcam_rtsp_Server_Destroy(CVI_VOID)
{
    CVI_S32 s32Ret = CVI_SUCCESS;

    if (pstRtspCtx->pstServerCtx == NULL) {
        printf("rtsp server has not been create\n");
        return s32Ret;
    }

    CVI_RTSP_Stop(pstRtspCtx->pstServerCtx);

    pthread_mutex_lock(&pstRtspCtx->RsRtspMutex);
    for (CVI_S32 i = 0; i < pstRtspCtx->session_cnt; i++) {
        if (pstRtspCtx->bStart[0]) {
            CVI_RTSP_DestroySession(pstRtspCtx->pstServerCtx, pstRtspCtx->pstSession[i]);
            pstRtspCtx->bStart[0] = CVI_FALSE;
        }
    }
    pthread_mutex_unlock(&pstRtspCtx->RsRtspMutex);

    CVI_RTSP_Destroy(&pstRtspCtx->pstServerCtx);
    APP_PROF_LOG_PRINT(LEVEL_INFO, "rtsp server destroyed\n");
    pthread_mutex_destroy(&pstRtspCtx->RsRtspMutex);

    pstRtspCtx->pstServerCtx = NULL;

    return 0;
}

int app_ipcam_Rtsp_Server_Create(CVI_VOID)
{
    CVI_S32 s32Ret = CVI_SUCCESS;

    app_ipcam_RtspAttr_Init();

    CVI_RTSP_CONFIG config = {0};
    config.port = pstRtspCtx->port;

    if (pstRtspCtx->pstServerCtx != NULL) {
        APP_PROF_LOG_PRINT(LEVEL_WARN, "rtsp server has been created\n");
        return s32Ret;
    }

    s32Ret = CVI_RTSP_Create(&pstRtspCtx->pstServerCtx, &config);
    if (s32Ret < 0) {
        APP_PROF_LOG_PRINT(LEVEL_ERROR, "fail to create rtsp\n");
        return s32Ret;
    }

    pthread_mutex_init(&pstRtspCtx->RsRtspMutex,NULL);
    s32Ret = CVI_RTSP_Start(pstRtspCtx->pstServerCtx);
    if (s32Ret < 0) {
        APP_PROF_LOG_PRINT(LEVEL_ERROR, "fail to rtsp start\n");
        goto error;
    }

    pthread_mutex_lock(&pstRtspCtx->RsRtspMutex);
    for (CVI_S32 i = 0; i < pstRtspCtx->session_cnt; i++) {
        snprintf(pstRtspCtx->SessionAttr[i].name, sizeof(pstRtspCtx->SessionAttr[i].name), "live%d", i);
        pstRtspCtx->SessionAttr[i].reuseFirstSource = 1;
        CVI_RTSP_CreateSession(pstRtspCtx->pstServerCtx, &pstRtspCtx->SessionAttr[i],
            &pstRtspCtx->pstSession[i]);

        pstRtspCtx->bStart[i] = CVI_TRUE;
        APP_PROF_LOG_PRINT(LEVEL_INFO, "======rtsp start [VencChn%d  %s]  ======\n",
            pstRtspCtx->VencChn[i], pstRtspCtx->SessionAttr[i].name);
    }
    pstRtspCtx->listener.onConnect = app_ipcam_Rtsp_Connect;
    pstRtspCtx->listener.argConn = pstRtspCtx->pstServerCtx;
    pstRtspCtx->listener.onDisconnect = app_ipcam_Rtsp_Disconnect;
    CVI_RTSP_SetListener(pstRtspCtx->pstServerCtx, &pstRtspCtx->listener);
    pthread_mutex_unlock(&pstRtspCtx->RsRtspMutex);

    return s32Ret;

error:
    app_ipcam_rtsp_Server_Destroy();

    return s32Ret;
}

int fpStreamingSendToRtsp(void* pData, void* pArgs, void *pUserData)
{
    APP_DATA_CTX_S* pstDataCtx = (APP_DATA_CTX_S*)pArgs;
    APP_DATA_PARAM_S* pstDataParam = &pstDataCtx->stDataParam;
    APP_VENC_CHN_CFG_S* pstVencChnCfg = (APP_VENC_CHN_CFG_S*)pstDataParam->pParam;
    VENC_CHN VencChn = pstVencChnCfg->VencChn;

    APP_PARAM_RTSP_T* prtspCtx = pstRtspCtx;

    uint8_t idx = 0;
    for (uint8_t i = 0; i < prtspCtx->session_cnt; i++) {
        if (prtspCtx->VencChn[i] == VencChn) {
            idx = i;
            break;
        }
    }

    if ((!prtspCtx->bStart[idx])) {
        return CVI_SUCCESS;
    }

    VENC_STREAM_S* pstStream = (VENC_STREAM_S*)pData;

    CVI_S32 s32Ret = CVI_SUCCESS;
    VENC_PACK_S* ppack;
    CVI_RTSP_DATA data;

    memset(&data, 0, sizeof(CVI_RTSP_DATA));

    data.blockCnt = pstStream->u32PackCount;
    for (CVI_U32 i = 0; i < pstStream->u32PackCount; i++) {
        ppack = &pstStream->pstPack[i];
        data.dataPtr[i] = ppack->pu8Addr + ppack->u32Offset;
        data.dataLen[i] = ppack->u32Len - ppack->u32Offset;
    }
    if (0 == pstStream->u32PackCount) {
        APP_PROF_LOG_PRINT(LEVEL_ERROR, "pstStream->u32PackCount is %d\n", pstStream->u32PackCount);
        return s32Ret;
    }

    if ((NULL != prtspCtx->pstServerCtx) && (NULL != prtspCtx->pstSession[idx])) {
        s32Ret = CVI_RTSP_WriteFrame(prtspCtx->pstServerCtx, prtspCtx->pstSession[idx]->video, &data);
        if (s32Ret != CVI_SUCCESS) {
            APP_PROF_LOG_PRINT(LEVEL_ERROR, "CVI_RTSP_WriteFrame failed\n");
        }
    }

    return CVI_SUCCESS;
}

int initRtsp(uint8_t chEnableFlag)
{
    _Load_Param_Rtsp();

    APP_PARAM_RTSP_T* Rtsp = pstRtspCtx;
    int cnt = 0;
    for (int i = 0; i < MAX_RTSP_SESSION; i++) {
        if (chEnableFlag & (0x1 << i)) {
            Rtsp->VencChn[cnt] = i;
            cnt++;
        }
    }
    Rtsp->session_cnt = cnt;

    app_ipcam_Rtsp_Server_Create();

    return 0;
}

int deinitRtsp(void)
{
    app_ipcam_rtsp_Server_Destroy();

    return 0;
}
```

`main/CMakeLists.txt`'s `SRCS` list must include this file (see the corrected CMakeLists
section further down — already updated to list `rtsp_demo.c` alongside `main.cpp` and
`mqtt_publisher.cpp`).

---

## `main/mqtt_publisher.h` (NEW)

```cpp
#pragma once

#include <atomic>
#include <cstdint>
#include <string>
#include <vector>

#include <mosquitto.h>

namespace weather {

struct MqttConfig {
    std::string host      = "localhost";
    int port               = 1883;
    std::string username;   // empty = anonymous
    std::string password;
    std::string client_id  = "recamera-weather-classifier";
    std::string topic      = "recamera/weather/results";
    int qos                 = 0;
    bool retain             = false;
};

class MqttPublisher {
public:
    MqttPublisher();
    ~MqttPublisher();

    bool init(const MqttConfig& config);
    void deinit();
    bool isConnected() const { return connected_.load(); }

    // Publish one classified-frame result as JSON to config_.topic.
    //   frame_id           : sequential frame counter (1-based, matches stdout log)
    //   label / class_id   : argmax label text and index
    //   confidence         : softmax score of the argmax class
    //   labels / scores    : full label list and per-class softmax scores (same order)
    //   inference_time_ms  : TPU EngineCVI::run() time only
    //   capture_ms         : camera->retrieveFrame() wait time
    //   preprocess_ms      : resize + normalize + tensor-pack time
    //   total_ms           : end-to-end loop latency for this frame
    bool publishClassification(uint64_t frame_id,
                                const std::string& label,
                                int class_id,
                                float confidence,
                                const std::vector<std::string>& labels,
                                const std::vector<float>& scores,
                                double inference_time_ms,
                                double capture_ms,
                                double preprocess_ms,
                                double total_ms);

    bool publish(const std::string& topic, const std::string& payload);

private:
    static void onConnectCallback(struct mosquitto* mosq, void* obj, int rc);
    static void onDisconnectCallback(struct mosquitto* mosq, void* obj, int rc);
    void onConnect(int rc);
    void onDisconnect(int rc);

    std::string buildResultJson(uint64_t frame_id,
                                 const std::string& label,
                                 int class_id,
                                 float confidence,
                                 const std::vector<std::string>& labels,
                                 const std::vector<float>& scores,
                                 double inference_time_ms,
                                 double capture_ms,
                                 double preprocess_ms,
                                 double total_ms);

    struct mosquitto* client_;
    MqttConfig config_;
    std::atomic<bool> connected_;
    std::atomic<bool> initialized_;
};

}  // namespace weather
```

## `main/mqtt_publisher.cpp` (NEW)

```cpp
#include "mqtt_publisher.h"

#include <cstdio>
#include <iomanip>
#include <sstream>

#define TAG "MqttPublisher"

namespace weather {

MqttPublisher::MqttPublisher()
    : client_(nullptr), connected_(false), initialized_(false) {}

MqttPublisher::~MqttPublisher() { deinit(); }

bool MqttPublisher::init(const MqttConfig& config) {
    if (initialized_.load()) {
        std::printf("[%s] already initialized\n", TAG);
        return true;
    }

    config_ = config;

    mosquitto_lib_init();

    client_ = mosquitto_new(config_.client_id.c_str(), true, this);
    if (!client_) {
        std::fprintf(stderr, "[%s] mosquitto_new failed\n", TAG);
        return false;
    }

    mosquitto_connect_callback_set(client_, onConnectCallback);
    mosquitto_disconnect_callback_set(client_, onDisconnectCallback);

    if (!config_.username.empty() && !config_.password.empty()) {
        mosquitto_username_pw_set(client_, config_.username.c_str(), config_.password.c_str());
    }

    mosquitto_reconnect_delay_set(client_, 2, 30, true);

    int rc = mosquitto_loop_start(client_);
    if (rc != MOSQ_ERR_SUCCESS) {
        std::fprintf(stderr, "[%s] mosquitto_loop_start failed: %d\n", TAG, rc);
        mosquitto_destroy(client_);
        client_ = nullptr;
        return false;
    }

    rc = mosquitto_connect(client_, config_.host.c_str(), config_.port, 60);
    if (rc != MOSQ_ERR_SUCCESS) {
        std::fprintf(stderr, "[%s] initial connect failed (will auto-retry): %d\n", TAG, rc);
        // do not fail init: mosquitto's background loop + reconnect_delay handles retry
    }

    initialized_.store(true);
    std::printf("[%s] initialized broker=%s:%d topic=%s\n", TAG, config_.host.c_str(),
                config_.port, config_.topic.c_str());
    return true;
}

void MqttPublisher::deinit() {
    if (!initialized_.load()) return;

    if (client_) {
        if (connected_.load()) mosquitto_disconnect(client_);
        mosquitto_loop_stop(client_, true);
        mosquitto_destroy(client_);
        client_ = nullptr;
    }

    mosquitto_lib_cleanup();
    initialized_.store(false);
    connected_.store(false);
}

void MqttPublisher::onConnectCallback(struct mosquitto*, void* obj, int rc) {
    auto* self = static_cast<MqttPublisher*>(obj);
    if (self) self->onConnect(rc);
}

void MqttPublisher::onDisconnectCallback(struct mosquitto*, void* obj, int rc) {
    auto* self = static_cast<MqttPublisher*>(obj);
    if (self) self->onDisconnect(rc);
}

void MqttPublisher::onConnect(int rc) {
    if (rc == 0) {
        connected_.store(true);
        std::printf("[%s] connected\n", TAG);
    } else {
        std::fprintf(stderr, "[%s] connect failed rc=%d\n", TAG, rc);
    }
}

void MqttPublisher::onDisconnect(int rc) {
    connected_.store(false);
    if (rc != 0) std::fprintf(stderr, "[%s] unexpected disconnect rc=%d\n", TAG, rc);
}

bool MqttPublisher::publish(const std::string& topic, const std::string& payload) {
    if (!initialized_.load() || !client_) return false;

    int rc = mosquitto_publish(client_, nullptr, topic.c_str(),
                                static_cast<int>(payload.size()), payload.data(),
                                config_.qos, config_.retain);
    if (rc != MOSQ_ERR_SUCCESS) {
        std::fprintf(stderr, "[%s] publish failed rc=%d\n", TAG, rc);
        return false;
    }
    return true;
}

std::string MqttPublisher::buildResultJson(uint64_t frame_id,
                                            const std::string& label,
                                            int class_id,
                                            float confidence,
                                            const std::vector<std::string>& labels,
                                            const std::vector<float>& scores,
                                            double inference_time_ms,
                                            double capture_ms,
                                            double preprocess_ms,
                                            double total_ms) {
    std::ostringstream json;
    json << std::fixed;

    json << "{";
    json << "\"type\":\"classification\",";
    json << "\"frame\":" << frame_id << ",";
    json << "\"label\":\"" << label << "\",";
    json << "\"class_id\":" << class_id << ",";
    json << "\"confidence\":" << std::setprecision(4) << confidence << ",";

    json << "\"scores\":{";
    for (size_t i = 0; i < scores.size(); ++i) {
        const std::string name = i < labels.size() ? labels[i] : ("class_" + std::to_string(i));
        if (i > 0) json << ",";
        json << "\"" << name << "\":" << std::setprecision(4) << scores[i];
    }
    json << "},";

    json << "\"inference_time_ms\":" << std::setprecision(2) << inference_time_ms << ",";
    json << "\"capture_ms\":" << std::setprecision(2) << capture_ms << ",";
    json << "\"preprocess_ms\":" << std::setprecision(2) << preprocess_ms << ",";
    json << "\"total_ms\":" << std::setprecision(2) << total_ms;
    json << "}";

    return json.str();
}

bool MqttPublisher::publishClassification(uint64_t frame_id,
                                           const std::string& label,
                                           int class_id,
                                           float confidence,
                                           const std::vector<std::string>& labels,
                                           const std::vector<float>& scores,
                                           double inference_time_ms,
                                           double capture_ms,
                                           double preprocess_ms,
                                           double total_ms) {
    const std::string payload = buildResultJson(frame_id, label, class_id, confidence, labels,
                                                 scores, inference_time_ms, capture_ms,
                                                 preprocess_ms, total_ms);
    return publish(config_.topic, payload);
}

}  // namespace weather
```

This produces exactly the schema requested:

```json
{"type":"classification","frame":42,"label":"foggy","class_id":2,"confidence":0.8341,"scores":{"clear":0.01,"cloudy":0.05,"foggy":0.83,"rainy":0.08,"snowy":0.03},"inference_time_ms":12.1,"capture_ms":1.2,"preprocess_ms":3.44,"total_ms":17.02}
```

---

## `main/main.cpp` (MODIFIED — full file)

Preprocessing/inference logic (`Classifier`, `softmax`, `load_labels`, `dtype_name`,
`ms_between`) is **byte-identical** to upstream. Only additions: new includes, a `Config`
struct + `getopt_long`-based flag parsing (backward compatible with the original
positional args), an `init_video_streaming()` step, an `init_mqtt()` step, and the MQTT
publish call inside the main loop.

```cpp
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <getopt.h>
#include <memory>
#include <numeric>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <sscma.h>
#include <video.h>

#include "engine_utils.h"
#include "mqtt_publisher.h"
#include "rtsp_demo.h"

using Clock = std::chrono::steady_clock;
using namespace ma;

static std::atomic<bool> g_running{true};

static double ms_between(const Clock::time_point& a, const Clock::time_point& b) {
    return std::chrono::duration<double, std::milli>(b - a).count();
}

static std::vector<std::string> load_labels(const std::string& path) {
    std::vector<std::string> labels;
    std::ifstream f(path);
    std::string line;
    while (std::getline(f, line)) {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (!line.empty())
            labels.push_back(line);
    }
    return labels;
}

static const char* dtype_name(ma_tensor_type_t t) {
    switch (t) {
        case MA_TENSOR_TYPE_F32:
            return "F32";
        case MA_TENSOR_TYPE_F16:
            return "F16";
        case MA_TENSOR_TYPE_BF16:
            return "BF16";
        case MA_TENSOR_TYPE_S8:
            return "S8";
        case MA_TENSOR_TYPE_U8:
            return "U8";
        default:
            return "UNKNOWN";
    }
}

struct Classifier {
    std::unique_ptr<ma::engine::EngineCVI> engine;
    ma_tensor_t input_desc{};
    ma_tensor_type_t input_type{};
    ma_quant_param_t input_qp{};
    weather::InputBuf input_buf;
    size_t input_numel = 0;
    int input_w        = 0;
    int input_h        = 0;
    bool nchw          = true;

    bool init(const std::string& model_path) {
        engine = std::make_unique<ma::engine::EngineCVI>();
        if (engine->init() != MA_OK) {
            std::fprintf(stderr, "[ERROR] EngineCVI::init failed\n");
            return false;
        }
        if (engine->load(model_path) != MA_OK) {
            std::fprintf(stderr, "[ERROR] load model failed: %s\n", model_path.c_str());
            return false;
        }

        if (engine->getInputSize() != 1) {
            std::fprintf(stderr, "[ERROR] expected one input, got %d\n", engine->getInputSize());
            return false;
        }

        input_desc             = engine->getInput(0);
        input_type             = input_desc.type;
        input_qp               = input_desc.quant_param;
        const ma_shape_t shape = engine->getInputShape(0);
        if (shape.size != 4) {
            std::fprintf(stderr, "[ERROR] expected 4-D image input\n");
            return false;
        }

        if (shape.dims[1] == 3) {
            nchw    = true;
            input_h = shape.dims[2];
            input_w = shape.dims[3];
        } else if (shape.dims[3] == 3) {
            nchw    = false;
            input_h = shape.dims[1];
            input_w = shape.dims[2];
        } else {
            std::fprintf(stderr, "[ERROR] cannot determine NCHW/NHWC layout\n");
            return false;
        }

        input_numel = weather::shape_numel(shape);
        input_buf.resize_for(input_type, input_numel);

        std::printf("[MODEL] input name=%s type=%s layout=%s shape=(", input_desc.name ? input_desc.name : "null", dtype_name(input_type), nchw ? "NCHW" : "NHWC");
        for (int i = 0; i < shape.size; ++i) {
            std::printf("%d%s", shape.dims[i], i + 1 < shape.size ? "," : "");
        }
        std::printf(") quant(scale=%g,zp=%d)\n", input_qp.scale, input_qp.zero_point);

        for (int i = 0; i < engine->getOutputSize(); ++i) {
            const ma_tensor_t t = engine->getOutput(i);
            const ma_shape_t s  = engine->getOutputShape(i);
            std::printf("[MODEL] output[%d] name=%s type=%s shape=(", i, t.name ? t.name : "null", dtype_name(t.type));
            for (int j = 0; j < s.size; ++j) {
                std::printf("%d%s", s.dims[j], j + 1 < s.size ? "," : "");
            }
            std::printf(")\n");
        }
        return true;
    }

    // 默认对齐 torchvision ImageNet 预处理：
    // RGB -> resize(input_w,input_h) -> /255 -> (x-mean)/std
    // 若你的 export_onnx.py 已把 Normalize 写进模型，请把 mean 改为 0、std 改为 1。
    void preprocess(const ::cv::Mat& rgb) {
        ::cv::Mat resized;
        ::cv::resize(rgb, resized, ::cv::Size(input_w, input_h), 0, 0, ::cv::INTER_LINEAR);

        const float mean[3] = {0.485f, 0.456f, 0.406f};
        const float stdv[3] = {0.229f, 0.224f, 0.225f};

        for (int y = 0; y < input_h; ++y) {
            const uint8_t* row = resized.ptr<uint8_t>(y);
            for (int x = 0; x < input_w; ++x) {
                for (int c = 0; c < 3; ++c) {
                    const float real = (row[x * 3 + c] / 255.0f - mean[c]) / stdv[c];
                    size_t idx;
                    if (nchw) {
                        idx = static_cast<size_t>(c) * input_h * input_w + static_cast<size_t>(y) * input_w + x;
                    } else {
                        idx = (static_cast<size_t>(y) * input_w + x) * 3 + c;
                    }
                    weather::store_val(input_buf, input_type, input_qp, idx, real);
                }
            }
        }
    }

    bool infer(std::vector<float>& output, double& run_ms) {
        ma_tensor_t input = weather::make_input_tensor(input_type, input_buf, input_numel);
        input.type        = input_type;
        input.quant_param = input_qp;

        if (engine->setInput(0, input) != MA_OK) {
            std::fprintf(stderr, "[ERROR] setInput failed\n");
            return false;
        }

        const auto t0 = Clock::now();
        const int ret = engine->run();
        const auto t1 = Clock::now();
        run_ms        = ms_between(t0, t1);
        if (ret != MA_OK) {
            std::fprintf(stderr, "[ERROR] engine run failed: %d\n", ret);
            return false;
        }

        const ma_tensor_t out = engine->getOutput(0);
        const size_t n        = weather::shape_numel(engine->getOutputShape(0));
        output.resize(n);
        for (size_t i = 0; i < n; ++i)
            output[i] = weather::read_val(out, i);
        return true;
    }
};

static std::vector<float> softmax(const std::vector<float>& logits) {
    if (logits.empty())
        return {};
    const float maxv = *std::max_element(logits.begin(), logits.end());
    std::vector<float> probs(logits.size());
    double sum = 0.0;
    for (size_t i = 0; i < logits.size(); ++i) {
        probs[i] = std::exp(logits[i] - maxv);
        sum += probs[i];
    }
    if (sum > 0) {
        for (float& p : probs)
            p = static_cast<float>(p / sum);
    }
    return probs;
}

// ---------------------------------------------------------------------------
// NEW: CLI config, RTSP streaming, MQTT publishing
// ---------------------------------------------------------------------------

struct Config {
    // Original positional args (unchanged contract)
    std::string model_path;
    std::string labels_path;
    int print_interval = 1;
    int camera_w        = 640;
    int camera_h        = 480;

    // MQTT (long-flag names match sibling apps: --mqtt-host / --mqtt-port)
    bool enable_mqtt      = true;
    std::string mqtt_host = "localhost";
    int mqtt_port          = 1883;
    std::string mqtt_topic = "recamera/weather/results";

    // RTSP (fixed at rtsp://<device-ip>:8554/live0 by the SDK's cvi_rtsp component;
    // only the encode resolution/fps are configurable here)
    bool enable_rtsp   = true;
    int stream_width    = 1280;
    int stream_height   = 720;
    int stream_fps       = 15;
};

static void print_usage(const char* prog) {
    std::printf(
        "Usage: %s <model.cvimodel> <labels.txt> [print_interval] [camera_w] [camera_h] "
        "[options]\n\n"
        "Options:\n"
        "  --mqtt-host HOST       MQTT broker host (default: localhost)\n"
        "  --mqtt-port PORT       MQTT broker port (default: 1883)\n"
        "  --mqtt-topic TOPIC     MQTT publish topic (default: recamera/weather/results)\n"
        "  --no-mqtt              Disable MQTT publishing\n"
        "  --no-rtsp              Disable RTSP streaming\n"
        "  --stream-width N       RTSP encode width (default: 1280)\n"
        "  --stream-height N      RTSP encode height (default: 720)\n"
        "  --stream-fps N         RTSP encode fps (default: 15)\n"
        "  -h, --help             Show this help message\n\n"
        "RTSP stream: rtsp://<device-ip>:8554/live0\n",
        prog);
}

static bool parse_args(int argc, char** argv, Config& cfg) {
    static struct option long_options[] = {
        {"mqtt-host", required_argument, 0, 1},
        {"mqtt-port", required_argument, 0, 2},
        {"mqtt-topic", required_argument, 0, 3},
        {"no-mqtt", no_argument, 0, 4},
        {"no-rtsp", no_argument, 0, 5},
        {"stream-width", required_argument, 0, 6},
        {"stream-height", required_argument, 0, 7},
        {"stream-fps", required_argument, 0, 8},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0},
    };

    int opt;
    while ((opt = getopt_long(argc, argv, "h", long_options, nullptr)) != -1) {
        switch (opt) {
            case 1: cfg.mqtt_host = optarg; break;
            case 2: cfg.mqtt_port = std::atoi(optarg); break;
            case 3: cfg.mqtt_topic = optarg; break;
            case 4: cfg.enable_mqtt = false; break;
            case 5: cfg.enable_rtsp = false; break;
            case 6: cfg.stream_width = std::atoi(optarg); break;
            case 7: cfg.stream_height = std::atoi(optarg); break;
            case 8: cfg.stream_fps = std::atoi(optarg); break;
            case 'h': print_usage(argv[0]); std::exit(0);
            default: print_usage(argv[0]); return false;
        }
    }

    // getopt_long permutes argv, so all remaining positional args land at
    // argv[optind..argc-1] regardless of where the flags were typed.
    std::vector<std::string> pos;
    for (int i = optind; i < argc; ++i) pos.emplace_back(argv[i]);

    if (pos.size() < 2) {
        print_usage(argv[0]);
        return false;
    }
    cfg.model_path  = pos[0];
    cfg.labels_path = pos[1];
    if (pos.size() > 2) cfg.print_interval = std::max(1, std::atoi(pos[2].c_str()));
    if (pos.size() > 3) cfg.camera_w = std::atoi(pos[3].c_str());
    if (pos.size() > 4) cfg.camera_h = std::atoi(pos[4].c_str());
    return true;
}

// H.264 encode channel (VIDEO_CH2) -> cvi_rtsp component -> rtsp://<ip>:8554/live0.
// This is a *separate* ISP output channel from the raw RGB888 channel the classifier
// reads via camera->retrieveFrame() below; both run concurrently off the same sensor.
static bool init_video_streaming(const Config& cfg) {
    if (!cfg.enable_rtsp) {
        std::printf("[INFO] RTSP streaming disabled\n");
        return true;
    }

    if (initVideo() != 0) {
        std::fprintf(stderr, "[ERROR] initVideo failed\n");
        return false;
    }

    video_ch_param_t stream_param{};
    stream_param.format = VIDEO_FORMAT_H264;
    stream_param.width  = static_cast<uint32_t>(cfg.stream_width);
    stream_param.height = static_cast<uint32_t>(cfg.stream_height);
    stream_param.fps    = static_cast<uint8_t>(cfg.stream_fps);
    setupVideo(VIDEO_CH2, &stream_param);
    registerVideoFrameHandler(VIDEO_CH2, 0, fpStreamingSendToRtsp, nullptr);
    initRtsp((0x01 << VIDEO_CH2));

    std::printf("[OK] RTSP streaming rtsp://<device-ip>:8554/live0 (%dx%d@%dfps)\n",
                cfg.stream_width, cfg.stream_height, cfg.stream_fps);
    return true;
}

static weather::MqttPublisher* g_mqtt = nullptr;

static bool init_mqtt(const Config& cfg) {
    if (!cfg.enable_mqtt) {
        std::printf("[INFO] MQTT publishing disabled\n");
        return true;
    }

    g_mqtt = new weather::MqttPublisher();
    weather::MqttConfig mc;
    mc.host  = cfg.mqtt_host;
    mc.port  = cfg.mqtt_port;
    mc.topic = cfg.mqtt_topic;

    if (!g_mqtt->init(mc)) {
        std::fprintf(stderr, "[ERROR] MQTT init failed\n");
        return false;
    }
    std::printf("[OK] MQTT publishing to %s:%d topic=%s\n", cfg.mqtt_host.c_str(),
                cfg.mqtt_port, cfg.mqtt_topic.c_str());
    return true;
}

int main(int argc, char** argv) {
    Config cfg;
    if (!parse_args(argc, argv, cfg)) return 1;

    Signal::install({SIGINT, SIGTERM, SIGQUIT}, [](int) { g_running.store(false); });

    const auto labels = load_labels(cfg.labels_path);
    Classifier classifier;
    if (!classifier.init(cfg.model_path))
        return 2;

    Device* device = Device::getInstance();
    Camera* camera = nullptr;
    for (auto& sensor : device->getSensors()) {
        if (sensor->getType() == ma::Sensor::Type::kCamera) {
            camera = static_cast<Camera*>(sensor);
            if (camera->init(0) != MA_OK) {
                std::fprintf(stderr, "[ERROR] camera init failed\n");
                return 3;
            }

            Camera::CtrlValue v;
            v.i32 = 0;
            camera->commandCtrl(Camera::CtrlType::kChannel, Camera::CtrlMode::kWrite, v);

            v.u16s[0] = static_cast<uint16_t>(cfg.camera_w);
            v.u16s[1] = static_cast<uint16_t>(cfg.camera_h);
            camera->commandCtrl(Camera::CtrlType::kWindow, Camera::CtrlMode::kWrite, v);

            v.i32 = 1;  // frame.data 返回物理地址
            camera->commandCtrl(Camera::CtrlType::kPhysical, Camera::CtrlMode::kWrite, v);
            break;
        }
    }

    if (!camera) {
        std::fprintf(stderr, "[ERROR] no camera found\n");
        return 4;
    }

    // NEW: bring up the H.264/RTSP encode channel and the MQTT publisher before we
    // start pulling inference frames, mirroring yolo-detector's init ordering
    // (detector -> camera -> video_streaming -> mqtt -> camera->startStream()).
    if (!init_video_streaming(cfg)) {
        camera->deInit();
        return 6;
    }
    if (!init_mqtt(cfg)) {
        if (cfg.enable_rtsp) { deinitRtsp(); deinitVideo(); }
        camera->deInit();
        return 7;
    }

    if (camera->startStream(Camera::StreamMode::kRefreshOnReturn) != MA_OK) {
        std::fprintf(stderr, "[ERROR] camera startStream failed\n");
        if (g_mqtt) { g_mqtt->deinit(); delete g_mqtt; g_mqtt = nullptr; }
        if (cfg.enable_rtsp) { deinitRtsp(); deinitVideo(); }
        camera->deInit();
        return 5;
    }

    std::printf("[OK] camera=%dx%d RGB888, model=%s\n", cfg.camera_w, cfg.camera_h, cfg.model_path.c_str());
    std::printf("[INFO] first 10 inference runs are warm-up and excluded from averages\n");

    uint64_t frame_id  = 0;
    uint64_t measured  = 0;
    double sum_capture = 0.0, sum_pre = 0.0, sum_run = 0.0, sum_total = 0.0;
    double min_run = 1e9, max_run = 0.0;

    while (g_running.load()) {
        const auto total0 = Clock::now();
        ma_img_t frame{};

        const auto cap0 = Clock::now();
        if (camera->retrieveFrame(frame, MA_PIXEL_FORMAT_RGB888) != MA_OK) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
            continue;
        }
        const auto cap1 = Clock::now();

        if (!frame.data || frame.size == 0 || frame.width == 0 || frame.height == 0) {
            camera->returnFrame(frame);
            continue;
        }

        void* mapped = CVI_SYS_Mmap(reinterpret_cast<uint64_t>(frame.data), frame.size);
        if (!mapped) {
            std::fprintf(stderr, "[WARN] CVI_SYS_Mmap failed\n");
            camera->returnFrame(frame);
            continue;
        }

        const int width  = static_cast<int>(frame.width);
        const int height = static_cast<int>(frame.height);
        int stride       = width * 3;
        if (height > 0) {
            const size_t guessed = frame.size / static_cast<size_t>(height);
            if (guessed >= static_cast<size_t>(width * 3))
                stride = static_cast<int>(guessed);
        }

        ::cv::Mat rgb(height, width, CV_8UC3, mapped, static_cast<size_t>(stride));

        const auto pre0 = Clock::now();
        classifier.preprocess(rgb);
        const auto pre1 = Clock::now();

        std::vector<float> logits;
        double run_ms = 0.0;
        const bool ok = classifier.infer(logits, run_ms);

        CVI_SYS_Munmap(mapped, frame.size);
        camera->returnFrame(frame);

        if (!ok || logits.empty())
            continue;

        // 若模型输出本身已经是概率，softmax 仍会改变结果。
        // 可通过观察输出和与 ONNX 对比确认；默认按 logits 处理。
        const std::vector<float> probs = softmax(logits);
        const auto best_it             = std::max_element(probs.begin(), probs.end());
        const size_t best              = static_cast<size_t>(std::distance(probs.begin(), best_it));
        const float score              = *best_it;

        const auto total1       = Clock::now();
        const double capture_ms = ms_between(cap0, cap1);
        const double pre_ms     = ms_between(pre0, pre1);
        const double total_ms   = ms_between(total0, total1);

        ++frame_id;
        if (frame_id > 10) {
            ++measured;
            sum_capture += capture_ms;
            sum_pre += pre_ms;
            sum_run += run_ms;
            sum_total += total_ms;
            min_run = std::min(min_run, run_ms);
            max_run = std::max(max_run, run_ms);
        }

        const std::string name = best < labels.size() ? labels[best] : ("class_" + std::to_string(best));

        // NEW: publish every classified frame over MQTT (independent of the
        // stdout print_interval throttle below — matches sibling apps' pattern
        // of publishing every frame regardless of their console verbosity flag).
        if (cfg.enable_mqtt && g_mqtt) {
            g_mqtt->publishClassification(frame_id, name, static_cast<int>(best), score, labels,
                                           probs, run_ms, capture_ms, pre_ms, total_ms);
        }

        if (frame_id % static_cast<uint64_t>(cfg.print_interval) == 0) {
            std::printf(
                "[RESULT] frame=%llu class=%zu(%s) score=%.4f | capture=%.2fms pre=%.2fms "
                "TPU_run=%.2fms total=%.2fms",
                static_cast<unsigned long long>(frame_id),
                best,
                name.c_str(),
                score,
                capture_ms,
                pre_ms,
                run_ms,
                total_ms);
            if (measured > 0) {
                std::printf(" | avg_run=%.2fms min=%.2fms max=%.2fms avg_total=%.2fms", sum_run / measured, min_run, max_run, sum_total / measured);
            }
            std::printf("\n");
            std::fflush(stdout);
        }
    }

    camera->stopStream();
    camera->deInit();
    if (g_mqtt) { g_mqtt->deinit(); delete g_mqtt; g_mqtt = nullptr; }
    if (cfg.enable_rtsp) { deinitRtsp(); deinitVideo(); }

    if (measured > 0) {
        std::printf("\n[SUMMARY] samples=%llu\n", static_cast<unsigned long long>(measured));
        std::printf("  avg capture : %.3f ms\n", sum_capture / measured);
        std::printf("  avg preprocess: %.3f ms\n", sum_pre / measured);
        std::printf("  avg TPU_run : %.3f ms (min %.3f, max %.3f)\n", sum_run / measured, min_run, max_run);
        std::printf("  avg total   : %.3f ms\n", sum_total / measured);
        std::printf("  inference FPS (TPU only): %.2f\n", 1000.0 / (sum_run / measured));
        std::printf("  end-to-end FPS: %.2f\n", 1000.0 / (sum_total / measured));
    }
    return 0;
}
```

---

## `main/CMakeLists.txt` (MODIFIED — component registration)

Original:

```cmake
link_directories("${CMAKE_CURRENT_LIST_DIR}")

component_register(
    COMPONENT_NAME main

    SRCS
    "${CMAKE_CURRENT_LIST_DIR}/main.cpp"

    INCLUDE_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/"

    PRIVATE_REQUIREDS
    sophgo
    sscma-micro
)
```

Modified:

```cmake
link_directories("${CMAKE_CURRENT_LIST_DIR}")

component_register(
    COMPONENT_NAME main

    SRCS
    "${CMAKE_CURRENT_LIST_DIR}/main.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/mqtt_publisher.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/rtsp_demo.c"

    INCLUDE_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/"

    PRIVATE_REQUIREDS
    sophgo
    sscma-micro
    cvi_rtsp
    mosquitto
)
```

(`cvi_rtsp` and `mosquitto` are the two new dependencies, confirmed from
`yolo-detector`/`ppocr-reader`'s `PRIVATE_REQUIREDS` list — both are prebuilt SDK
components resolved from `SG200X_SDK_PATH`, not built from source in this repo. Omit
`debug_stream mongoose` since this patch doesn't add the debug WS overlay.)

## Root `CMakeLists.txt`

**No change required.** It only sets up the toolchain, C++17 flag, and links
`opencv_imgproc`/`opencv_core` from the TPU SDK directly via
`target_link_libraries`/`target_include_directories` — `cvi_rtsp` and `mosquitto` resolve
through the `component_register(PRIVATE_REQUIREDS ...)` mechanism above, not this file.

---

## What to verify on real hardware

1. **Cross-compile clean**: `cvi_rtsp`, `rtsp.h`, `cvi_type.h`, `linux/cvi_common.h`,
   `mosquitto.h` must all resolve from `SG200X_SDK_PATH`/toolchain sysroot — confirm the
   include/lib paths `yolo-detector` relies on (via the SDK's `component_register` system)
   are actually present for this specific SDK checkout, not just declared.
2. **musl `getopt_long` permutation**: confirm `riscv64-linux-musl-x86_64`'s libc permutes
   non-option args the same way glibc does, so `--mqtt-host` can be placed anywhere
   relative to the positional `<model> <labels> ...` args. If not, document/enforce
   flags-after-positionals ordering.
3. **Dual video channel contention**: verify pulling raw RGB888 frames via
   `camera->retrieveFrame()` (inference channel) concurrently with the H.264 `VIDEO_CH2`
   encode channel doesn't starve either pipeline or drop the camera's effective FPS below
   what the classifier loop expects — `yolo-detector` explicitly sets an inference-channel
   FPS control (`Camera::CtrlType::kFps`) to avoid this; this patch does not (upstream
   didn't either), so watch capture-latency numbers in `[RESULT]` after adding RTSP.
4. **RTSP playback**: confirm `rtsp://<device-ip>:8554/live0` actually plays in VLC/ffplay
   once `initRtsp()` succeeds — the encode channel resolution (1280x720@15fps) is a
   default from `yolo-detector`, not validated for this model/camera combo.
5. **MQTT connectivity end-to-end**: confirm `mosquitto -c /etc/mosquitto/mosquitto.conf`
   is actually listening on `0.0.0.0:1883` (this solution's
   `devices/recamera_weather.yaml` deploy action enables that) before the binary starts,
   and that `mosquitto_sub -h <device-ip> -t recamera/weather/results` shows a JSON line
   per frame.
6. **`/etc/weather-classifier.conf` wiring**: this solution's deploy action writes
   `MQTT_HOST=`/`MQTT_PORT=` into that file — the `.deb`'s init script
   (`S92weather-classifier`, per `skills/prepare-deb-package` convention, priority `92`)
   must actually `source`/`grep` that file and pass `--mqtt-host "$MQTT_HOST" --mqtt-port
   "$MQTT_PORT"` on the command line; this was **not** found in any sibling app (they're
   run directly from the shell per their own READMEs) and needs to be written from
   scratch for this solution's init script.
7. **Stop conflicting services first**: per upstream README, `S03node-red`,
   `S91sscma-node`, `S93sscma-supervisor` must be stopped/disabled before running (already
   handled by this solution's deploy action) — otherwise something else may already own
   the RTSP/H.264 venc channel or port 8554.
8. **Shutdown/signal path**: confirm `Signal::install` still fires cleanly with the new
   `deinitRtsp()`/`deinitVideo()`/`g_mqtt->deinit()` calls added to the shutdown sequence —
   no sibling app was found combining SSCMA-Micro's `Signal::install` (used only by the
   upstream weather app) with `cvi_rtsp`/mosquitto teardown, so this ordering is inferred,
   not copied from a confirmed-working combination.
9. **JSON field precision**: `confidence`/`scores` are emitted with `setprecision(4)`, and
   the `_ms` timing fields with `setprecision(2)`, matching the example payload in the task
   (`0.8341`, `12.1`) — double check downstream consumers (e.g.
   `preview/draw_weather.js`) tolerate this vs. expecting fixed decimal places.
