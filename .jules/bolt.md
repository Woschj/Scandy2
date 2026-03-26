## 2025-07-14 - [Initial Journal]
**Learning:** Found a recurring performance anti-pattern where $lookup and $unwind are used before $sort and $limit in MongoDB pipelines.
**Action:** Prioritize moving $sort and $limit as early as possible in aggregation pipelines to reduce join workload.
## 2025-07-14 - [Aggregation Optimization Strategy]
**Learning:** When moving $sort and $limit before $lookup, using 'preserveNullAndEmptyArrays: True' in $unwind and $ifNull in $project ensures that data integrity is maintained and no documents are unexpectedly filtered out, while still benefiting from the performance gain of a smaller join workload.
**Action:** Always use this pattern when optimizing Top-K queries to ensure consistent results.

## 2025-07-14 - [Aggregation for Activity Feeds]
**Learning:** Replacing loop-based lookups (N+1 queries) with single aggregation pipelines in `get_recent_activity` reduces database roundtrips by over 90% (from 42 queries to 2). Using `$unwind` without `preserveNullAndEmptyArrays` effectively replicates `if tool and worker:` filtering logic in the database layer.
**Action:** Apply similar aggregation patterns to other feed-like features (e.g., `manual_lending` in `app/routes/admin/system.py`).
## 2025-05-15 - [Optimization with Aggregation Pipelines]
**Learning:** This codebase frequently uses N+1 query patterns in service methods (e.g., looping through results and calling find_one). These can be significantly optimized using MongoDB aggregation pipelines with $lookup. However, mongomock (used in the test suite) has limited support for advanced $lookup features like 'let' and sub-pipelines.
**Action:** Use simple $lookup (localField/foreignField) when possible to maintain test compatibility, and handle any additional filtering or data processing in Python if necessary, which still provides a massive performance win by reducing database roundtrips to 1.

## 2026-03-14 - [Efficient ID/Number Generation]
**Learning:** Found an O(N) bottleneck where the application scanned the entire collection to determine the next sequential ID (`job_number`).
**Action:** Replace full-collection scans with a sorted query (`sort=[('field', -1)], limit=1`) and ensure a unique index exists on that field to provide O(1)/O(log N) lookup and guarantee consistency.
## 2026-03-15 - [LendingService N+1 Optimization]
**Learning:** Multiple methods in `LendingService` (active lendings, recent usage, history) were performing N+1 database queries. These can be optimized into single aggregation pipelines using `$lookup`.
**Action:** Use aggregation for joined data. In Top-K queries like `get_recent_consumable_usage`, place `$sort` and `$limit` BEFORE `$lookup` to minimize the join workload and improve memory efficiency.

## 2024-05-19 - [Route-level N+1 Query Aggregation Optimization]
**Learning:** N+1 queries embedded within route-level Python loops (e.g., retrieving `tool` and `worker` via `mongodb.find_one()` inside a `for` loop) can be reliably replaced by MongoDB aggregation pipelines using `$lookup` and `$unwind`. In `app/routes/admin/system.py`, replacing these loops with an aggregation pipeline successfully and robustly eliminates the N+1 problem without altering the intended output behavior (because `$unwind` simulates an inner join). Using `.get('field', fallback)` when reconstructing dictionaries from the pipeline output safeguards against `KeyError` crashes.
**Action:** When finding manual loops over database records that trigger additional queries per iteration, extract the logic into a single `$lookup`-based aggregation pipeline. Always use `.get()` to handle the result map defensively. Remember to delete temporary benchmark scripts before requesting code review or submitting.

## 2026-03-16 - [Aggregation Index Usage and Correctness]
**Learning:** In `AdminDashboardService`, use direct `$match` on indexed fields at the start of aggregation pipelines instead of normalising with `$addFields` first, as the latter prevents index usage and forces a collection scan. Additionally, using `$expr` for field-to-field comparisons (e.g., `quantity` <= `min_quantity`) allows for dynamic logic while still potentially benefiting from compound indexes on those fields.
**Action:** Always place `$match` on indexed fields as the first stage. Ensure business logic (like low stock) uses correct field names and database-level comparisons rather than hardcoded Python values.

## 2026-03-22 - [Jinja2 Compatibility in Aggregations]
**Learning:** MongoDB aggregation pipelines often return date fields as strings if that's how they are stored, but Jinja2 templates in this app expect 'datetime' objects for formatting filters.
**Action:** Always perform manual date-string-to-datetime conversion in the Service layer after executing an aggregation pipeline to prevent UI regressions and template crashes.

## 2024-05-20 - [Consolidating Independent Counts with Aggregation]
**Learning:** Multiple independent `count_documents` calls on the same collection (e.g., for different statuses or priorities) create unnecessary network roundtrips. These can be consolidated into a single `$group` stage with conditional sums (`{'$sum': {'$cond': [...]}}`) or a `$facet` stage. In `AdminNotificationService`, this reduced 13 database calls down to 2.
**Action:** When a service method performs multiple count operations on the same collection, replace them with a single aggregation pipeline to minimize latency.
