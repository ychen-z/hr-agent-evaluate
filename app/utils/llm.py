import os
from langchain_openai import ChatOpenAI

_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def get_qwen_model() -> ChatOpenAI:
    """Return a ChatOpenAI instance configured for Qwen3-32b via DashScope.

    Raises KeyError if DASHSCOPE_API_KEY is not set in the environment.
    """
    return ChatOpenAI(
        model="qwen3-32b",
        base_url=_DASHSCOPE_BASE_URL,
        api_key=os.environ["DASHSCOPE_API_KEY"],
        temperature=0.1,
        max_tokens=4096,
        extra_body={"enable_thinking": False},
    )
