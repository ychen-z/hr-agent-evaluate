"""
测试 LLM 客户端功能
"""
import pytest
from unittest.mock import Mock, patch
from app.utils.llm_client import LLMClient


class TestLLMClient:
    """测试 LLMClient 类"""
    
    @pytest.fixture
    def llm_client(self):
        """创建 LLM 客户端实例"""
        # 创建 mock model
        mock_model = Mock()
        return LLMClient(model=mock_model)
    
    def test_extract_json_from_markdown_code_block(self, llm_client):
        """测试从 markdown 代码块中提取 JSON"""
        content = """这是一些文本
```json
{"name": "张三", "score": 85}
```
更多文本"""
        result = llm_client._extract_json(content)
        assert result == {"name": "张三", "score": 85}
    
    def test_extract_json_from_plain_code_block(self, llm_client):
        """测试从普通代码块中提取 JSON"""
        content = """```
{"name": "李四", "score": 90}
```"""
        result = llm_client._extract_json(content)
        assert result == {"name": "李四", "score": 90}
    
    def test_extract_json_from_raw_text(self, llm_client):
        """测试从纯文本中提取 JSON"""
        content = '好的,结果是: {"name": "王五", "score": 75}'
        result = llm_client._extract_json(content)
        assert result == {"name": "王五", "score": 75}
    
    def test_extract_json_multiline(self, llm_client):
        """测试提取多行 JSON"""
        content = """```json
{
  "name": "赵六",
  "scores": {
    "hard_skills": 85,
    "experience": 90
  }
}
```"""
        result = llm_client._extract_json(content)
        assert result == {
            "name": "赵六",
            "scores": {
                "hard_skills": 85,
                "experience": 90
            }
        }
    
    def test_extract_json_invalid_format(self, llm_client):
        """测试无效 JSON 格式抛出异常"""
        content = "这里没有 JSON"
        with pytest.raises((ValueError, Exception)):  # 允许 JSONDecodeError
            llm_client._extract_json(content)
    
    def test_extract_json_malformed(self, llm_client):
        """测试格式错误的 JSON 抛出异常"""
        content = '```json\n{"name": "invalid,}\n```'
        with pytest.raises((ValueError, Exception)):  # 允许 JSONDecodeError
            llm_client._extract_json(content)
    
    @patch('app.utils.llm_client.ChatOpenAI')
    def test_invoke_success(self, mock_chat_openai, llm_client):
        """测试成功调用 LLM"""
        # Mock LLM 响应
        mock_response = Mock()
        mock_response.content = '```json\n{"result": "success"}\n```'
        llm_client.model.invoke = Mock(return_value=mock_response)
        
        result = llm_client.invoke("test prompt", expect_json=True)
        assert result == {"result": "success"}
        llm_client.model.invoke.assert_called_once()
    
    @patch('app.utils.llm_client.ChatOpenAI')
    def test_invoke_plain_text(self, mock_chat_openai, llm_client):
        """测试返回纯文本响应"""
        # Mock LLM 响应
        mock_response = Mock()
        mock_response.content = "这是纯文本响应"
        llm_client.model.invoke = Mock(return_value=mock_response)
        
        result = llm_client.invoke("test prompt", expect_json=False)
        assert result == "这是纯文本响应"
    
    @patch('app.utils.llm_client.ChatOpenAI')
    def test_invoke_api_error(self, mock_chat_openai, llm_client):
        """测试 API 调用错误"""
        # Mock API 错误
        llm_client.model.invoke = Mock(side_effect=Exception("API Error"))
        
        with pytest.raises(Exception, match="API Error"):
            llm_client.invoke("test prompt")
    
    def test_json_extraction_with_special_characters(self, llm_client):
        """测试包含特殊字符的 JSON 提取"""
        content = '''```json
{
  "description": "这是一段包含\\"引号\\"和\\n换行的文本",
  "url": "https://example.com/path?param=value"
}
```'''
        result = llm_client._extract_json(content)
        assert "description" in result
        assert "url" in result
    
    def test_json_extraction_with_chinese(self, llm_client):
        """测试包含中文的 JSON 提取"""
        content = """```json
{
  "姓名": "张三",
  "技能": ["Python", "机器学习"],
  "评价": "候选人具有较强的技术能力"
}
```"""
        result = llm_client._extract_json(content)
        assert result["姓名"] == "张三"
        assert "Python" in result["技能"]
        assert "评价" in result
