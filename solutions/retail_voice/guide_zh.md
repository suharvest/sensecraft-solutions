## 套餐: 设备转写并上传 {#local_transcribe}

设备将语音转成文字，再上传到零售语音后台统一查看。

## 步骤 1: 部署零售语音后台 {#deploy_backend_local type=docker_deploy required=true config=devices/cloud_stack.yaml}

填写后台设备的地址和登录信息，点击部署。完成后，记下后台地址和接入密钥，下一步会用到。

## 步骤 2: 连接采集设备 {#deploy_local type=docker_deploy required=true config=devices/local_rk3576.yaml}

选好设备型号，接上麦克风。填写设备登录信息、后台地址和接入密钥，然后点击部署。

### Target {#local_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/local_rk3576.yaml default=true}

选择与你的设备一致的型号。

### Target {#local_rk3588_remote type=remote device=rk3588 device_name="reComputer RK3588" config=devices/local_rk3588.yaml}

选择与你的设备一致的型号。

### Target {#local_j30_remote type=remote device=j30 device_name="reComputer J3011" config=devices/local_j30.yaml}

选择与你的设备一致的型号。

### Target {#local_j40_remote type=remote device=j40 device_name="reComputer J4012" config=devices/local_j40.yaml}

选择与你的设备一致的型号。

### Target {#local_r2000_remote type=remote device=r2000 device_name="reComputer R2000（不配加速卡）" config=devices/local_r2000.yaml}

选择与你的设备一致的型号。

### Target {#local_r2000_hailo_remote type=remote device=r2000_hailo device_name="reComputer R2000（配 Hailo 加速卡）" config=devices/local_r2000_hailo.yaml}

选择与你的设备一致的型号。

### Target {#local_cm4_remote type=remote device=rerouter device_name="reRouter CM4" config=devices/local_rerouter.yaml}

选择与你的设备一致的型号。

## 步骤 3: 检查录音结果 {#verify_local type=manual verify=true required=true config=devices/verify_asr.yaml}

对着麦克风说一句话，再打开零售语音后台。能看到这条录音和对应文字，就完成了。

[详细说明与问题排查](https://wiki.seeedstudio.com/solutions/smart-retail-voice-ai-solution-1/)

## 套餐: Clip＋手机，后台转写 {#cloud_stack}

Clip 负责录音，手机上传音频，零售语音后台自动转成文字。

## 步骤 1: 部署零售语音平台 {#deploy_server_platform type=docker_deploy required=true config=devices/cloud_rk3576.yaml}

选择要部署的设备，填写地址和登录信息，点击部署。后台和转写服务会一起安装。

### Target {#stack_rk3588_remote type=remote device=rk3588 device_name="reComputer RK3588" config=devices/cloud_rk3588.yaml}

选择与你的设备一致的型号。

### Target {#stack_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/cloud_rk3576.yaml default=true}

选择与你的设备一致的型号。

### Target {#stack_j30_remote type=remote device=j30 device_name="reComputer J3011" config=devices/cloud_j30.yaml}

选择与你的设备一致的型号。

### Target {#stack_j40_remote type=remote device=j40 device_name="reComputer J4012" config=devices/cloud_j40.yaml}

选择与你的设备一致的型号。

### Target {#stack_r2000_remote type=remote device=r2000 device_name="reComputer R2000（配 Hailo 加速卡）" config=devices/cloud_r2000.yaml}

选择与你的设备一致的型号。

### Target {#stack_r2000_cpu_remote type=remote device=r2000_cpu device_name="reComputer R2000（不配加速卡）" config=devices/cloud_r2000_cpu.yaml}

选择与你的设备一致的型号。

## 步骤 2: 连接手机 App {#asr_endpoint type=manual required=true config=devices/asr_endpoint.yaml}

1. 将 Clip 与 SenseCraft Voice App 配对。
2. 打开 **AI CONFIG**，选择 `local_whisper`。
3. Base URL 填 `http://<部署设备 IP>:18621`；接入密钥填写平台管理员提供的密钥。
4. 点击“测试连接”，成功后保存。

[查看 Clip 配对和 App 设置说明](https://wiki.seeedstudio.com/respeaker_clip/)

## 步骤 3: 打开零售语音后台 {#admin_web type=web_dashboard required=false config=devices/admin_web.yaml}

打开后台并登录。之后可在这里查看和管理录音。

## 步骤 4: 试录一段语音 {#verify_stack type=manual required=true verify=true config=devices/verify_stack.yaml}

用 Clip 录一小段语音并在手机中上传。确认后台出现录音和对应文字。

[详细说明与问题排查](https://wiki.seeedstudio.com/solutions/smart-retail-voice-ai-solution-1/)
