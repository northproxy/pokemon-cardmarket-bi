from src.load.canonical_file import resolve_canonical_filename


class TestResolveCanonicalFilename:
    def test_base_file_only(self):
        r = resolve_canonical_filename(
            "price_guide_6", "2026-07-03", ["price_guide_6_2026-07-03.json"]
        )
        assert r.filename == "price_guide_6_2026-07-03.json"
        assert r.is_rerun is False
        assert r.rerun_number is None
        assert r.superseded_filenames == ()

    def test_highest_rerun_wins(self):
        r = resolve_canonical_filename(
            "price_guide_6",
            "2026-07-03",
            [
                "price_guide_6_2026-07-03.json",
                "price_guide_6_2026-07-03_rerun-01.json",
                "price_guide_6_2026-07-03_rerun-02.json",
            ],
        )
        assert r.filename == "price_guide_6_2026-07-03_rerun-02.json"
        assert r.is_rerun is True
        assert r.rerun_number == 2
        assert set(r.superseded_filenames) == {
            "price_guide_6_2026-07-03.json",
            "price_guide_6_2026-07-03_rerun-01.json",
        }

    def test_no_file_for_date_is_a_gap_not_an_error(self):
        r = resolve_canonical_filename(
            "price_guide_6", "2026-07-04", ["price_guide_6_2026-07-03.json"]
        )
        assert r.filename is None
        assert r.superseded_filenames == ()

    def test_different_prefix_does_not_match(self):
        r = resolve_canonical_filename(
            "products_singles_6", "2026-07-03", ["price_guide_6_2026-07-03.json"]
        )
        assert r.filename is None

    def test_similar_date_does_not_match(self):
        r = resolve_canonical_filename(
            "price_guide_6",
            "2026-07-03",
            ["price_guide_6_2026-07-030.json", "price_guide_6_2026-07-03x.json"],
        )
        assert r.filename is None

    def test_only_reruns_no_base_file(self):
        # Base was superseded/removed hypothetically -- still resolves to
        # the highest rerun present.
        r = resolve_canonical_filename(
            "price_guide_6",
            "2026-07-03",
            ["price_guide_6_2026-07-03_rerun-01.json"],
        )
        assert r.filename == "price_guide_6_2026-07-03_rerun-01.json"
        assert r.is_rerun is True

    def test_products_singles_prefix_pattern(self):
        r = resolve_canonical_filename(
            "products_singles_6",
            "2026-07-10",
            [
                "products_singles_6_2026-07-10.json",
                "products_nonsingles_6_2026-07-10.json",  # different prefix, must be ignored
            ],
        )
        assert r.filename == "products_singles_6_2026-07-10.json"
