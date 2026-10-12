import os
import pickle
import shutil
import tempfile
import unittest
from unittest import mock

import pandas as pd

from katottglib import data as D

HEADER = [
    "Перший рівень",
    "Другий рівень",
    "Третій рівень",
    "Четвертий рівень",
    "Додатковий рівень",
    "Категорія об’єкта",
    "Назва об’єкта",
]

#: One oblast, one raion, one hromada, one village, and a city with
#: special status whose district repeats the city id across the levels.
ROWS = [
    ["UA01", None, None, None, None, "O", "Тестівська"],
    ["UA01", "UA0102", None, None, None, "P", "Тестівський"],
    ["UA01", "UA0102", "UA010203", None, None, "H", "Тестівська"],
    ["UA01", "UA0102", "UA010203", "UA01020304", None, "C", " Осична "],
    ["UA80", None, None, None, None, "K", "Тестоград"],
    ["UA80", "UA80", "UA80", "UA80", "UA8005", "B", "Південний"],
]


def workbook(path, rows=ROWS, title_block=True, header=HEADER):
    """Write a workbook the way the ministry publishes one."""
    lines = []
    if title_block:
        lines.append([None] * 7)
        lines.append(["Кодифікатор..."] + [None] * 6)
    lines.append(list(header))
    lines.extend(rows)
    pd.DataFrame(lines).to_excel(path, header=False, index=False)
    return path


class SourceFileTestCase(unittest.TestCase):
    """The published workbook has a title block above the table."""

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.path = os.path.join(self.directory, "kodifikator.xlsx")

    def read(self, **kwargs):
        workbook(self.path, **kwargs)
        with mock.patch.object(D, "_source_path", return_value=self.path):
            return D._read_source()

    def test_header_block_is_skipped(self):
        frame = self.read()
        self.assertEqual(len(ROWS), len(frame))
        self.assertIn("Назва об’єкта", frame.columns)

    def test_a_trimmed_workbook_reads_too(self):
        frame = self.read(title_block=False)
        self.assertEqual(len(ROWS), len(frame))

    def test_values_are_stripped(self):
        frame = self.read()
        self.assertIn("Осична", list(frame["Назва об’єкта"]))

    def test_rows_without_a_known_category_are_dropped(self):
        rows = ROWS + [
            ["UA01", None, None, None, None, None, "Примітка"],
            ["UA01", None, None, None, None, "Z", "Невідома категорія"],
            ["UA01", None, None, None, None, "C", None],
        ]
        self.assertEqual(len(ROWS), len(self.read(rows=rows)))

    def test_missing_header_is_reported(self):
        with self.assertRaises(ValueError) as caught:
            self.read(header=["a", "b", "c", "d", "e", "f", "g"])
        self.assertIn("Перший рівень", str(caught.exception))

    def test_missing_column_is_reported(self):
        header = list(HEADER)
        header[6] = "Найменування"
        with self.assertRaises(ValueError) as caught:
            self.read(header=header)
        self.assertIn("Назва об’єкта", str(caught.exception))


class PrepareTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory, True)
        path = workbook(os.path.join(directory, "kodifikator.xlsx"))
        with mock.patch.object(D, "_source_path", return_value=path):
            self.frame = D._prepare(D._read_source())

    def row(self, identifier):
        return self.frame[self.frame["id"] == identifier].iloc[0]

    def test_id_is_the_deepest_level(self):
        self.assertEqual("UA01020304", self.row("UA01020304")["id"])
        self.assertEqual(
            ["UA01", "UA0102", "UA010203", "UA01020304", "UA80", "UA8005"],
            list(self.frame["id"]),
        )

    def test_ancestors_run_broadest_first_without_self(self):
        self.assertEqual(
            ("UA01", "UA0102", "UA010203"),
            self.row("UA01020304")["ancestors"],
        )
        self.assertEqual((), self.row("UA01")["ancestors"])

    def test_repeated_levels_collapse_to_one_ancestor(self):
        """Kyiv repeats its own id on levels 1 to 4."""
        self.assertEqual(("UA80",), self.row("UA8005")["ancestors"])

    def test_category_is_named_and_ordered(self):
        oblast = self.row("UA01")
        self.assertEqual(D.CATEGORIES["O"], oblast["category_name"])
        self.assertLess(
            oblast["category_order"], self.row("UA8005")["category_order"]
        )

    def test_search_name_is_normalised(self):
        self.assertEqual("осична", self.row("UA01020304")["search_name"])

    def test_indexes_follow_the_frame(self):
        positions = D.position_index(self.frame)
        self.assertEqual(len(self.frame), len(positions))
        self.assertEqual(
            ["UA0102", "UA010203", "UA01020304"],
            [
                self.frame.iloc[p]["id"]
                for p in D.children_index(self.frame)["UA01"]
            ],
        )
        self.assertNotIn(
            "UA8005", D.children_index(self.frame).get("UA0102", [])
        )

    def test_every_ancestor_resolves(self):
        known = set(self.frame["id"])
        for ancestors in self.frame["ancestors"]:
            self.assertTrue(set(ancestors) <= known)


class NormalisationTestCase(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual("", D.normalize(None))
        self.assertEqual("", D.normalize(float("nan")))
        self.assertEqual("київ", D.normalize("  Київ  "))
        self.assertEqual("нова каховка", D.normalize("Нова   Каховка"))

    def test_apostrophe_forms_are_one_character(self):
        forms = [
            "Солом'янський",
            "Солом’янський",
            "Солом`янський",
            "Соломʼянський",
        ]
        self.assertEqual(1, len({D.normalize(form) for form in forms}))

    def test_settlement_type_prefix_is_dropped_from_a_query(self):
        for query in ("м. Київ", "м.Київ", "м Київ", "М. Київ", "  м.  Київ"):
            self.assertEqual("київ", D.normalize_query(query))
        self.assertEqual("ставище", D.normalize_query("смт Ставище"))
        self.assertEqual("осична", D.normalize_query("с. Осична"))

    def test_a_name_that_merely_starts_with_a_type_letter_survives(self):
        """'Мала Виска' must not become 'ала Виска'."""
        self.assertEqual("мала виска", D.normalize_query("Мала Виска"))
        self.assertEqual(
            "стара збур'ївка", D.normalize_query("Стара Збур’ївка")
        )
        self.assertEqual("суми", D.normalize_query("Суми"))


class CacheTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.source = workbook(os.path.join(self.directory, "kodifikator.xlsx"))
        self.cache = os.path.join(self.directory, "cache")

        patch_source = mock.patch.object(
            D, "_source_path", return_value=self.source
        )
        patch_env = mock.patch.dict(
            os.environ, {D.CACHE_DIR_ENV: self.cache}, clear=False
        )
        patch_source.start()
        patch_env.start()
        self.addCleanup(patch_source.stop)
        self.addCleanup(patch_env.stop)
        D.reset_cache()
        self.addCleanup(D.reset_cache)

    def cached_files(self):
        return (
            sorted(os.listdir(self.cache)) if os.path.isdir(self.cache) else []
        )

    def test_the_chosen_directory_is_used_first(self):
        self.assertEqual(self.cache, D._cache_directories()[0])

    def test_the_frame_is_written_once_and_read_back(self):
        D.load_data()
        self.assertEqual(1, len(self.cached_files()))

        D.reset_cache()
        with mock.patch.object(D, "_read_source") as read_source:
            frame = D.load_data()
        read_source.assert_not_called()
        self.assertEqual(len(ROWS), len(frame))

    def test_the_frame_is_parsed_once_per_process(self):
        D.load_data()
        with mock.patch.object(D, "_read_cache") as read_cache:
            D.load_data()
            D.load_data()
        read_cache.assert_not_called()

    def test_the_key_covers_the_layout_the_data_and_pandas(self):
        key = D._cache_key()
        with mock.patch.object(D, "LAYOUT_VERSION", D.LAYOUT_VERSION + 1):
            self.assertNotEqual(key, D._cache_key())
        with mock.patch.object(pd, "__version__", "0.0.0"):
            self.assertNotEqual(key, D._cache_key())

    def test_a_changed_data_file_is_not_served_from_the_cache(self):
        D.load_data()
        stale = self.cached_files()[0]

        workbook(self.source, rows=ROWS[:2])
        os.utime(self.source, (0, 0))
        D.reset_cache()
        frame = D.load_data()

        self.assertEqual(2, len(frame))
        self.assertNotIn(stale, self.cached_files())

    def test_stale_caches_are_purged(self):
        os.makedirs(self.cache, exist_ok=True)
        orphan = os.path.join(self.cache, f"{D.CACHE_PREFIX}-v0-old.pkl")
        keep = os.path.join(self.cache, "something-else.txt")
        with open(orphan, "wb") as handle:
            pickle.dump({}, handle)
        with open(keep, "w", encoding="utf-8") as handle:
            handle.write("keep me")

        D.load_data()

        self.assertFalse(os.path.exists(orphan))
        self.assertTrue(os.path.exists(keep))
        self.assertEqual(
            1, len([n for n in self.cached_files() if n.endswith(".pkl")])
        )

    def test_an_unreadable_cache_falls_back_to_the_workbook(self):
        os.makedirs(self.cache, exist_ok=True)
        with open(os.path.join(self.cache, D._cache_key()), "wb") as handle:
            handle.write(b"not a pickle")

        frame = D.load_data()

        self.assertEqual(len(ROWS), len(frame))

    def test_an_unwritable_directory_is_skipped(self):
        with mock.patch.object(D, "_cache_candidates", return_value=[]):
            D.reset_cache()
            self.assertEqual(len(ROWS), len(D.load_data()))


class ShippedCodifierTestCase(unittest.TestCase):
    """Invariants the bundled data file must hold after any update."""

    @classmethod
    def setUpClass(cls):
        cls.frame = D.load_data()

    def test_identifiers_are_unique(self):
        identifiers = list(self.frame["id"])
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertTrue(all(isinstance(value, str) for value in identifiers))

    def test_every_category_is_known(self):
        self.assertTrue(set(self.frame["category"]) <= set(D.CATEGORIES))

    def test_every_ancestor_exists(self):
        known = set(self.frame["id"])
        for ancestors in self.frame["ancestors"]:
            self.assertTrue(set(ancestors) <= known)

    def test_the_top_level_is_twenty_five_oblasts_and_two_cities(self):
        counts = self.frame["category"].value_counts()
        self.assertEqual(25, counts["O"])
        self.assertEqual(2, counts["K"])
        top = self.frame[self.frame["ancestors"].str.len() == 0]
        self.assertEqual(27, len(top))
        self.assertTrue(set(top["category"]) <= set(D.TOP_LEVEL_CATEGORIES))

    def test_nothing_below_the_top_level_is_an_orphan(self):
        below = self.frame[~self.frame["category"].isin(D.TOP_LEVEL_CATEGORIES)]
        self.assertTrue(all(len(a) > 0 for a in below["ancestors"]))

    def test_no_name_is_blank(self):
        self.assertTrue(all(self.frame["search_name"].str.len() > 0))


if __name__ == "__main__":
    unittest.main()
