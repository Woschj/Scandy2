# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-02 - [Defensive Global Keyboard Listeners]
**Learning:** Global keyboard shortcut listeners in shared templates (like `list_base.html`) must verify the existence of target elements *inside* the event handler. This prevents JavaScript `TypeError` crashes on pages that extend the template but omit or rename the target components.
**Action:** Always wrap element-specific logic within global event listeners in an existence check (e.g., `if (targetElement)`).
