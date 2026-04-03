import json
import re
import logging
from typing import Optional
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger("hr_agent.llm_client")


class LLMClient:
    """统一的 LLM 客户端,封装调用和 JSON 解析逻辑"""
    
    def __init__(self, model: ChatOpenAI):
        """
        初始化 LLM 客户端
        
        Args:
            model: LangChain ChatOpenAI 模型实例
        """
        self.model = model
    
    def invoke(self, prompt: str, expect_json: bool = True) -> str | dict:
        """
        调用 LLM 并返回响应
        
        Args:
            prompt: 提示词
            expect_json: 是否期望 JSON 响应并自动解析
            
        Returns:
            如果 expect_json=True,返回解析后的 dict
            如果 expect_json=False,返回原始字符串
            
        Raises:
            ValueError: LLM 响应为空或 JSON 解析失败
        """
        try:
            # 调用 LLM
            response = self.model.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            logger.info(f"[LLMClient] Response length: {len(content)} chars")
            logger.debug(f"[LLMClient] Raw response: {content[:300]}...")
            
            # 检查空响应
            if not content or content.isspace():
                raise ValueError("LLM returned empty response")
            
            # 如果不需要 JSON,直接返回
            if not expect_json:
                return content
            
            # 解析 JSON
            return self._extract_json(content)
            
        except json.JSONDecodeError as e:
            logger.error(f"[LLMClient] JSON parse error: {e}")
            logger.error(f"[LLMClient] Content: {content[:500]}")
            raise ValueError(f"Failed to parse JSON from LLM response: {e}") from e
        except Exception as e:
            logger.error(f"[LLMClient] Error: {e}")
            raise ValueError(f"LLM invocation failed: {e}") from e
    
    def _extract_json(self, content: str) -> dict:
        """
        从 LLM 响应中提取 JSON 对象
        
        支持多种格式:
        1. Markdown 代码块: ```json {...} ```
        2. 普通代码块: ``` {...} ```
        3. 文本中嵌入的 JSON 对象
        
        Args:
            content: LLM 响应内容
            
        Returns:
            解析后的 JSON 字典
            
        Raises:
            json.JSONDecodeError: JSON 解析失败
        """
        original_content = content
        
        # Pattern 1: 提取 markdown 代码块中的 JSON
        # 匹配 ```json {...} ``` 或 ``` {...} ```
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            content,
            re.DOTALL | re.IGNORECASE
        )
        if json_match:
            content = json_match.group(1)
            logger.debug(f"[LLMClient] Extracted from markdown block")
        else:
            # Pattern 2: 去除首尾的代码块标记
            content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content.strip())
            
            # Pattern 3: 尝试从文本中提取 JSON 对象
            if not content.startswith("{"):
                json_obj_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_obj_match:
                    content = json_obj_match.group(0)
                    logger.debug(f"[LLMClient] Extracted JSON object from text")
        
        logger.debug(f"[LLMClient] Final JSON string: {content[:200]}...")
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 如果解析失败,记录完整内容
            logger.error(f"[LLMClient] Failed to parse extracted JSON")
            logger.error(f"[LLMClient] Original content: {original_content[:1000]}")
            logger.error(f"[LLMClient] Extracted content: {content[:1000]}")
            raise
