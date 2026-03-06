# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-03-06 - [Unified List Filtering Pattern]
**Learning:** Centralizing list filtering logic in a base template using a standard naming convention for filter IDs (e.g., ending in `Filter`) and matching them to `data-` attributes on rows significantly reduces code duplication and ensures a consistent UX across all listing pages.
**Action:** Use the `[key]Filter` ID pattern for dropdowns and `data-[key]` attributes on table rows to enable automatic filtering via the shared `updateSearch` logic.

## 2025-03-06 - [Accessible Icon-Only Buttons]
**Learning:** Icon-only action buttons (like Edit/Delete) must always have an `aria-label` for screen readers and a `title` attribute for mouse-over tooltips to be fully accessible and user-friendly.
**Action:** Always provide both `aria-label` and `title` for icon-only interactive elements.
