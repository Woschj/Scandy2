# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-04-02 - [Dynamic List Search Feedback]
**Learning:** When implementing client-side list filtering, visual hiding of rows is insufficient for screen reader users. Providing an `aria-live` region that announces the result count and a clear 'no results' empty state significantly improves the experience.
**Action:** Always include an `aria-live` status region and a dedicated empty state row when implementing searchable tables.
