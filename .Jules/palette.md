# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2024-03-04 - [Unified List Filtering]
**Learning:** Centralizing search and filtering logic in a base template using data-attributes and a standardized naming convention (e.g., `#categoryFilter` matching `data-category`) reduces redundancy and ensures a consistent UX. It also simplifies adding new filters to child templates.
**Action:** Prefer the unified filtering pattern in `shared/list_base.html` for all data-heavy list views.
