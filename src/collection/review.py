"""
Handles the review loop: needs_review / error / waiting_for_product are not
terminal -- re-validate and re-match after correction. Also handles
possible-duplicate detection (idProduct + language + condition + purchaseDate
+ purchasePrice match against existing collection_items). See docs/08.

TODO (Phase 5): implement re_evaluate_staging_row()
"""
