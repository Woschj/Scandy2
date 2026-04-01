# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-01 - [Global Search Shortcuts]
**Learning:** When implementing global keyboard shortcuts (e.g., '/' to focus search), ensure the event listener excludes triggers when the user is already focused on 'INPUT' or 'TEXTAREA' elements to avoid interrupting active text entry.
**Action:** Always check `document.activeElement.tagName` before triggering global shortcuts.

## 2026-04-01 - [Dynamic Search Feedback]
**Learning:** Using a `MutationObserver` on `table tbody` (observing `attributes` for `style` updates) is a robust way to dynamically update search feedback (counts, empty states) without tightly coupling the feedback logic to the filtering logic.
**Action:** Use `MutationObserver` for decoupled UI updates based on element visibility changes.
