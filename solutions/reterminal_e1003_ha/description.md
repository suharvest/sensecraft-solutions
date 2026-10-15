# E1003 Light Panel Setup Demo

Connect the device and enter the light to control. The App checks and installs firmware when needed.

This technical demo uses one form to set the light binding, with no compilation, configuration-file editing or API key entry.

## What to test

- Bind E1003 to one HA dimmable light.
- Check saving, restart and readback results.
- After saving succeeds, connect to HA and test panel control.

Only five zones define touch actions: on/off and 25%, 50%, 75% and 100% brightness. Other graphics have no click binding. Physical touch, HA control and display synchronization still need acceptance.

## Device and connection

USB handles device checks and network setup; the LAN carries settings and readback.

<details>
<summary>Technical details and verification status</summary>
<p>Reference firmware 0.2.1 is fixed plaintext-only, with no API encryption option or key copying. It uses ESPHome native API (TCP 6053), no MQTT or device web server, and USB-only updates.</p>
<p>Build and software checks passed, but final hardware upload has not begun. Earlier firmware results do not verify this release. E-paper retention after power-off does not prove touch-circuit power.</p>
<p>The formal candidate remains disabled pending public App contract 15 synchronization, compatible App distribution, a firmware download URL and hardware acceptance. The developer firmware retains encryption separately. Display state and brightness synchronization for arbitrary lights still need a HA Blueprint or adapter.</p>
</details>
