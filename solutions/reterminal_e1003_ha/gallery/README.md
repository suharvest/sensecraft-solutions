# E1003 visual assets

- `e1003-product-official.jpg`: unmodified official reTerminal E1003 product photo, 1800×1200. Model/SKU checked with `solution-cli product query reterminal_e_series --json` (E1003, 100090602). Source: [Seeed product page](https://www.seeedstudio.com/reTerminal-E1003-p-6731.html), [original image](https://media-cdn.seeedstudio.com/media/catalog/product/1/-/1-reterminal-e1003-epaper-display.jpg). The screen is Seeed's stock demonstration, not an acceptance photo of this firmware. Rights remain with Seeed Studio.
- `e1003-architecture-cover.png`: generated with Codex's built-in imagegen, then inspected. This is an architecture illustration, not a product photograph or a live App screenshot. It distinguishes USB setup, Wi-Fi/LAN and pending HA validation.

## Generation prompt

Create a polished wide 16:9 cover for an E1003 ESPHome runtime-configuration technical demo. Off-white background, charcoal text and green accent. Headline `E1003`, subtitle `One firmware. Runtime configuration.` Four schematic nodes: `DESKTOP APP`, `E1003`, `LOCAL NETWORK`, `HOME ASSISTANT`. Connect App to panel with `USB setup`, panel to network with `Wi-Fi`, network to HA with a dashed `HA validation pending` line. Show settings `Wi-Fi`, `Light entity`, `Device key`. Footer `Technical demo • No MQTT • No user compilation`. No real-time numeric data, cloud service or success badge.

Final refinement: use a simple neutral landscape e-paper schematic, remove invented leaf branding/tagline and decorative plants, preserve the original labels and connectors. The schematic does not assert the physical device geometry.
