import ast
import unittest
from pathlib import Path

from max_mcp.python2_compat import (
    transpile_python2_source,
    transpile_user_python2_source,
)


class Python2CompatibilityTests(unittest.TestCase):
    def test_annotations_fstrings_unicode_and_str_checks(self):
        source = """
def describe(value: str, width: int = 6) -> str:
    text: str = value
    return f"raw={text!r}; width={width:02d}; braces={{ok}}"
"""
        translated = transpile_python2_source(source)
        compile(translated, "<translated sample>", "exec")
        self.assertNotIn("->", translated)
        self.assertIn("_mcp_string_types", transpile_python2_source(
            "def check(value): return isinstance(value, str)"
        ))
        namespace = {
            "_mcp_string_types": (str,),
            "_mcp_text": str,
            "_mcp_fstring": lambda template, *values: template.format(*values),
            "_mcp_ascii": repr,
        }
        exec(compile(translated, "<translated sample>", "exec"), namespace)
        self.assertEqual(
            namespace["describe"]("Box", 4),
            "raw='Box'; width=04; braces={ok}",
        )

    def test_python2_string_literals_are_unicode(self):
        source = "def message(): return '场景' + '。'"
        translated = transpile_python2_source(source)
        self.assertRegex(translated, r"u['\"]场景['\"]")
        self.assertRegex(translated, r"u['\"]。['\"]")
        compile(translated, "<unicode literal sample>", "exec")

    def test_json_decode_error_is_python_2_safe(self):
        source = 'import json\ndef parse(value):\n    try:\n        return json.loads(value)\n    except json.JSONDecodeError:\n        return None\n'
        translated = transpile_python2_source(source)
        self.assertIn("except ValueError", translated)
        compile(translated, "<JSON tool>", "exec")

    def test_all_tool_sources_transform(self):
        tool_root = Path(__file__).resolve().parents[1] / "max_mcp" / "max_tools"
        tool_sources = sorted(tool_root.rglob("*.py"))
        self.assertEqual(len(tool_sources), 24)
        for path in tool_sources:
            with self.subTest(path=path.name):
                translated = transpile_python2_source(
                    path.read_text(encoding="utf-8"), str(path)
                )
                compile(translated, str(path), "exec")
                ast.parse(translated)

    def test_unsupported_python3_argument_and_unpacking_syntax_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positional-only arguments"):
            transpile_python2_source("def f(value, /): return value")
        with self.assertRaisesRegex(ValueError, "container unpacking"):
            transpile_python2_source("values = [*items]")

    def test_user_python_2_only_script_is_preserved(self):
        source = "print 'legacy syntax'\n"
        self.assertEqual(transpile_user_python2_source(source), source)


if __name__ == "__main__":
    unittest.main()
