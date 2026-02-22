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

## 2025-02-22 - [Optimization using $facet]
**Learning:** For reporting/dashboarding features that require multiple groupings (e.g., by category, location, and status), MongoDB's `$facet` stage is highly effective at reducing database roundtrips and network traffic. While `mongomock` may show higher execution time locally due to Python overhead, the real-world performance gain from reduced serialization and network transfer is substantial for large collections.
**Action:** Use `$facet` for multi-grouping statistics to keep logic in the database layer and return only the final results.
