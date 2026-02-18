## 2025-07-14 - [Initial Journal]
**Learning:** Found a recurring performance anti-pattern where $lookup and $unwind are used before $sort and $limit in MongoDB pipelines.
**Action:** Prioritize moving $sort and $limit as early as possible in aggregation pipelines to reduce join workload.
## 2025-07-14 - [Aggregation Optimization Strategy]
**Learning:** When moving $sort and $limit before $lookup, using 'preserveNullAndEmptyArrays: True' in $unwind and $ifNull in $project ensures that data integrity is maintained and no documents are unexpectedly filtered out, while still benefiting from the performance gain of a smaller join workload.
**Action:** Always use this pattern when optimizing Top-K queries to ensure consistent results.

## 2025-07-14 - [Aggregation for Activity Feeds]
**Learning:** Replacing loop-based lookups (N+1 queries) with single aggregation pipelines in `get_recent_activity` reduces database roundtrips by over 90% (from 42 queries to 2). Using `$unwind` without `preserveNullAndEmptyArrays` effectively replicates `if tool and worker:` filtering logic in the database layer.
**Action:** Apply similar aggregation patterns to other feed-like features (e.g., `manual_lending` in `app/routes/admin/system.py`).
## 2026-02-18 - [N+1 Query in Lending Feed]
**Learning:** Found a core N+1 bottleneck in LendingService.get_active_lendings where each active lending triggered separate tool and worker lookups.
**Action:** Replaced loop-based enrichment with a single MongoDB aggregation pipeline using $lookup. This reduces database roundtrips from 1+2N to 1, providing a major speed boost for high-volume environments.
