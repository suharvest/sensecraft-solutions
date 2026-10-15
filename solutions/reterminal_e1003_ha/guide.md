## Preset: Configure E1003 {#usb_candidate}

Connect the device and enter the light to control. The App checks and installs firmware when needed.

> Disabled technical demo candidate. This manual review step does not configure hardware; formal execution awaits public App contract 15 synchronization, a compatible App and firmware download URL.

## Step 1: Configure E1003 {#review_setup type=manual required=true verify=true config=devices/review_setup.yaml}

In a compatible test App, click **Save settings** and wait for **Settings saved and verified**.

### Setup

1. Enter “Light controlled by the buttons”: copy its <code>light.*</code> ID from HA entity settings, such as <code>light.bedroom</code>. Input is manual; there is no automatic light discovery.
2. Click **Save settings**. The App checks firmware and installs it only when needed, then saves and verifies settings. There is one flow with no compilation or flash-mode choice.
3. Keep power connected through “Check device → Save settings → Restart and verify.” Saving requires at least 65 seconds; zero seconds or “Restarting” is not success.

<details>
<summary>Wi-Fi: leave blank to keep a saved network</summary>
<p>Leave the name and password blank to reuse the saved network. This does not mean the App detected the device's current network. For first setup or a network change, enter the 2.4 GHz Wi-Fi name and password.</p>
</details>

<details>
<summary>Technical details and release dependencies</summary>
<p>Reference firmware 0.2.1 is fixed plaintext-only, with no encryption or API key controls. Public contract 5 provides only this manual review step; App contract 15 is committed at a597ccad, pending public content synchronization.</p>
<p>Factory size: 1,337,072 B. SHA-256: <code>23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528</code>. Use 115200, offset 0x0, no full-chip erase and retain NVS. Formal execution also needs a compatible App and public firmware URL.</p>
<p>Build/software and UI checks passed; final 0.2.1 hardware upload, new Wi-Fi, upgrade/migration, sustained plaintext operation, physical touch, real HA control and display synchronization remain pending acceptance.</p>
</details>

### Prerequisites

Have a USB data cable and an HA dimmable light. Keep the computer, device and HA on the same reachable LAN.

### Wiring

1. Connect the E1003 carrier's USB-UART port to the computer.
2. Select the device port; use “Refresh” in the same row if needed.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device missing | Refresh, check the data cable and close tools using the port |
| Setup failed | Resolve the displayed error and retry; do not erase NVS |
| Saving or verification continues | Keep power connected until the final result |
| Light or display does not respond | Check the light ID, dimming support and HA action permission; touch/control remain pending acceptance and state synchronization needs a Blueprint or adapter |

### Deployment Complete

Continue only after **Settings saved and verified** appears in the compatible App.

1. Use the displayed **Device address** to add an ESPHome device in HA, without an API key.
2. Allow the device to perform Home Assistant actions.
3. Test on/off and 25/50/75/100% brightness, then close the App and repeat. Only these five zones have bindings; saved settings do not verify real control or display synchronization.
