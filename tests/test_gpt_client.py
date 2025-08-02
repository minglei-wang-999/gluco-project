import pytest
import json
from app.utils.gpt_client import repair_json_str


class TestRepairJsonStr:
    def test_basic_json(self):
        """Test basic valid JSON passes through unchanged."""
        input_json = '[{"name": "test", "value": 123}]'
        result = repair_json_str(input_json)
        assert json.loads(result) == [{"name": "test", "value": 123}]

    def test_trailing_comma(self):
        """Test handling of trailing commas."""
        input_json = '[{"name": "test",},]'
        result = repair_json_str(input_json)
        assert json.loads(result) == [{"name": "test"}]

    def test_chinese_punctuation(self):
        """Test handling of Chinese punctuation."""
        input_json = '[{"name": "测试"，"value"：123}]'
        result = repair_json_str(input_json)
        assert json.loads(result) == [{"name": "测试", "value": 123}]

    # def test_incomplete_values(self):
    #     """Test handling of incomplete values."""
    #     input_json = '[{"name": "test", "value": }, {"name": "test2", "value": }]'
    #     result = repair_json_str(input_json)
    #     assert json.loads(result) == [
    #         {"name": "test", "value": 0},
    #         {"name": "test2", "value": 0}
    #     ]

    def test_comments(self):
        """Test handling of comments."""
        input_json = '''[{
            "name": "test", // this is a comment
            "value": 123
        }]'''
        result = repair_json_str(input_json)
        assert json.loads(result) == [{"name": "test", "value": 123}]

    # def test_unbalanced_brackets(self):
    #     """Test handling of unbalanced brackets."""
    #     input_json = '[{"name": "test"'
    #     result = repair_json_str(input_json)
    #     assert json.loads(result) == [{"name": "test"}]

    def test_whitespace_normalization(self):
        """Test whitespace normalization."""
        input_json = '''[  {    "name"   :   "test"   ,   
            "value"   :   123   }   ]'''
        result = repair_json_str(input_json)
        assert json.loads(result) == [{"name": "test", "value": 123}]

    # def test_underscore_value(self):
    #     """Test handling of underscore value."""
    #     input_json = '[{"name": "生菜沙拉", "portion": 250, "gi": "_"}, {"name": "奶油通心粉", "portion": 486}]'
    #     result = repair_json_str(input_json)
    #     assert json.loads(result) == [{"name": "生菜沙拉", "portion": 250, "gi": 0}, {"name": "奶油通心粉", "portion": 486}]
