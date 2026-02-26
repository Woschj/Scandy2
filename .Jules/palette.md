# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-26 - [Robust UI State Toggling]
**Learning:** Programmatic visibility toggles (e.g., "Clear Search" buttons) should favor inline `style.display = 'none'/'block'` over utility classes like Tailwind's `.hidden`. This avoids specificity conflicts and ensures correct behavior in environments where CSS might not be fully loaded or processed, such as during automated UI verification.
**Action:** Use inline styles for JavaScript-driven visibility changes on critical UI feedback elements.
