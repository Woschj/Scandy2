# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-01 - [Standardized List Search UX]
**Learning:** List-based interfaces benefit greatly from a unified search experience that includes: 1) keyboard shortcuts (`/` for focus, `Esc` for clear/blur), 2) screen reader announcements via `aria-live` for result counts, and 3) empty state feedback ("No results") to prevent confusion when filters return zero matches. Using a `MutationObserver` on the `tbody` is a robust way to implement these enhancements without refactoring existing per-page filtering logic.
**Action:** Implement this three-tier search UX (shortcuts, status, empty state) in all centralized list components.
