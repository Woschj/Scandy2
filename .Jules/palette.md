# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-23 - [Micro-UX: Maintainable Diffs in Legacy Templates]
**Learning:** When working with legacy templates that use CRLF line endings, performing full-file conversions (like `dos2unix`) results in massive, unreviewable diffs. For micro-UX improvements, it is critical to preserve original line endings to keep the PR focused on semantic changes.
**Action:** Use `dos2unix` only temporarily for patching, or use targeted tools like `sed` to modify specific lines while respecting original formatting. Always verify diff size before submission.
