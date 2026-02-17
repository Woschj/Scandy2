## 2026-02-17 - [Handling Line Endings in Templates]
**Learning:** The repository templates frequently utilize CRLF line endings. When using search-and-replace tools like `replace_with_git_merge_diff`, these line endings can cause patches to fail if not accounted for.
**Action:** Use `dos2unix` to convert files to LF before applying patches, or use tools like `sed` that are line-ending agnostic for surgical changes.

## 2026-02-17 - [Surgical Micro-UX Improvements]
**Learning:** Broad accessibility sweeps across multiple files can lead to large, noisy diffs and potential regressions in generated artifacts (like `main.css`).
**Action:** Focus on a single, high-impact micro-improvement (under 50 lines) to ensure a clean, reviewable, and safe contribution.
