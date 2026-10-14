# Handwriting collector design QA

## Evidence

- Source visual truth:
  - `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/a0f1474a118f7f8d0ed535afdbc4a105.jpg`
  - `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/9afea13526c613ca3fa78741c528a57d.jpg`
  - `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/c0fc21b97344efe209cb4527f5a5c93b.jpg`
  - `D:/微信/xwechat_files/wxid_u8a6juweabdr22_5f17/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/a108800db9a864ee1eb4111481f7c00f.jpg`
- Source dimensions: 2624 × 1744 px each. These are wide storyboard sketches containing a centered phone screen, not literal phone viewport captures.
- Implementation screenshot evidence: browser-rendered captures from Codex in-app browser tab 1 at `http://localhost:5173/`. The browser provider supplied non-file-backed screenshots for the entry, questionnaire, writing, and success states.
- Viewports checked:
  - Mobile: 390 × 844 CSS px, device pixel ratio 1; body and collector width 390 px with no horizontal overflow.
  - Tablet: 768 × 1024 CSS px, device pixel ratio 1; collector width 560 px, centered at x=104, document scroll width 768 px.
  - Desktop: default in-app browser viewport; centered 560 px collection card.
- Density normalization: the storyboard was compared for structure, hierarchy, and flow rather than pixel scale. Implementation screenshots were judged at their native CSS viewport density.

## Full-view comparison

The implementation preserves the four intended stages: collection entry, editable anonymous ID with automatically sequenced round, paged questionnaire with progress, and a task-led writing canvas with confirmation. Mobile uses the whole viewport; larger screens preserve the narrow centered collection surface shown in the sketches.

The hand-drawn wireframe did not define final brand typography, color, spacing tokens, or component styling. The implementation intentionally applies the existing MindLine green/cream system while retaining the source information architecture.

## Focused-region comparison

- Participant identification: editable ID, read-only automatically generated round, and primary start action are present. A required consent confirmation was added because the flow collects sensitive research data.
- Questionnaire: progress, question title, five selectable values, previous/next controls, selected state, and validation feedback were verified.
- Writing collection: task title, prompt, large writing area, live input/point/stroke/pressure feedback, clear/retry control, and confirm action were verified.
- Completion: browser-local persistence and JSON export were completed in the end-to-end interaction test.

## Required fidelity surfaces

- Fonts and typography: existing project font stack is retained; headings have clear mobile hierarchy and wrap without clipping.
- Spacing and layout rhythm: mobile controls remain visible, tap targets are at least 48 px, and tablet/desktop layouts remain centered without horizontal overflow.
- Colors and tokens: MindLine green, warm paper, lime primary action, warning, and muted text colors are consistent and have readable contrast.
- Image quality and assets: the source contains no production image assets; no placeholder image, custom SVG, or decorative raster substitute was introduced.
- Copy and content: wording is standalone, explains privacy limits, and avoids diagnostic claims.
- Accessibility: semantic labels, visible focus states, radio-group semantics, reduced-motion handling, and touch-action isolation on the canvas are present.

## Findings

- No actionable P0, P1, or P2 visual or interaction mismatch remains.

## Comparison history

1. Initial end-to-end pass found a P0 task-transition failure caused by cloning reactive point objects. The snapshot now converts each point to a plain object; the complete three-task flow was rerun successfully.
2. The next completion pass found a P0 persistence failure caused by reactive trace objects reaching IndexedDB. Attempts are now converted to plain serializable records; local persistence and JSON download then completed successfully.
3. Post-fix mobile, tablet, and desktop checks found no clipping, horizontal overflow, hidden primary action, or new console error.

## Follow-up polish

- P3: a later field test on the exact target tablet and stylus should confirm physical writing-area comfort and pressure compatibility; this is hardware validation rather than a current visual defect.

## Implementation checklist

- [x] Four-stage flow matches the storyboard structure.
- [x] Mobile, tablet, and desktop proportions checked.
- [x] Main inputs, navigation, validation, canvas collection, persistence, and export work.
- [x] Browser console checked after fixes.
- [x] No actionable P0/P1/P2 findings remain.

final result: passed

