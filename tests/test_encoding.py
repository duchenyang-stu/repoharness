from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

from repoharness.cli import configure_utf8_output
from repoharness.sandbox import WorkspaceSandbox


class EncodingTests(unittest.TestCase):
    def test_child_python_output_is_decoded_as_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "hello.py").write_text("print('修复完成：测试通过')\n", encoding="utf-8")
            completed = WorkspaceSandbox(root).run(["python", "hello.py"], 30)
            self.assertIn("修复完成：测试通过", completed.stdout)

    def test_stdout_is_reconfigured_to_utf8(self):
        original_out, original_err = sys.stdout, sys.stderr
        buffer = io.BytesIO()
        try:
            sys.stdout = io.TextIOWrapper(buffer, encoding="gbk")
            sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="gbk")
            configure_utf8_output()
            print("中文")
            sys.stdout.flush()
            self.assertEqual(buffer.getvalue().decode("utf-8").strip(), "中文")
        finally:
            sys.stdout, sys.stderr = original_out, original_err


if __name__ == "__main__":
    unittest.main()
