"""Entities without rdfs:label must be mappable via their IRI.
Run: python -m unittest discover -s tests
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rdflib import URIRef  # noqa: E402

import maptomethod as m  # noqa: E402

FIXTURE = (Path(__file__).parent / "fixtures" / "unlabeled-metadata.json").resolve()
DATA_URL = FIXTURE.as_uri()
OA_ANNOTATION = URIRef("http://www.w3.org/ns/oa#Annotation")
LABELED = "http://example.org/data/labeled"
UNLABELED = "http://example.org/data/unlabeled"


def entities():
    ents, _ = m.query_entities(DATA_URL, [OA_ANNOTATION])
    return ents


def mapping(map_list):
    return m.get_mapping_output(
        data_url=DATA_URL,
        use_template_rowwise=False,
        data_ns="http://example.org/data/",
        template_ns="http://example.org/template/",
        map_list=map_list,
        subjects_dict=entities(),
        mapping_predicate_uri=URIRef("http://example.org/p"),
    )["filedata"]


def condition_params(rule):
    return {k: v for k, v in rule["condition"]["parameters"]}


class QueryEntitiesTest(unittest.TestCase):
    def test_labeled_entity_keeps_label_lookup(self):
        e = entities()["labeled"]
        self.assertEqual((e["text"], e["property"]), ("Width", "label"))

    def test_unlabeled_entity_is_looked_up_by_iri(self):
        e = entities()["unlabeled"]
        self.assertEqual((e["text"], e["property"]), (UNLABELED, "@id"))
        self.assertEqual(e["uri"], UNLABELED)


class MappingOutputTest(unittest.TestCase):
    def test_unlabeled_entity_produces_rule_matching_on_id(self):
        rules = mapping([("TemplateThing", "unlabeled")])["mappings"]
        self.assertIn("TemplateThing", rules)  # was silently dropped before
        self.assertEqual(
            condition_params(rules["TemplateThing"]),
            {"str1": "$(@id)", "str2": UNLABELED},
        )

    def test_unlabeled_rule_uses_iterator_of_array_containing_it(self):
        out = mapping([("TemplateThing", "unlabeled")])
        source = out["mappings"]["TemplateThing"]["sources"][0]
        self.assertEqual(out["sources"][source]["iterator"], "$.notes[*]")

    def test_labeled_entity_unchanged(self):
        rules = mapping([("TemplateThing", "labeled")])["mappings"]
        self.assertEqual(
            condition_params(rules["TemplateThing"]),
            {"str1": "$(label)", "str2": "Width"},
        )

    def test_mixed_mapping_creates_both_rules(self):
        rules = mapping([("A", "labeled"), ("B", "unlabeled")])["mappings"]
        self.assertEqual(set(rules), {"A", "B"})

    def test_unknown_entity_is_ignored(self):
        self.assertEqual(mapping([("A", "nope")])["mappings"], {})


class IteratorTest(unittest.TestCase):
    def test_id_value_selects_array_with_that_id(self):
        it, _ = m.find_jsonpath_iterator(DATA_URL, "@id", field_value=UNLABELED)
        self.assertEqual(it, "$.notes[*]")

    def test_id_value_not_found_falls_back(self):
        it, _ = m.find_jsonpath_iterator(DATA_URL, "@id", field_value="http://x/none")
        self.assertEqual(it, "$..[*]")


if __name__ == "__main__":
    unittest.main()
