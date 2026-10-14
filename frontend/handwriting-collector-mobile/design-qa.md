# Design QA

**Source visual truth**

- `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/a0f1474a118f7f8d0ed535afdbc4a105.jpg`
- `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/9afea13526c613ca3fa78741c528a57d.jpg`
- `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/c0fc21b97344efe209cb4527f5a5c93b.jpg`
- `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/a108800db9a864ee1eb4111481f7c00f.jpg`

**Implementation evidence**

- Browser-rendered local implementation: `http://localhost:5174/`
- Captured in the Codex in-app browser from `[data-testid="device-screen"]`.
- iPhone viewport: 393 × 852 CSS px, device scale 1, captured region 393 × 852 px.
- Pixel 10 viewport: 427 × 952 CSS px, device scale 1, captured region 427 × 952 px.
- Source images: 2624 × 1744 px design-note canvases. The embedded phone wireframes are conceptual rather than pixel-sized screen exports, so comparison used their hierarchy, sequence, and proportions rather than false pixel precision.
- State compared: writing collection screen, including header, progress, prompt, writing canvas, counters, clear action, and confirmation action.

**Full-view comparison evidence**

- The implementation preserves the source sequence: start → participant identity/automatic round → paginated current-state scale → writing collection → confirmation.
- The writing screen retains the source's dominant portrait writing area and bottom confirmation action while adding progress, task guidance, counters, and a clear action needed for real collection.
- The same screen was rendered at unscaled iPhone and Pixel 10 dimensions. No clipping, overlap, inaccessible controls, or broken text wrapping was observed.

**Focused region comparison evidence**

- A separate crop was not needed: at the required 1:1 iPhone capture, the prompt, writing surface, metadata row, and confirmation control were all legible in the full device-screen image.
- No source logos, illustrations, photos, or non-standard image assets required asset-level comparison.

**Required fidelity surfaces**

- Fonts and typography: a Kai-style display face is used for handwriting prompts, with a system sans-serif for controls and small text. Hierarchy and line lengths remain readable on both devices.
- Spacing and layout rhythm: the large writing surface remains the primary region; margins, progress, task label, prompt, metadata, and the 52 px confirmation control form a consistent vertical rhythm.
- Colors and visual tokens: warm paper background, dark green ink, soft sage progress/status treatments, and high-contrast action states preserve the hand-drawn, calm source intent.
- Image quality and asset fidelity: the source contains no app-specific raster imagery to reproduce. Device chrome comes from the protected mobile runtime rather than duplicated app content.
- Copy and content: standalone copy explains anonymity, local-only storage, non-diagnostic use, complete-sentence copying, and free writing without referring to the original website.

**Interaction and accessibility checks**

- Tested anonymous-ID validation, required consent, four required scale answers, three writing tasks, clear/rewrite, task advancement, IndexedDB save, and JSON export.
- Pointer samples include coordinates, normalized coordinates, elapsed time, timestamp, pressure, tilt, twist, contact size, input type, stroke ID, and coalesced-event flag.
- Disabled and selected states are visible; fields and controls have labels; primary controls meet practical mobile tap-target sizes.
- Browser console errors/warnings checked after iPhone and Pixel flows: none.
- `npm run check:runtime`: passed.
- The template's separate Playwright runtime suite could not launch because its bundled Chromium executable is not installed on this machine; the same core flow and both device layouts were exercised in the Codex in-app browser instead.

**Comparison history**

- Pass 1 found a P2 layout issue after text-field focus: the simulated keyboard could remain visually present and the device screen retained an internal scroll offset when entering collection.
- Fix: hide the keyboard dock whenever runtime state is closed and reset both the device screen and active app scroller when a new flow screen mounts.
- Pass 2 evidence: the 1:1 iPhone writing screen opened at the top with header, progress, prompt, full canvas, metadata, and confirmation visible. Pixel 10 also rendered the full interaction without clipping. No actionable P0/P1/P2 differences remain.

**Findings**

- No actionable P0, P1, or P2 findings remain.

**Open Questions**

- The sketches do not specify a final brand mark or production typography. The current text seal and system/Kai fallbacks are intentional prototype choices.

**Implementation Checklist**

- [x] Independent mobile project and URL.
- [x] Responsive iPhone and Android layouts.
- [x] Complete sentence and free-writing tasks.
- [x] Raw pointer/pressure/time capture.
- [x] Local persistence and JSON export.
- [x] Runtime integrity, build, interaction, console, and visual checks.

**Follow-up Polish**

- P3: replace the temporary text seal when a final product logo is available.

final result: passed
