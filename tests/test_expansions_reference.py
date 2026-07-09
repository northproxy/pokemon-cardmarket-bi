from pathlib import Path
import csv


REFERENCE_FILE = Path("data/reference/expansions.csv")


def test_expansions_reference_file_exists():
    assert REFERENCE_FILE.exists()


def test_expansions_reference_has_required_columns():
    with REFERENCE_FILE.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = set(reader.fieldnames or [])

    required_columns = {
        "id_expansion",
        "name_en",
        "name_de",
        "slug",
        "series_en",
        "series_de",
        "release_date",
        "card_count",
        "source_url_en",
        "source_url_de",
        "is_active",
    }

    assert required_columns.issubset(fieldnames)


def test_expansions_reference_has_no_duplicate_ids():
    with REFERENCE_FILE.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        ids = [row["id_expansion"] for row in reader if row.get("id_expansion")]

    assert len(ids) == len(set(ids))


def test_expansions_reference_required_values_are_filled():
    with REFERENCE_FILE.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            assert row["id_expansion"].strip()
            assert row["name_en"].strip()
            assert row["name_de"].strip()
