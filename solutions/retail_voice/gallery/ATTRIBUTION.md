# Gallery attribution

This gallery is the union of the two packages merged into `retail_voice` on
2026-09-07, one per preset. Every file shared by both was byte-identical, so
nothing had to be reconciled.

Six of the seven files were copied byte-for-byte from
`solutions/smart_retail_voice_ai/gallery/`, the earlier cloud-connected package
for the same hardware. Nothing was regenerated, retouched or re-rendered, so the
provenance below is inherited from that package rather than established here.
SHA-256 of the copies, recorded so a later divergence is visible:

| File | SHA-256 |
|---|---|
| `respeaker.jpg` | `11fed631e50e04c036edaa5a85eb00e78d12f47e06b0b55a94c0b1e5f06cb42a` |
| `rerouter.png` | `0e42a28031b480f9867a7081af251729c9520ed6bc44fddc33dc835ecc12e95e` |
| `recomputer-rk3576.jpg` | `18c81f01025ecd90844f8d009418657a357928f05c37bfd63433ac4a6a8ed7e4` |
| `architecture.png` | `0635d0f1e7ac393dded8649467a144afca24d9cf57ccb635494c7541726b57f3` |
| `cover.webp` | `f028d0e5392d7276220bdf70aa6062cdcbee3c721d242dbb0d5fd8d50a33315d` |
| `wan_lan.png` | `d86a47574dd2db5fbaf665689c73730f046e44a74f956718547c91441489dcdc` |
| `boot-mode.png` | `25b34b87ecfca7f4100db9808fbd324e5d60e1e2819a4baa99815b2830e8a32c` |

## What each file shows

- **`recordings-console.png`** — the SenseCraft Voice recordings console
  (录音管理), showing the transcript list with speaker labels (顾客 A / 店员 B /
  顾客 C / 店长 D), per-record status (中间结果 / 最终结果) and PII placeholders
  ([[NAME]], [[PHONE]], [[LOCATION]]) already redacted. It is the cover and
  leads the gallery — see the 2026-09-08 note below.
- **`architecture.png`** — despite the name, a flat-lay photograph of the actual
  kit: a reRouter CM4, its power supply, a USB cable and a reSpeaker XVF3800.
  No longer the cover (see 2026-09-08 note) but kept in the gallery — it shows
  the hardware, not the software, so it still adds information the console
  screenshot doesn't.
- **`respeaker.jpg`** — Seeed product photography of the reSpeaker XVF3800,
  the array both presets use.
- **`rerouter.png`** — Seeed product photography of the reRouter CM4.
- **`recomputer-rk3576.jpg`** — official product photography for reComputer
  RK3576-30 (SKU 100052518, family `recomputer_rk3576`), downloaded 2026-09-07
  from the Seeed media CDN:
  <https://media-cdn.seeedstudio.com/media/catalog/product/cache/961a49e1875f8c1f40e5990d74e68365/2/-/2-rk3576.jpg>
  (product page <https://www.seeedstudio.com/reComputer-RK3576-30-p-6815.html>).
  First-party Seeed material. It replaced `voice-web-recordings.png`, an
  admin-console screenshot that showed an empty dataset (all counters zero,
  "No data" table).
- **`cover.webp`** — a reRouter and a reSpeaker on a table in a shop. Not
  referenced by `intro.cover_image` or `intro.gallery` any more; see the
  2026-09-07 note below. The file stays in this directory.
- **`wan_lan.png`**, **`boot-mode.png`** — wiring and boot-jumper diagrams used
  by the reRouter firmware step in the guide.

The earlier packages' client screenshots were **not** carried over. They were
taken against builds whose pages differ from what these two presets deploy, and
a gallery image that shows a UI the user will not see is worse than no image.

## Provenance limits

These are Seeed first-party product and setup images as far as the upstream
package records; no third-party dataset or licensed footage is involved, and no
identifiable person appears in any of them. What is **not** established here:
the original photographer, the shoot date, and whether any of them were produced
under a contract with usage limits. Nothing in the earlier packages documented
that, and this file does not invent it. If these images move to a context where
that matters, confirm with whoever produced them.

None of these images is evidence of measured behaviour. Every number quoted on
the solution page comes from the sources cited in `description.md`, not from a
screenshot.

## 2026-09-07 — cover changed

The cover was `cover.webp`, a picture of a reRouter and a reSpeaker on a table
in a shop. Whatever its origin, it does not read as a photograph: the laptop
keys and the shelving behind it do not hold up at full size, and this page
cannot carry a rendered scene as its cover. It is no longer referenced by
`intro.cover_image` or `intro.gallery`; the file stays in this directory.

The cover is now `architecture.png` — despite the name, a flat-lay photograph
of the actual kit (reRouter CM4, power supply, USB cable, reSpeaker XVF3800),
first-party Seeed material, unmodified.

**Still missing (as of 2026-09-07):** a photograph of the kit installed at a
counter, and a console screenshot showing real transcripts. The only console
screenshots available in this repository
(`solutions/smart_retail_voice_ai/gallery/edge-client*.png`) show an empty
transcript list and belong to a different package.

## 2026-09-08 — cover changed again, to a real console screenshot

`architecture.png` is a photograph of the hardware kit, not of the software.
It doesn't tell a reader what the demo does — retail voice transcription —
without reading the caption, and the project rule for this page set is that
the cover must communicate that on sight. Hardware flat-lays and architecture
diagrams are both excluded as covers under that rule.

The cover is now `recordings-console.png`: the SenseCraft Voice recordings
console (`sensecraft_voice/sensecraft-voice-web`, page `/recordings`),
captured at 3200×2000 px (1600×1000 CSS viewport, device scale factor 2) with
Playwright, using the repository's own `scripts/shot-recordings.mjs` fixture
data adapted for a higher-resolution capture
(`scripts/shot-cover.mjs`, not committed to that repo — a one-off local
script). SHA-256: `5e48deb5dbc746e77bd44d6d0d4788ce010fd3edb2a0de158d104426141d8317`.

Source of the on-screen content:
- The console itself was run locally (`npm run dev`) against the real
  frontend build, so the chrome, layout and Chinese copy are the shipped UI,
  not a mockup.
- The table rows are not real customer recordings. Per the source script's
  own comment, the backend API was stubbed with `page.route()` so the
  screenshot "不依赖真实环境，也不会把真实 PII 截进图里" (doesn't depend on a
  real environment and doesn't capture real PII into the image). No live
  microphone, no real store, no real customer or employee is behind any row.
  The transcript text is placeholder retail dialogue the fixture authors
  wrote for this purpose, with `[[NAME]]`, `[[PHONE]]`, `[[LOCATION]]` already
  in the redacted placeholder form the real pipeline produces after PII
  removal — i.e. the redaction *format* shown is real, the *conversations*
  are not.

`architecture.png` stays in the gallery (see "What each file shows" above) —
it still documents the physical kit, just no longer as the cover.
