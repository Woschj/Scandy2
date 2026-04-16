# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-05-15 - [List View Feedback Pattern]
**Learning:** Centralized result feedback (counters and empty states) should leverage existing semantic markers like the `.data-row` class. Keeping these enhancements within the base template ensures consistency and keeps changes surgically small (< 50 lines) while avoiding logic duplication across specialized views.
**Action:** Use global UI update functions in base templates to synchronize search results across all inheriting views.
