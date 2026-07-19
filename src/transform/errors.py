"""
Shared exception types for src/transform/.

Any ValidationError (or subclass) raised here should be treated by the
caller as a pipeline FAILURE per docs/04-etl-pipeline-design.md's
"Failure vs. Warning: MVP Thresholds" -- specifically:
    "file is not valid JSON"
    "file is empty / zero records parsed"
    "a required field (id_product, and name for catalogs) is missing on a row"

Warnings (missing product matches, category mismatches, etc.) are NOT
represented as exceptions here -- they don't block loading, so they belong
in the data-quality-check layer (sql/checks/, or src/load/'s post-load
checks), not in transform-time validation.
"""



from typing import Any, Dict, Optional

class ValidationError(Exception):
    """Raised when a raw source file fails MVP validation."""

class RecordValidationError(ValidationError):
    """A single record within a raw file failed a required-field check."""

    def __init__(
        self,
        message: str,
        record_index: Optional[int] = None,
        raw_record: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.record_index = record_index
        self.raw_record = raw_record