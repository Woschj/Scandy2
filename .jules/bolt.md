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

## 2026-03-15 - [LendingService Validation N+1 Optimization]
**Learning:** `validate_lending_consistency` and `fix_lending_inconsistencies` contained severe N+1 query bottlenecks where `mongodb.find_one` was called inside loops over the entire `tools` collection and inside loops over orphaned lendings. Given typical dataset sizes, this forces thousands of individual database queries for a single validation run.
**Action:** Replaced the iterative `find_one` lookups with two single batch O(1) queries (`tools` and active `lendings`), mapped them into memory dictionaries and sets, and resolved the inconsistencies natively in Python. The validation time dropped from ~3.3 seconds to ~0.03 seconds.
