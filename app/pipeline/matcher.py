from app.types.models import Resume, JDRequirements, DimensionScore
from app.utils.scorer import Scorer
from app.utils.llm import get_minmax_model
from app.utils.llm_client import LLMClient
import re
import json
import logging

logger = logging.getLogger("hr_agent.matcher")

# AI 评估 Prompt 模板
AI_EVALUATION_PROMPT = """你是一位资深的技术招聘专家,拥有15年的HR和技术背景。
请对以下候选人进行全面、客观的评估。

【岗位需求】
{requirements_json}

【候选人简历】
{resume_json}

【算法基准评分】(供参考)
- 技术技能: {baseline_hard_skills}分
- 工作经验: {baseline_experience}分  
- 教育背景: {baseline_education}分
- 软技能: {baseline_soft_skills}分

【评估要求】
请从以下4个维度进行深度评估,每个维度给出0-100分的分数:

1. **技术技能匹配度** (40%权重)
   - 考虑技能的语义相似性 (如 React vs Vue, Python vs Go)
   - 从项目经历推断技能深度 (精通 vs 了解)
   - 评估技能生态的完整性 (如 Python + Django + Celery 是完整技术栈)
   - 识别可迁移技能 (如熟悉 C++ 的人学 Rust 容易)

2. **工作经验质量** (30%权重)  
   - 不仅看年限,更要看经验的相关性和质量
   - 评估项目复杂度 (并发量、分布式、架构设计等)
   - 判断职责深度 (架构师 > 高级工程师 > 工程师)
   - 识别经验中的水分 (重复经历、简单CRUD)

3. **教育背景** (15%权重)
   - 学历等级 (博士 > 硕士 > 本科 > 大专)
   - 专业相关性 (计算机 > 理工科 > 其他)
   - 学校背景 (985/211 可酌情加分,但不强制)

4. **软技能与潜力** (15%权重)
   - 从工作经历推断软技能 (带团队→领导力, 跨部门→沟通能力)
   - 评估学习能力 (技术栈的演进路径)
   - 判断成长潜力 (职业发展轨迹)
   - 考虑稳定性 (跳槽频率)

【输出格式】
严格按照以下 JSON 格式输出,不要包含任何其他文字:

{{
  "dimensions": {{
    "hard_skills": {{
      "score": 85,
      "baseline": 60,
      "adjustment_reasoning": "候选人虽然简历只列出Python和FastAPI,但项目经历显示其使用了Django、Celery、Redis等完整技术栈,说明技能深度较高。虽未明确列出Docker,但在项目中有容器化部署经验,实际掌握程度较好。算法基准分60分主要是字符串匹配遗漏了相关技能,综合评估应为85分。",
      "highlights": ["技术栈完整", "有架构经验"],
      "concerns": ["缺少云原生经验"]
    }},
    "experience": {{
      "score": 90,
      "baseline": 100,
      "adjustment_reasoning": "候选人3年经验满足要求,但深入分析发现其项目规模较大(日活百万级),且负责核心模块架构设计,经验质量较高。虽然年限刚好达标,但经验含金量超出一般3年工程师,给予90分。",
      "highlights": ["高并发经验", "架构设计能力"],
      "concerns": []
    }},
    "education": {{
      "score": 100,
      "baseline": 100,
      "adjustment_reasoning": "本科学历,计算机专业,完全符合要求。",
      "highlights": ["专业对口"],
      "concerns": []
    }},
    "soft_skills": {{
      "score": 70,
      "baseline": 33,
      "adjustment_reasoning": "简历明确提到'沟通能力',但未列出'团队协作'和'领导力'。然而从工作经历看,候选人在某项目中'负责前后端协作对接'(体现沟通和协作能力),且'指导2名初级工程师'(体现领导力潜质)。算法基准分33分过低,综合推断应为70分。",
      "highlights": ["有指导他人经验", "跨团队协作能力"],
      "concerns": ["领导经验有限"]
    }}
  }},
  "overall_assessment": {{
    "final_score": 84,
    "recommendation": "推荐",
    "summary": "候选人技术功底扎实,项目经验质量高,具有一定的架构思维。虽然在云原生和领导力方面有提升空间,但整体匹配度高,建议进入面试环节。",
    "top_strengths": [
      "技术栈完整且有深度",
      "高并发项目经验",
      "学习能力强(技术栈持续演进)"
    ],
    "key_concerns": [
      "云原生经验不足,可能需要培训",
      "团队管理经验有限"
    ]
  }}
}}

【重要提示】
- 评分要客观公正,不要过度乐观或悲观
- 推理过程要具体,引用简历中的实际内容
- 识别简历中的"暗示"信息,不要只看明确列出的内容
- 算法基准分仅供参考,你的评估应基于深度理解
- 最终分数 = Σ(维度分数 × 权重)
"""

class Matcher:
    def __init__(self):
        self.scorer = Scorer()
    
    def match(self, resume: Resume, requirements: JDRequirements) -> dict[str, DimensionScore]:
        resume_years = self._calculate_years(resume.experience)
        
        results = {
            "hard_skills": self.scorer.score_hard_skills(
                resume.skills,
                requirements.required_skills
            ),
            "experience": self.scorer.score_experience(
                resume_years,
                requirements.experience_years
            ),
            "education": self.scorer.score_education(
                self._get_highest_degree(resume.education),
                requirements.education_level
            ),
            "soft_skills": self.scorer.score_soft_skills(
                resume.soft_skills,
                requirements.soft_skills
            )
        }
        
        return results
    
    def _calculate_years(self, experiences: list) -> int:
        total = 0
        for exp in experiences:
            match = re.search(r'(\d+)年', exp.duration)
            if match:
                total += int(match.group(1))
        return total
    
    def _get_highest_degree(self, education: list) -> str:
        degrees = [e.degree for e in education]
        priority = ["博士", "硕士", "本科", "大专"]
        for d in priority:
            if d in degrees:
                return d
        return "本科"

class AIEnhancedMatcher(Matcher):
    """AI 增强的匹配器,结合算法基准和 LLM 深度评估"""
    
    def __init__(self):
        super().__init__()
        model = get_minmax_model()
        self.llm_client = LLMClient(model)
    
    def match(self, resume: Resume, requirements: JDRequirements) -> dict[str, DimensionScore]:
        """
        执行 AI 增强评分
        
        流程:
        1. 调用父类获取算法基准分
        2. 使用 LLM 进行深度评估
        3. 失败时降级到算法基准分
        """
        # Step 1: 获取算法基准分
        baseline_scores = super().match(resume, requirements)
        
        logger.info("[AIEnhancedMatcher] Baseline scores calculated")
        
        # Step 2: AI 深度评估
        try:
            ai_scores = self._ai_evaluate(resume, requirements, baseline_scores)
            logger.info("[AIEnhancedMatcher] AI evaluation successful")
            return ai_scores
        except Exception as e:
            # Step 3: 降级到算法基准分
            logger.warning(f"[AIEnhancedMatcher] AI evaluation failed, using baseline: {e}")
            return baseline_scores
    
    def _ai_evaluate(
        self,
        resume: Resume,
        requirements: JDRequirements,
        baseline_scores: dict[str, DimensionScore]
    ) -> dict[str, DimensionScore]:
        """
        使用 LLM 进行深度评估
        
        Args:
            resume: 候选人简历
            requirements: 岗位需求
            baseline_scores: 算法基准分
            
        Returns:
            AI 调整后的评分结果
            
        Raises:
            ValueError: LLM 调用或解析失败
        """
        # 构建 prompt
        prompt = self._build_prompt(resume, requirements, baseline_scores)
        
        # 调用 LLM
        try:
            response_data = self.llm_client.invoke(prompt, expect_json=True)
        except ValueError as e:
            logger.error(f"[AIEnhancedMatcher] LLM invocation failed: {e}")
            raise
        
        # 解析响应
        try:
            ai_scores = self._parse_ai_response(response_data, baseline_scores)
            return ai_scores
        except Exception as e:
            logger.error(f"[AIEnhancedMatcher] Failed to parse AI response: {e}")
            logger.error(f"[AIEnhancedMatcher] Response data: {json.dumps(response_data, ensure_ascii=False)[:500]}")
            raise ValueError(f"Failed to parse AI evaluation response: {e}") from e
    
    def _build_prompt(
        self,
        resume: Resume,
        requirements: JDRequirements,
        baseline_scores: dict[str, DimensionScore]
    ) -> str:
        """构建评估 prompt"""
        # 序列化为 JSON (可读性好)
        resume_json = json.dumps(resume.model_dump(), ensure_ascii=False, indent=2)
        requirements_json = json.dumps(requirements.model_dump(), ensure_ascii=False, indent=2)
        
        # 提取基准分
        baseline_hard_skills = baseline_scores["hard_skills"].score
        baseline_experience = baseline_scores["experience"].score
        baseline_education = baseline_scores["education"].score
        baseline_soft_skills = baseline_scores["soft_skills"].score
        
        # 填充模板
        return AI_EVALUATION_PROMPT.format(
            resume_json=resume_json,
            requirements_json=requirements_json,
            baseline_hard_skills=baseline_hard_skills,
            baseline_experience=baseline_experience,
            baseline_education=baseline_education,
            baseline_soft_skills=baseline_soft_skills
        )
    
    def _parse_ai_response(
        self,
        response_data: dict,
        baseline_scores: dict[str, DimensionScore]
    ) -> dict[str, DimensionScore]:
        """
        解析 AI 响应,转换为 DimensionScore 对象
        
        Args:
            response_data: LLM 返回的 JSON 数据
            baseline_scores: 算法基准分 (用于补充 matched/missing 字段)
            
        Returns:
            AI 调整后的 DimensionScore 字典
        """
        dimensions_data = response_data.get("dimensions", {})
        
        result = {}
        for dim_name in ["hard_skills", "experience", "education", "soft_skills"]:
            ai_dim = dimensions_data.get(dim_name, {})
            baseline_dim = baseline_scores[dim_name]
            
            # 构建 DimensionScore
            result[dim_name] = DimensionScore(
                score=ai_dim.get("score", baseline_dim.score),
                matched=baseline_dim.matched,  # 保留算法识别的匹配项
                missing=baseline_dim.missing,  # 保留算法识别的缺失项
                detail=baseline_dim.detail,  # 保留算法的详情
                # AI 增强字段
                baseline_score=ai_dim.get("baseline", baseline_dim.score),
                adjustment_reasoning=ai_dim.get("adjustment_reasoning"),
                highlights=ai_dim.get("highlights"),
                concerns=ai_dim.get("concerns")
            )
        
        return result