# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-15 - [Dynamic Search Feedback & Shortcuts]
**Learning:** Client-side list filtering needs both visual (empty states) and non-visual (ARIA-live) feedback to be truly accessible. Global keyboard shortcuts like '/' significantly improve efficiency but must be scoped to exclude active input elements to prevent UX "hijacking".
**Action:** Include `aria-live` regions for results counts and `colspan="100"` empty rows in all list views. Always check `document.activeElement` before triggering global shortcuts.
