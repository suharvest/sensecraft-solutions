## Preset: Transcribe on the device {#local_transcribe}

The device turns speech into text and sends the results to your retail voice dashboard.

## Step 1: Set up the retail voice dashboard {#deploy_backend_local type=docker_deploy required=true config=devices/cloud_stack.yaml}

Enter the server address and login details, then deploy. Keep its dashboard address and access key for the next step.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect to the server | Check the server address and SSH login details, and that the server is reachable from this machine |
| Deploy stops while waiting for the service to turn healthy | Sign in to the server and run `docker compose logs voice-service`; MySQL or MinIO may still be starting |
| Dashboard does not open afterwards | Confirm the `voice-web` container is running and port 3000 is reachable |

### Target {#backend_remote type=remote config=devices/cloud_stack.yaml default=true}

Deploy to a Linux server the recording devices can reach.

### Target {#backend_local type=local config=devices/cloud_stack.yaml}

Deploy to this computer. The recording devices must be able to reach its IP.

## Step 2: Set up the recording device {#deploy_local type=docker_deploy required=true config=devices/local_rk3576.yaml}

Choose your device model and connect the microphone. Enter its login details, dashboard address and access key, then deploy.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect to the device | Check the device IP and SSH login details |
| Microphone not detected during deploy | Move the reSpeaker microphone array to a USB-A host port and run the deploy again |
| No transcription reaches the dashboard | Check the dashboard address and access key match what Step 1 issued |

### Target {#local_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/local_rk3576.yaml default=true}

Choose the model that matches your device.

### Target {#local_rk3588_remote type=remote device=rk3588 device_name="reComputer RK3588" config=devices/local_rk3588.yaml}

Choose the model that matches your device.

### Target {#local_j30_remote type=remote device=j30 device_name="reComputer J3011" config=devices/local_j30.yaml}

Choose the model that matches your device.

### Target {#local_j40_remote type=remote device=j40 device_name="reComputer J4012" config=devices/local_j40.yaml}

Choose the model that matches your device.

### Target {#local_r2000_remote type=remote device=r2000 device_name="reComputer R2000" config=devices/local_r2000.yaml}

Choose the model that matches your device.

### Target {#local_r2000_hailo_remote type=remote device=r2000_hailo device_name="reComputer R2000 + Hailo-8" config=devices/local_r2000_hailo.yaml}

Choose the model that matches your device.

### Target {#local_cm4_remote type=remote device=rerouter device_name="reRouter CM4" config=devices/local_rerouter.yaml}

Choose the model that matches your device.

## Step 3: Check a recording {#verify_local type=manual verify=true required=true config=devices/verify_asr.yaml}

Speak into the microphone, then open the retail voice dashboard. Confirm that the recording and its text appear.

[Detailed instructions and troubleshooting](https://wiki.seeedstudio.com/solutions/smart-retail-voice-ai-solution-1/)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The recording does not appear | Check the recording device is powered and the microphone is connected, then record again |
| The recording appears without text | Check the `speech` service container is running on the recording device |

## Preset: Clip and phone, server transcription {#cloud_stack}

Clip records the conversation, your phone uploads the audio, and the retail voice platform turns it into text.

## Step 1: Set up the retail voice platform {#deploy_server_platform type=docker_deploy required=true config=devices/cloud_rk3576.yaml}

Choose your server model, enter its address and login details, then deploy. The dashboard and transcription service are installed together.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect to the server | Check the server address and SSH login details, and that the server is reachable from this machine |
| Deploy stops while waiting for the service to turn healthy | Sign in to the server and run `docker compose logs voice-service`; MySQL or MinIO may still be starting |
| The phone app cannot reach the transcription endpoint later | Confirm the `capture-gateway` container is running and port 18621 is reachable |

### Target {#stack_rk3588_remote type=remote device=rk3588 device_name="reComputer RK3588" config=devices/cloud_rk3588.yaml}

Choose the model that matches your device.

### Target {#stack_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/cloud_rk3576.yaml default=true}

Choose the model that matches your device.

### Target {#stack_j30_remote type=remote device=j30 device_name="reComputer J3011" config=devices/cloud_j30.yaml}

Choose the model that matches your device.

### Target {#stack_j40_remote type=remote device=j40 device_name="reComputer J4012" config=devices/cloud_j40.yaml}

Choose the model that matches your device.

### Target {#stack_r2000_remote type=remote device=r2000 device_name="reComputer R2000 + Hailo-8" config=devices/cloud_r2000.yaml}

Choose the model that matches your device.

### Target {#stack_r2000_cpu_remote type=remote device=r2000_cpu device_name="reComputer R2000" config=devices/cloud_r2000_cpu.yaml}

Choose the model that matches your device.

## Step 2: Connect the phone app {#asr_endpoint type=manual required=true config=devices/asr_endpoint.yaml}

1. Pair Clip with SenseCraft Voice App.
2. Open **AI CONFIG** and choose `local_whisper`.
3. Set Base URL to `http://<deployment-device-IP>:18621`; enter the access key provided by the platform administrator.
4. Tap **Test Connection**, then save after it succeeds.

[See the Clip pairing and app instructions](https://wiki.seeedstudio.com/respeaker_clip/)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Test Connection fails | Check the Base URL is `http://<deployment-device-IP>:18621`, that the phone can reach that address, and that port 18621 is not blocked |
| Access key rejected | Re-enter the access key exactly as provided by the platform administrator |
| Clip does not pair | Follow the Clip pairing instructions linked above |

## Step 3: Open the dashboard {#admin_web type=web_dashboard required=false config=devices/admin_web.yaml}

Open the dashboard and sign in to view and manage recordings.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not load | Check the platform deployment finished successfully and the `voice-web` container is running and its port reachable |
| Cannot sign in | Confirm the dashboard address and the login details from the platform deployment |

## Step 4: Try a recording {#verify_stack type=manual required=true verify=true config=devices/verify_stack.yaml}

Record a short clip and upload it from your phone. Confirm that the recording and its text appear in the dashboard.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The upload does not appear in the dashboard | Confirm Test Connection succeeded in Step 2 and the app configuration was saved |
| The recording appears without text | Check the `speech` service container is running on the server |

[Detailed instructions and troubleshooting](https://wiki.seeedstudio.com/solutions/smart-retail-voice-ai-solution-1/)
