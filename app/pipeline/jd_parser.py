from app.types.models import JDRequirements
from app.utils.llm import get_minmax_model
from app.utils.llm_client import LLMClient

import logging

logger = logging.getLogger("hr_agent.jd_parser")

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
        model = get_minmax_model()
        self.llm_client = LLMClient(model)

    def parse(self, jd_text: str) -> JDRequirements:
        """Parse a job description text into structured JDRequirements.

        Raises ValueError if the model response cannot be parsed into JDRequirements.
        """
        prompt = _PROMPT_TEMPLATE.format(jd_text=jd_text)
        try:
            # 使用统一的 LLM 客户端
            data = self.llm_client.invoke(prompt, expect_json=True)
            logger.info(f"[JDParser] LLM response: {data}")
            return JDRequirements(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse JD: {e}") from e
