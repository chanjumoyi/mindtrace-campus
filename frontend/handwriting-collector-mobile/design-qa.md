# Design QA

## Source visual truth

- `C:/Users/acer1/AppData/Local/Temp/codex-clipboard-2568a2d7-c5a5-4218-aa06-0464a786a225.png`
- `C:/Users/acer1/AppData/Local/Temp/codex-clipboard-4b555763-af4f-4ceb-b212-d9a45a3abb96.png`
- `C:/Users/acer1/AppData/Local/Temp/codex-clipboard-a64e58bb-8563-4f3a-bb21-ff7be2d7740d.png`

## Implementation evidence

- Browser-rendered implementation: `http://localhost:5174/`
- Verified in the Codex in-app browser with the iPhone device preview at 393 × 852 CSS px.
- Captured and visually inspected the participant identity page and the first questionnaire item after the implementation build.
- Inspected the completion-state markup and automated assertions for removed participant-facing metadata.

## Full-view comparison evidence

- Participant identity keeps the anonymous ID and automatic test number, but no longer displays the redundant locked-ID explanation marked in the source screenshot.
- Questionnaire keeps the question number, wording, frequency choices, progress, and navigation while removing the scoring-domain label marked in the source screenshot.
- Completion keeps only the success state, export action, and save result; the explanatory paragraph and hidden-data card marked in the source screenshot are absent.
- At the iPhone preview size, the visible hierarchy remains complete without overlap, clipping, or additional page scrolling.

## Focused region comparison evidence

- Identity card: the ID remains visually anchored in the same card and the removed third line does not leave an awkward gap.
- Question card: removing the domain label moves the question text into the natural first content row without affecting option spacing.
- Completion content: the success title and export action remain centered and balanced after the note block is removed.
- No source logos, illustrations, or raster assets were required for this change.

## Required fidelity surfaces

- Typography: existing hierarchy and mobile-readable line lengths preserved.
- Spacing: affected cards collapse naturally around the remaining content.
- Color and tokens: warm paper background, dark green actions, and selected states unchanged.
- Copy: no questionnaire score grouping, result implication, or internal data-handling explanation is shown to participants.
- Writing prompt: selected from one positive, questionnaire-independent pool; the same selected sentence is presented twice.

## Interaction and accessibility checks

- In-app browser DOM checks confirmed the removed identity and questionnaire text is not present.
- Automated flow test confirms the hidden labels stay absent during normal navigation.
- Prompt-pool tests confirm nine alternatives, 19–20 Chinese characters each, and no questionnaire score/band metadata.
- Writing-quality tests confirm both supplied scribble-like copy samples and the supplied scribble-like free-writing sample are blocked by multiple independent signals.
- `npm run check:runtime`: passed.
- `npm run build`: passed.
- Relevant Playwright tests: 17 passed; full applicable suite: 29 passed.
- Sites packaging tests: 4 passed.
- The protected runtime's unrelated `BottomSheet remains mounted` test still times out because the document root intercepts its synthetic overlay click; the collector flow and all changed surfaces pass.

## Comparison history

- Pass 1: removed the three participant-facing metadata regions and separated prompt selection from questionnaire results.
- Pass 2: verified the identity and questionnaire pages in the in-app iPhone preview; no layout regression or residual red-box copy remained.
- Pass 3: added combined trajectory checks and regression fixtures based on the supplied invalid export and a prior character-like sample.

## Findings

- No actionable P0, P1, or P2 visual findings remain.
- Trajectory heuristics can reliably block the supplied obvious scribbles but are not semantic handwriting recognition; borderline records should retain QC flags for review.

## Implementation checklist

- [x] Remove locked-ID helper copy.
- [x] Remove questionnaire scoring-domain label.
- [x] Remove completion-page collection explanation card.
- [x] Use questionnaire-independent positive copy prompts.
- [x] Keep two repeats of the same sentence.
- [x] Block obvious non-text scribbles using combined signals.
- [x] Preserve mobile layout and local JSON export.

final result: passed
