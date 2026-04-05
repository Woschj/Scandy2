# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-05 - [Synchronized Search and Filter UX]
**Learning:** In list views with multiple filter sources (search text + dropdowns), independent filter logic leads to visual bugs where one filter overwrites the other. Unifying these through a centralized `applyFilters` logic ensures consistent results and correct "no results" state feedback.
**Action:** Always implement filtering as a holistic state-check function that combines all active criteria.
