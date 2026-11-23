"""Regression: `python app.py` (dev compose / CI) crashed on yaml.load(f) with PyYAML 6.
Run from the repo root: python -m unittest discover -s tests
"""
import logging.config
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # app.py loads templates/static relative to cwd

import app  # noqa: E402


class LogConfigTest(unittest.TestCase):
    def test_log_config_loads_and_is_valid_for_dictconfig(self):
        config = app.load_log_config(str(ROOT / "log_config.yml"))
        self.assertIsInstance(config, dict)
        self.assertIn("root", config)
        logging.config.dictConfig(config)


if __name__ == "__main__":
    unittest.main()
