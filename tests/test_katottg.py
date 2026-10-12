import unittest

from katottglib import (
    CATEGORIES,
    TOP_LEVEL_CATEGORIES,
    find_by_id,
    find_by_name,
    find_children,
    find_top_level,
)
from katottglib.katottg import parse_categories

KYIV = "UA80000000000093317"
SEVASTOPOL = "UA85000000000065278"
KYIVSKA = "UA32000000000030281"
KHERSONSKA = "UA65000000000030969"
KIROVOHRADSKA = "UA35000000000016081"


class KatottgSearchTestCase(unittest.TestCase):
    def test_simple_search(self):
        cases = (
            ("Херсон", "UA65100150010064384"),
            ("Миколаїв", "UA46100110010094231"),
            # The city, not whichever of the 40 villages of that name the
            # old similarity sort happened to put first.
            ("Миколаївка", "UA14120130010079249"),
            # A село outranks a селище: the codifier's own category order
            # is now honoured instead of the letter sorted backwards.
            ("Червона Поляна", "UA12040230170020096"),
        )
        for input_query, expected_id in cases:
            actual = find_by_name(input_query)
            self.assertTrue(len(actual) > 0)
            self.assertEqual(expected_id, actual[0].entity_id)

    def test_search_in_parent(self):
        cases = (
            ("Червона Поляна", KHERSONSKA, "UA65060130090033121"),
            ("Червона Поляна", KIROVOHRADSKA, "UA35060090140077182"),
        )
        for input_query, parent_id, expected_id in cases:
            actual = find_by_name(input_query, parent_id=parent_id)
            self.assertTrue(len(actual) > 0)
            self.assertEqual(expected_id, actual[0].entity_id)

    def test_limit_caps_but_never_pads(self):
        self.assertEqual(len(find_by_name("Червона Поляна")), 5)
        self.assertEqual(len(find_by_name("Червона Поляна", limit=3)), 3)
        self.assertLess(len(find_by_name("Червона Поляна", limit=100)), 100)

    def test_exact_match_outranks_a_longer_name(self):
        self.assertEqual("Херсон", find_by_name("Херсо")[0].name)
        self.assertEqual("Київ", find_by_name("Київ")[0].name)


class FindByIdTestCase(unittest.TestCase):
    def test_find_by_id(self):
        self.assertEqual(
            find_by_id("UA65060130090033121").name, "Червона Поляна"
        )
        self.assertEqual(find_by_id("UA65100150010064384").name, "Херсон")
        self.assertEqual(find_by_id("UA00000001234567890"), None)

    def test_identifier_is_matched_whole(self):
        """A prefix is not an identifier; it used to return Kyiv."""
        self.assertIsNone(find_by_id("UA8"))
        self.assertIsNone(find_by_id("UA650601300900331"))
        self.assertIsNone(find_by_id(""))


class TopLevelTestCase(unittest.TestCase):
    """The capital is a category K object, not an oblast."""

    def test_top_level_holds_every_region(self):
        entities = find_top_level(limit=100)
        self.assertEqual(27, len(entities))
        identifiers = {entity.entity_id for entity in entities}
        self.assertIn(KYIV, identifiers)
        self.assertIn(SEVASTOPOL, identifiers)

    def test_oblast_only_filter_cannot_offer_the_capital(self):
        identifiers = {
            entity.entity_id
            for entity in find_by_name("Київ", category="O", limit=50)
        }
        self.assertNotIn(KYIV, identifiers)

    def test_capital_is_found_once_both_categories_are_asked_for(self):
        entities = find_top_level("Київ")
        self.assertEqual(KYIV, entities[0].entity_id)

    def test_capital_has_no_parent(self):
        self.assertTrue(find_by_id(KYIV).is_top_level)


class ParentFilterTestCase(unittest.TestCase):
    def test_parent_is_not_its_own_child(self):
        """
        The oblast row matched its own parent filter, so an oblast was
        offered in the settlement list and got stored as a settlement.
        """
        children = find_children(KYIVSKA, name="Київ", limit=50)
        self.assertNotIn(KYIVSKA, {child.entity_id for child in children})

        for entity in find_children(KYIVSKA, limit=200):
            self.assertNotEqual(KYIVSKA, entity.entity_id)
            self.assertNotEqual("O", entity.category_code)

    def test_children_are_returned_once(self):
        """Kyiv repeats its own id across levels 1..4."""
        districts = find_children(KYIV, limit=50)
        identifiers = [district.entity_id for district in districts]
        self.assertEqual(10, len(identifiers))
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_ancestors_are_deduplicated(self):
        district = find_children(KYIV, name="Солом'янський")[0]
        self.assertEqual("Київ, Солом’янський", district.path)
        self.assertEqual(1, len(district.parents))

    def test_unknown_parent_yields_nothing(self):
        self.assertEqual([], find_children("UA00000000000000000"))


class CategoryTestCase(unittest.TestCase):
    def test_parse_categories(self):
        self.assertIsNone(parse_categories(None))
        self.assertEqual(["O"], parse_categories("O"))
        self.assertEqual(["O", "K"], parse_categories("O,K"))
        self.assertEqual(["O", "K"], parse_categories(("O", "K")))
        self.assertEqual(["O", "K"], parse_categories(TOP_LEVEL_CATEGORIES))
        self.assertEqual(["O"], parse_categories(CATEGORIES["O"]))

    def test_a_blank_category_is_no_filter(self):
        for blank in ("", "   ", ",,", []):
            self.assertIsNone(parse_categories(blank))

    def test_repeated_codes_collapse(self):
        self.assertEqual(["O"], parse_categories("O,O"))
        self.assertEqual(["O", "K"], parse_categories(["O", "K", "O"]))

    def test_an_unknown_category_matches_nothing(self):
        """It must not quietly fall back to the whole codifier."""
        self.assertEqual([], parse_categories("Z"))
        self.assertEqual([], parse_categories("нема такої"))
        self.assertEqual([], find_by_name("Київ", category="Z", limit=50))

    def test_several_categories_are_honoured(self):
        codes = {
            entity.category_code
            for entity in find_by_name("", category="O,K", limit=100)
        }
        self.assertEqual({"O", "K"}, codes)

    def test_category_and_parent_combine(self):
        entities = find_children(KYIVSKA, category="P", limit=100)
        self.assertEqual(7, len(entities))
        self.assertEqual({"P"}, {entity.category_code for entity in entities})


class ArgumentTestCase(unittest.TestCase):
    def test_no_limit_means_no_work(self):
        self.assertEqual([], find_by_name("Київ", limit=0))
        self.assertEqual([], find_by_name("Київ", limit=-5))

    def test_similarity_threshold_is_adjustable(self):
        loose = find_by_name("Кийів", min_similarity=0.5, limit=20)
        strict = find_by_name("Кийів", min_similarity=0.95, limit=20)
        self.assertTrue(len(loose) > len(strict))

    def test_an_unknown_parent_yields_nothing(self):
        self.assertEqual([], find_by_name("Київ", parent_id="UA00"))

    def test_a_leaf_has_no_children(self):
        self.assertEqual([], find_children("UA65060130090033121"))

    def test_a_query_no_name_opens_with_yields_nothing(self):
        self.assertEqual([], find_by_name("ьъэ", limit=50))


class SimilarityTestCase(unittest.TestCase):
    def test_a_real_typo_is_still_corrected(self):
        self.assertEqual("Миколаївка", find_by_name("Миколаїка")[0].name)

    def test_nonsense_returns_nothing(self):
        self.assertEqual([], find_by_name("Квжыфыва", limit=50))

    def test_similarity_does_not_pad_a_short_result(self):
        """
        "Крива" shares enough letters with "Київ" to pass a bare ratio
        check. A settlement list must not suggest it.
        """
        names = {entity.name for entity in find_children(KYIVSKA, name="Київ")}
        self.assertNotIn("Крива", names)


class QueryNormalisationTestCase(unittest.TestCase):
    def test_settlement_type_prefix_is_ignored(self):
        for query in ("м. Київ", "м.Київ", "м Київ"):
            self.assertEqual(KYIV, find_top_level(query)[0].entity_id)

    def test_case_and_apostrophe_forms_match(self):
        expected = "Солом’янський"
        for query in ("Солом'янський", "солом`янський", "СОЛОМ’ЯНСЬКИЙ"):
            self.assertEqual(expected, find_children(KYIV, name=query)[0].name)

    def test_empty_query_lists_the_broadest_objects_first(self):
        entities = find_children(KYIVSKA, limit=10)
        self.assertEqual("P", entities[0].category_code)
        names = [
            entity.name for entity in entities if entity.category_code == "P"
        ]
        self.assertEqual(sorted(names, key=str.casefold), names)


class EntityContractTestCase(unittest.TestCase):
    """apps.services.AddressService serialises KatottgEntity.__dict__."""

    def test_serialisable_attributes(self):
        entity = find_by_id("UA65060130090033121")
        self.assertEqual(
            {"entity_id", "name", "category", "category_code", "parent"},
            set(entity.__dict__),
        )
        self.assertEqual("Села", entity.category)
        self.assertEqual("C", entity.category_code)
        self.assertIsNotNone(entity.parent)

    def test_parent_chain_runs_outwards(self):
        entity = find_by_id("UA65060130090033121")
        self.assertEqual(
            ["Костянтинівська", "Каховський", "Херсонська"],
            [parent.name for parent in entity.parents],
        )


if __name__ == "__main__":
    unittest.main()
