# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-05-15 - [Empty State Actionability]
**Learning:** A "No results found" empty state should not just be a dead end; providing a "Reset filters" or "Clear search" action directly within the message significantly reduces user friction and encourages exploration.
**Action:** Always include a primary action (like resetting filters) in empty state placeholders for searchable or filterable lists.
