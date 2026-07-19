import datetime
from decimal import Decimal

import pytest

from src.transform.errors import RecordValidationError, ValidationError
from src.transform.price_guide import (
    extract_source_created_at,
    normalize_price_guide_record,
    transform_price_guide,
    validate_price_guide,
)

SNAPSHOT_DATE = datetime.date(2026, 7, 19)


def make_record(**overrides):
    base = {
        "idProduct": 12345,
        "idCategory": 7,
        "avg": "1.23",
        "low": "0.99",
        "trend": "1.50",
        "avg1": "1.10",
        "avg7": "1.20",
        "avg30": "1.30",
        "avg-holo": "5.00",
        "low-holo": "4.50",
        "trend-holo": "5.25",
        "avg1-holo": "5.10",
        "avg7-holo": "5.20",
        "avg30-holo": "5.30",
    }
    base.update(overrides)
    return base


class TestValidatePriceGuide:
    def test_accepts_bare_list_root(self):
        records = validate_price_guide([make_record()])
        assert len(records) == 1

    def test_rejects_empty_list(self):
        with pytest.raises(ValidationError):
            validate_price_guide([])

    def test_rejects_missing_id_product(self):
        with pytest.raises(RecordValidationError):
            validate_price_guide([make_record(idProduct=None)])

    def test_rejects_record_without_id_product_key(self):
        bad = make_record()
        del bad["idProduct"]
        with pytest.raises(RecordValidationError):
            validate_price_guide([bad])

    def test_price_fields_are_not_required(self):
        # avg/trend/etc. all missing -- should still pass, since only
        # idProduct is required per docs/04.
        record = {"idProduct": 1}
        records = validate_price_guide([record])
        assert records == [record]

    def test_wrapper_dict_root_is_accepted(self):
        records = validate_price_guide({"priceGuides": [make_record()]})
        assert len(records) == 1

    def test_unrecognized_root_shape_raises(self):
        with pytest.raises(ValidationError):
            validate_price_guide({"somethingElse": "not a list"})


class TestNormalizePriceGuideRecord:
    def test_holo_fields_normalized_to_snake_case(self):
        out = normalize_price_guide_record(make_record(), SNAPSHOT_DATE)
        assert out["avg_holo"] == Decimal("5.00")
        assert out["low_holo"] == Decimal("4.50")
        assert out["trend_holo"] == Decimal("5.25")
        assert out["avg1_holo"] == Decimal("5.10")
        assert out["avg7_holo"] == Decimal("5.20")
        assert out["avg30_holo"] == Decimal("5.30")
        # Original hyphenated keys must not leak through.
        for hyphenated in ("avg-holo", "low-holo", "trend-holo"):
            assert hyphenated not in out

    def test_plain_price_fields_carried_through_as_decimal(self):
        out = normalize_price_guide_record(make_record(), SNAPSHOT_DATE)
        assert out["avg"] == Decimal("1.23")
        assert out["trend"] == Decimal("1.50")

    def test_id_fields_renamed_and_typed(self):
        out = normalize_price_guide_record(make_record(), SNAPSHOT_DATE)
        assert out["id_product"] == 12345
        assert out["id_category"] == 7
        assert "idProduct" not in out
        assert "idCategory" not in out

    def test_missing_price_fields_become_none(self):
        record = {"idProduct": 1}
        out = normalize_price_guide_record(record, SNAPSHOT_DATE)
        assert out["avg"] is None
        assert out["avg_holo"] is None
        assert out["id_category"] is None

    def test_malformed_price_value_becomes_none_not_a_crash(self):
        out = normalize_price_guide_record(make_record(avg="not-a-number"), SNAPSHOT_DATE)
        assert out["avg"] is None

    def test_snapshot_date_and_source_created_at_passed_through(self):
        ts = datetime.datetime(2026, 7, 19, 17, 5, 0)
        out = normalize_price_guide_record(make_record(), SNAPSHOT_DATE, source_created_at=ts)
        assert out["snapshot_date"] == SNAPSHOT_DATE
        assert out["source_created_at"] == ts


class TestTransformPriceGuide:
    def test_end_to_end_transform(self):
        rows = transform_price_guide([make_record(), make_record(idProduct=999)], SNAPSHOT_DATE)
        assert len(rows) == 2
        assert {r["id_product"] for r in rows} == {12345, 999}
        assert all(r["snapshot_date"] == SNAPSHOT_DATE for r in rows)

    def test_end_to_end_fails_on_invalid_file(self):
        with pytest.raises(ValidationError):
            transform_price_guide([], SNAPSHOT_DATE)


class TestExtractSourceCreatedAt:
    def test_parses_confirmed_format(self):
        raw = {"createdAt": "2026-06-29T02:55:18+0200", "priceGuides": []}
        dt = extract_source_created_at(raw)
        assert dt == datetime.datetime(
            2026, 6, 29, 2, 55, 18, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )

    def test_missing_field_returns_none(self):
        assert extract_source_created_at({"priceGuides": []}) is None

    def test_malformed_value_returns_none_not_a_crash(self):
        assert extract_source_created_at({"createdAt": "not-a-date"}) is None

    def test_non_dict_root_returns_none(self):
        assert extract_source_created_at([make_record()]) is None

    def test_transform_price_guide_uses_file_createdAt_by_default(self):
        raw = {
            "createdAt": "2026-06-29T02:55:18+0200",
            "priceGuides": [make_record()],
        }
        rows = transform_price_guide(raw, SNAPSHOT_DATE)
        expected = datetime.datetime(
            2026, 6, 29, 2, 55, 18, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )
        assert rows[0]["source_created_at"] == expected

    def test_explicit_override_still_wins(self):
        raw = {"createdAt": "2026-06-29T02:55:18+0200", "priceGuides": [make_record()]}
        override = datetime.datetime(2020, 1, 1)
        rows = transform_price_guide(raw, SNAPSHOT_DATE, source_created_at=override)
        assert rows[0]["source_created_at"] == override


class TestRealSampleFile:
    """
    Regression test against the actual confirmed price_guide_6.json shape
    (data/sample/price_guide_6_sample.json), including a record with a
    real trend-holo: 0 value (must stay Decimal('0'), not become None)
    and records missing the holo keys entirely (must become None, not error).
    """

    SAMPLE = {
        "version": 1,
        "createdAt": "2026-06-29T02:55:18+0200",
        "priceGuides": [
            {"idProduct": 895108, "idCategory": 1654, "avg": None, "low": 8.99,
             "trend": None, "avg1": None, "avg7": None, "avg30": None},
            {"idProduct": 895109, "idCategory": 1654, "avg": None, "low": None,
             "trend": None, "avg1": None, "avg7": None, "avg30": None},
            {"idProduct": 895112, "idCategory": 1017, "avg": 0.5, "low": 0.4,
             "trend": 0.5, "avg1": None, "avg7": None, "avg30": None},
            {"idProduct": 895113, "idCategory": 51, "avg": 16.98, "low": 3.85,
             "trend": 13, "avg1": 13, "avg7": 13, "avg30": 13,
             "avg-holo": None, "low-holo": None, "trend-holo": 0,
             "avg1-holo": None, "avg7-holo": None, "avg30-holo": None},
        ],
    }

    def test_transforms_without_error(self):
        rows = transform_price_guide(self.SAMPLE, SNAPSHOT_DATE)
        assert len(rows) == 4

    def test_zero_holo_value_preserved(self):
        rows = transform_price_guide(self.SAMPLE, SNAPSHOT_DATE)
        row = next(r for r in rows if r["id_product"] == 895113)
        assert row["trend_holo"] == Decimal("0")
        assert row["avg_holo"] is None

    def test_records_without_holo_keys_get_none(self):
        rows = transform_price_guide(self.SAMPLE, SNAPSHOT_DATE)
        row = next(r for r in rows if r["id_product"] == 895108)
        assert row["avg_holo"] is None
        assert row["trend_holo"] is None

    def test_source_created_at_applied_to_every_row(self):
        rows = transform_price_guide(self.SAMPLE, SNAPSHOT_DATE)
        expected = datetime.datetime(
            2026, 6, 29, 2, 55, 18, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )
        assert all(r["source_created_at"] == expected for r in rows)
