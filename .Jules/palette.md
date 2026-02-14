## 2026-02-14 - Accessibility and Semantic Improvements in Layout

**Learning:** DaisyUI v4 recommends using `<button type="button">` instead of `<label>` for dropdown triggers. Additionally, theme variables (like `--p` for primary) are stored as raw values and should be wrapped in `oklch()` when used in custom CSS. Focus-visible styles are critical for keyboard navigation in custom sidebar components.

**Action:** Always prefer `<button>` for interactive elements and ensure color variables are correctly wrapped in their color space function (e.g., `oklch()`) in CSS blocks. Always provide `:focus-visible` styles for custom navigation items.
