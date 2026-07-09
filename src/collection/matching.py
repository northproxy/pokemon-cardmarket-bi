"""
Matching logic, in order: exact idProduct (if provided) -> exact name match
-> needs_review. A providedIdProduct that doesn't resolve locally does NOT
fall back to a name match (intentional) -- see docs/08.
matchConfidence: 1.00 exact id, 0.90 exact name, 0.00 attempted/no match,
null not attempted yet.

TODO (Phase 5): implement match_staging_row()
"""
