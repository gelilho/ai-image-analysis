"""Tests for json_utils module."""

from src.image.analyzers.json_utils import clean_json_response


class TestCleanJsonResponse:
    def test_empty_string(self):
        assert clean_json_response("") == ""

    def test_plain_json(self):
        assert clean_json_response('{"key": "value"}') == '{"key": "value"}'

    def test_markdown_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert clean_json_response(text) == '{"key": "value"}'

    def test_markdown_without_lang(self):
        text = '```\n{"key": 1}\n```'
        assert clean_json_response(text) == '{"key": 1}'

    def test_text_before_json(self):
        text = 'Here is the result: {"key": "val"}'
        assert clean_json_response(text) == '{"key": "val"}'

    def test_text_after_json(self):
        text = '{"key": "val"} and some more text'
        assert clean_json_response(text) == '{"key": "val"}'

    def test_nested_braces(self):
        text = '{"outer": {"inner": 1}}'
        assert clean_json_response(text) == '{"outer": {"inner": 1}}'

    def test_bom_removal(self):
        text = '\ufeff{"key": 1}'
        assert clean_json_response(text) == '{"key": 1}'

    def test_whitespace_trimming(self):
        text = '   \n  {"key": 1}  \n  '
        assert clean_json_response(text) == '{"key": 1}'

    def test_no_json_object(self):
        text = "no json here"
        result = clean_json_response(text)
        assert result == "no json here"
