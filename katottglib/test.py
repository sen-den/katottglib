import unittest

from .katottg import find_by_name, find_by_id


class KatottgSearchTestCase(unittest.TestCase):
    def test_simple_search(self):
        cases = (
            ("Херсон", "UA65100150010064384"),
            ("Миколаїв", "UA46100110010094231"),
            ("Миколаївка", "UA05100090120011921"),
            ("Червона Поляна", "UA05100110150052879"),
        )
        for input_query, expected_id in cases:
            actual = find_by_name(input_query)
            self.assertTrue(len(actual) > 0)
            self.assertEqual(expected_id, actual[0].entity_id)

    def test_search_in_parent(self):
        cases = (
            ("Червона Поляна", "UA65000000000030969", "UA65060130090033121"),  # В Херсонській області
            ("Червона Поляна", "UA35000000000016081", "UA35060090140077182"),  # В Кіровоградській області
        )
        for input_query, parent_id, expected_id in cases:
            actual = find_by_name(input_query, parent_id=parent_id)
            self.assertTrue(len(actual) > 0)
            self.assertEqual(expected_id, actual[0].entity_id)

    def test_search_with_limit(self):
        self.assertEqual(len(find_by_name("Червона Поляна")), 5)
        self.assertEqual(len(find_by_name("Червона Поляна", limit=5)), 5)
        self.assertEqual(len(find_by_name("Червона Поляна", limit=100)), 100)  # No similarity threshold yet!

    def test_find_by_id(self):
        self.assertEqual(find_by_id("UA65060130090033121").name, "Червона Поляна")
        self.assertEqual(find_by_id("UA65100150010064384").name, "Херсон")
        self.assertEqual(find_by_id("UA00000001234567890"), None)


if __name__ == '__main__':
    unittest.main()
