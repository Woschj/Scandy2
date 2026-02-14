## 2025-01-24 - [Aggregation Pipeline Optimization]
**Learning:** In MongoDB aggregation pipelines, performing joins ($lookup) and unwinding ($unwind) on the entire collection before sorting and limiting is a major performance anti-pattern. Moving $sort and $limit to the beginning of the pipeline (after initial $match) reduces the workload from O(N) joins to O(Limit) joins.
**Action:** Always check if $sort and $limit can be moved before $lookup in aggregation pipelines.

## 2025-01-24 - [Global MongoDB Initialization in Flask]
**Learning:** Performing global initialization of database connections in route modules (e.g., `mongodb = MongoDB()` at module level) can cause issues during test collection if the test environment doesn't have a running database and isn't using a lazy-loading pattern correctly.
**Action:** Favor lazy-loading for database connections or ensure mocks are applied before importing route modules.

## 2025-01-24 - [Docker Tag Formatting in CI]
**Learning:** Docker tags cannot start with a hyphen. Using `type=sha,prefix={{branch}}-` in `docker/metadata-action` can result in an invalid tag like `:-sha` if `{{branch}}` is empty (e.g., during a pull_request event).
**Action:** Use standard SHA tagging (e.g., `type=sha`) or ensure prefixes are never empty and don't lead to leading hyphens.

## 2025-01-24 - [CI Efficiency with Metadata Action]
**Learning:** Manually pulling, tagging, and pushing images to update a "latest" tag in GitHub Actions is inefficient. `docker/metadata-action` can handle multiple tags (including `latest` conditionally) in a single pass, which `build-push-action` can then push efficiently.
**Action:** Consolidate all tagging logic into `docker/metadata-action` to speed up CI and reduce bandwidth usage.
