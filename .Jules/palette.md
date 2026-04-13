# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-15 - [ARIA Live Feedback for Search]
**Learning:** When users filter lists, screen readers need explicit confirmation of the result count to understand the impact of their actions. An `aria-live="polite"` region that updates with the count (e.g., "5 results found") provides this essential feedback.
**Action:** Implement ARIA-live status regions for all client-side filtering and searching interfaces.
