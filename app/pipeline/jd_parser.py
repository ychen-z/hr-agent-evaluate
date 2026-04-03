import json
import re
from langchain_core.messages import HumanMessage
from app.types.models import JDRequirements
from app.utils.llm import get_minmax_model

_PROMPT_TEMPLATE = """你是一个职位需求提取助手。从职位描述中提取结构化信息,以JSON格式返回。

职位描述:
{jd_text}

请严格按照以下JSON格式返回(不要有任何其他文字):
```json
{{
  "required_skills": ["提取的技能1", "技能2"],
  "experience_years": 提取的年限数字,
  "education_level": "本科",
  "soft_skills": ["软技能1", "软技能2"]
}}
```

规则:
- required_skills: 技术技能列表
- experience_years: 工作年限(整数),未提及则为0
- education_level: 只能是 "大专"/"本科"/"硕士"/"博士" 之一,未提及则为"本科"
- soft_skills: 软技能列表(沟通能力、团队协作等)

只返回JSON,不要有其他解释文字。"""


class JDParser:
    def __init__(self):
        self.model = get_minmax_model()

    def parse(self, jd_text: str) -> JDRequirements:
        """Parse a job description text into structured JDRequirements.

        Raises ValueError if the model response cannot be parsed into JDRequirements.
        """
        prompt = _PROMPT_TEMPLATE.format(jd_text=jd_text)
        try:
            response = self.model.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            # DEBUG: 记录原始响应
            import logging
            logger = logging.getLogger("hr_agent.tools")
            logger.info(f"[DEBUG] LLM raw response (len={len(content)}): {content[:300]}...")
            
            # Check for empty response
            if not content or content.isspace():
                raise ValueError("LLM returned empty response")
            
            # Try to extract JSON from markdown fences or code blocks
            # Pattern 1: ```json ... ```
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL | re.IGNORECASE)
            if json_match:
                content = json_match.group(1)
                logger.info(f"[DEBUG] Extracted from markdown: {content[:200]}...")
            else:
                # Pattern 2: Just strip leading/trailing fences
                content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
                content = re.sub(r"\s*```$", "", content.strip())
                
                # Pattern 3: Try to find JSON object in text
                if not content.startswith("{"):
                    json_obj_match = re.search(r"\{.*\}", content, re.DOTALL)
                    if json_obj_match:
                        content = json_obj_match.group(0)
                        logger.info(f"[DEBUG] Extracted JSON object from text: {content[:200]}...")
            
            logger.info(f"[DEBUG] Final content: {content[:200]}...")
            
            data = json.loads(content)
            return JDRequirements(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}\nContent: {content[:500]}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse JD: {e}") from e
