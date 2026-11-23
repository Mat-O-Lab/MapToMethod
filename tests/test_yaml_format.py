"""yarrrml-parser silently drops block-style nested `po:` lists (PyYAML >= 5.1 default),
which made RDFConverter generate no triples. po entries must stay inline lists.
Run: python -m unittest discover -s tests
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import yaml  # noqa: E402
from rdflib import URIRef  # noqa: E402

import maptomethod as m  # noqa: E402

DATA_URL = (Path(__file__).parent / "fixtures" / "unlabeled-metadata.json").resolve().as_uri()


def mapping_dict():
    ents, _ = m.query_entities(DATA_URL, [URIRef("http://www.w3.org/ns/oa#Annotation")])
    return m.get_mapping_output(
        DATA_URL, False, "http://example.org/data/", "http://example.org/template/",
        [("A", "labeled"), ("B", "unlabeled")], ents,
        URIRef("http://purl.obolibrary.org/obo/RO_0010002"),
    )["filedata"]


class YamlFormatTest(unittest.TestCase):
    def test_po_entries_are_inline_lists(self):
        text = m.dump_yaml(mapping_dict())
        po_blocks = re.findall(r"po:\n((?:\s+- .*\n)+)", text)
        self.assertEqual(len(po_blocks), 2)
        for block in po_blocks:
            for line in block.splitlines():
                self.assertRegex(line.strip(), r"^- \[.+, .+\]$")  # not "- - pred"

    def test_roundtrip_preserves_data(self):
        data = mapping_dict()
        self.assertEqual(yaml.safe_load(m.dump_yaml(data)), json.loads(json.dumps(data)))

    def test_unicode_not_escaped(self):
        self.assertIn("Prüfung", m.dump_yaml({"label": "Prüfung"}))


if __name__ == "__main__":
    unittest.main()
