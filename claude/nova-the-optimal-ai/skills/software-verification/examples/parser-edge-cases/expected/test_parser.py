import unittest

from input.parser import parse_pairs


class EscapedDelimiterContract(unittest.TestCase):
    def test_escaped_delimiter_stays_inside_value(self):
        self.assertEqual({"message": "one;two", "mode": "safe"}, parse_pairs(r"message=one\;two;mode=safe"))

    def test_unescaped_delimiter_still_separates_pairs(self):
        self.assertEqual({"a": "1", "b": "2"}, parse_pairs("a=1;b=2"))

    def test_parse_then_escape_preserves_semantics(self):
        value = r"path=C:\\tmp\;archive;mode=read"
        parsed = parse_pairs(value)
        self.assertEqual("C:\\tmp;archive", parsed["path"])
        self.assertEqual("read", parsed["mode"])


if __name__ == "__main__":
    unittest.main()
