import os
import pytest
from unittest.mock import patch
from langchain_openai import ChatOpenAI


def test_get_qwen_model_returns_chat_openai():
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}):
        from app.utils import llm as llm_mod
        import importlib; importlib.reload(llm_mod)
        model = llm_mod.get_qwen_model()
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "qwen3-32b"


def test_get_qwen_model_uses_dashscope_base_url():
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}):
        from app.utils import llm as llm_mod
        import importlib; importlib.reload(llm_mod)
        model = llm_mod.get_qwen_model()
    assert "dashscope" in str(model.openai_api_base).lower()


def test_get_qwen_model_raises_key_error_without_api_key():
    """get_qwen_model() must raise KeyError when DASHSCOPE_API_KEY is absent."""
    env = {k: v for k, v in os.environ.items() if k != "DASHSCOPE_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        from app.utils import llm as llm_mod
        import importlib; importlib.reload(llm_mod)
        with pytest.raises(KeyError):
            llm_mod.get_qwen_model()
