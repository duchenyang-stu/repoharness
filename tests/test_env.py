from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from repoharness.env import load_env, parse_env_file


class EnvTests(unittest.TestCase):
    def test_parse_handles_comments_quotes_export_and_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "\ufeff# comment\nA=1\nexport B=\"two words\"\nC='x'  \nD=val # trailing\n\nBAD\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_env_file(path), {"A": "1", "B": "two words", "C": "x", "D": "val"})

    def test_load_env_does_not_override_existing_variables(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text("RH_TEST_KEEP=file\nRH_TEST_NEW=file\n", encoding="utf-8")
            os.environ["RH_TEST_KEEP"] = "shell"
            os.environ.pop("RH_TEST_NEW", None)
            try:
                loaded = load_env([Path(directory)])
                self.assertEqual(len(loaded), 1)
                self.assertEqual(os.environ["RH_TEST_KEEP"], "shell")
                self.assertEqual(os.environ["RH_TEST_NEW"], "file")
            finally:
                os.environ.pop("RH_TEST_KEEP", None)
                os.environ.pop("RH_TEST_NEW", None)

    def test_missing_env_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_env([Path(directory)]), [])


if __name__ == "__main__":
    unittest.main()
