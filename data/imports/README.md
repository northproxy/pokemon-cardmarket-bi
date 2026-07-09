# data/imports/ (LOCAL ONLY — gitignored)

Personal filing convenience for collection CSV/Excel files you're working
with — NOT a second source of truth. The real status of an import row
lives in collection_import_staging.matchStatus (see
docs/08-collection-import-flow.md); these folders are just where you keep
the files themselves before/after running an import.

    collection/incoming/    files you haven't imported yet
    collection/processed/   files whose batch fully resolved
                            (ready_to_import / imported)
    collection/failed/      files whose batch had rows that ended in
                            needs_review / error and still need attention

A file can move to processed/ even if a few rows are sitting in
waiting_for_product — that's an expected timing state, not a failure.
