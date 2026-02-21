# Palette's Journal - UX & Accessibility Learnings

## 2026-02-21 - Search Bar 'Clear' Button UX
**Learning:** Search inputs in complex data lists significantly benefit from a persistent 'Clear' button that appears only when text is present. This reduces user friction during multi-step filtering workflows. Keyboard accessibility must be maintained by returning focus to the input after clearing and providing descriptive ARIA labels.
**Action:** Implement 'Clear' buttons using absolute positioning within the input container and ensure triggering an 'input' event (or manual DOM update) to refresh filtered lists immediately.
