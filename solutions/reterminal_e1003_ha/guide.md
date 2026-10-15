## Preset: Configure E1003 {#usb_candidate}

Connect the device and enter the light to control. The App checks and installs firmware when needed.

> Technical demo candidate; formal deployment is not open yet. These instructions are for a compatible test App.

## Step 1: Connect the device {#flash_panel type=manual required=true config=devices/review_flash.yaml}

Connect USB and select the device port.

### Prerequisites

Have a USB data cable and an HA dimmable light. Keep the computer, device and HA on the same reachable LAN.

### Wiring

1. Connect the E1003 carrier's USB-UART port to the computer.
2. Select the device in the port row; click “Refresh” in the same row if the list is stale.
3. Enter “Light controlled by the buttons”: copy its <code>light.*</code> ID from HA entity settings, such as <code>light.bedroom</code>. This is manual input, not automatic light discovery.

<details>
<summary>Wi-Fi: leave blank to keep a saved network</summary>
<p>Leave the name and password blank to reuse the device's saved network. This does not mean the App has detected its current network.</p>
<p>For first setup or a network change, enter the 2.4 GHz Wi-Fi name and password. Password input is masked.</p>
</details>

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device missing | Refresh, check the data cable and close tools using the port |
| Unsure which light to enter | Copy the light's ID starting with <code>light.</code> from HA entity settings |

## Step 2: Configure E1003 {#configure_panel type=manual required=true config=devices/review_setup.yaml}

Click **Save settings** and keep power connected.

Wait through “Check device → Save settings → Restart and verify.” If a save countdown is shown, wait for it to finish. The final success message is **Settings saved and verified**.

<details>
<summary>Technical details</summary>
<p>The App checks firmware project, version and hardware, installing the precompiled image when needed. There is one setup entry, with no user compilation or flash-mode preset choice.</p>
<p>Reference firmware 0.2.1 is fixed plaintext-only and requires App contract 14. There is no encryption choice or API key input/copying. Keep power connected for at least 65 seconds after the last write, then restart and read back.</p>
<p>Firmware size: 1,337,072 B. SHA-256: <code>23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528</code>. Flash at 115200, offset 0x0, with no full-chip erase and NVS retained. Upgrade and migration still need acceptance on this release.</p>
<p>The formal candidate remains disabled. Public contract 5 manual review steps do not write to devices. Build and software checks passed, but final 0.2.1 hardware upload has not begun. Formal execution needs public contract 14, a compatible App and a firmware download URL.</p>
</details>

### Troubleshooting

| Issue | Action |
| --- | --- |
| Setup failed | Resolve the current error and retry; do not erase NVS or delete recovery records |
| Saving or verification continues | Keep power connected and wait for the final result; “Restarting” is not success |

## Step 3: Verify after saving {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

Continue only after the App shows **Settings saved and verified**.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Light does not respond | Check its ID, dimming support and HA action permission; touch and real control still need acceptance |
| Display does not follow the light | Dynamic state and brightness synchronization still need a HA Blueprint or adapter |

### Deployment Complete

1. Use the **Device address** shown after success to add an ESPHome device in HA, without an API key.
2. Allow the device to perform Home Assistant actions.
3. Test on/off and four brightness levels, then close the App and repeat. Only these five zones have bindings; saved settings do not verify real control or display synchronization.
