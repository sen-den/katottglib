import unittest

from katottglib import KatottgEntity


def entity(entity_id, name, code="C"):
    return KatottgEntity(entity_id, name, "Села", category_code=code)


class EntityTestCase(unittest.TestCase):
    def setUp(self):
        self.village = entity("UA01020304", "Осична")
        self.village.add_parent(entity("UA010203", "Тестівська", "H"))
        self.village.add_parent(entity("UA0102", "Тестівський", "P"))
        self.village.add_parent(entity("UA01", "Тестівська", "O"))

    def test_add_parent_builds_the_chain_outwards(self):
        self.assertEqual(
            ["Тестівська", "Тестівський", "Тестівська"],
            [parent.name for parent in self.village.parents],
        )
        self.assertEqual("UA01", self.village.parents[-1].entity_id)

    def test_path_reads_broadest_first(self):
        self.assertEqual(
            "Тестівська, Тестівський, Тестівська, Осична",
            self.village.path,
        )

    def test_a_root_has_no_parents(self):
        root = entity("UA01", "Тестівська", "O")
        self.assertTrue(root.is_top_level)
        self.assertEqual([], root.parents)
        self.assertEqual("Тестівська", root.path)
        self.assertFalse(self.village.is_top_level)

    def test_identity_is_the_identifier(self):
        self.assertEqual(entity("UA01", "Тестівська"), entity("UA01", "Інша"))
        self.assertNotEqual(entity("UA01", "A"), entity("UA02", "A"))
        self.assertEqual(1, len({entity("UA01", "A"), entity("UA01", "B")}))

    def test_comparison_with_another_type_is_not_claimed(self):
        self.assertNotEqual(entity("UA01", "A"), "UA01")
        self.assertIs(NotImplemented, entity("UA01", "A").__eq__("UA01"))

    def test_repr_names_the_identifier_and_the_code(self):
        self.assertEqual(
            "KatottgEntity('UA01', 'Тестівська', 'O')",
            repr(entity("UA01", "Тестівська", "O")),
        )

    def test_str_indents_the_chain(self):
        lines = str(self.village).splitlines()
        self.assertEqual(4, len(lines))
        self.assertEqual("Села - Осична [UA01020304]", lines[0])
        self.assertTrue(lines[1].startswith("\t"))
        self.assertTrue(lines[3].startswith("\t\t\t"))

    def test_the_attributes_a_consumer_serialises(self):
        """apps.services.AddressService walks __dict__."""
        self.assertEqual(
            {"entity_id", "name", "category", "category_code", "parent"},
            set(entity("UA01", "Тестівська").__dict__),
        )


if __name__ == "__main__":
    unittest.main()
