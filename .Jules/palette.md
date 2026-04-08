# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-08 - [Search Accessibility & Shortcuts]
**Learning:** Adding a keyboard shortcut hint like `( / )` to search placeholders significantly improves discoverability. Coupled with `aria-live="polite"` to announce result counts and a dedicated `#noResultsRow`, the search experience becomes much more accessible and intuitive for all users, especially those using screen readers.
**Action:** Include discoverable shortcuts and screen-reader-friendly status updates in all searchable list views.
