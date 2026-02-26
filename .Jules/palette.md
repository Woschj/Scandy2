# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-21 - [Surgical Fixes for Mixed Line Endings]
**Learning:** In repositories with mixed line endings (CRLF/LF), using global reformatting tools like `dos2unix` creates large, noisy diffs that violate "micro-UX" constraints. Targeted `sed` commands or precise search blocks are preferred for minimal, safer changes.
**Action:** Use `sed` for single-line tag fixes and keep `replace_with_git_merge_diff` blocks as small as possible.
