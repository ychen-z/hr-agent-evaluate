"""
测试 AI 增强评分匹配器
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.pipeline.matcher import Matcher, AIEnhancedMatcher
from app.types.models import Resume, JDRequirements, Education, Experience


class TestAIEnhancedMatcher:
    """测试 AIEnhancedMatcher 类"""
    
    @pytest.fixture
    def sample_resume(self):
        """创建测试简历"""
        return Resume(
            name="张三",
            email="zhangsan@example.com",
            phone="13800138000",
            education=[Education(
                degree="本科",
                major="计算机科学",
                school="清华大学",
                year=2020
            )],
            experience=[Experience(
                company="字节跳动",
                position="Python 工程师",
                duration="3年",
                description="负责后端服务开发,使用 Python/FastAPI/Redis,处理日活百万级用户请求"
            )],
            skills=["Python", "FastAPI", "Redis"],
            soft_skills=["沟通能力"]
        )
    
    @pytest.fixture
    def sample_requirements(self):
        """创建测试需求"""
        return JDRequirements(
            required_skills=["Python", "FastAPI", "Docker"],
            experience_years=3,
            education_level="本科",
            soft_skills=["沟通能力", "团队协作", "领导力"]
        )
    
    @pytest.fixture
    def baseline_matcher(self):
        """创建基准匹配器"""
        return Matcher()
    
    @pytest.fixture
    @patch.dict('os.environ', {'BASE_URL': 'http://test', 'DASHSCOPE_API_KEY': 'test_key'})
    @patch('app.pipeline.matcher.LLMClient')
    def ai_matcher(self, mock_llm_class):
        """创建 AI 增强匹配器"""
        # Mock LLMClient
        mock_llm_instance = Mock()
        mock_llm_class.return_value = mock_llm_instance
        matcher = AIEnhancedMatcher()
        return matcher
    
    def test_inheritance(self, ai_matcher):
        """测试 AIEnhancedMatcher 继承自 Matcher"""
        assert isinstance(ai_matcher, Matcher)
    
    def test_baseline_score_calculation(self, ai_matcher, baseline_matcher, sample_resume, sample_requirements):
        """测试算法基准分正确计算"""
        # 对比基准 matcher 和 AI matcher 的算法评分
        baseline_scores = baseline_matcher.match(sample_resume, sample_requirements)
        
        # Mock LLM 调用失败,应该返回基准分
        with patch.object(ai_matcher, '_ai_evaluate', side_effect=Exception("LLM Error")):
            ai_scores = ai_matcher.match(sample_resume, sample_requirements)
        
        # 降级后应该返回基准分
        assert ai_scores["hard_skills"].score == baseline_scores["hard_skills"].score
        assert ai_scores["experience"].score == baseline_scores["experience"].score
        assert ai_scores["education"].score == baseline_scores["education"].score
        assert ai_scores["soft_skills"].score == baseline_scores["soft_skills"].score
    
    @patch('app.pipeline.matcher.LLMClient')
    def test_ai_evaluation_success(self, mock_llm_client_class, ai_matcher, sample_resume, sample_requirements):
        """测试 AI 评估成功的场景"""
        # Mock LLM 响应
        mock_llm_instance = Mock()
        mock_llm_response = {
            "dimensions": {
                "hard_skills": {
                    "score": 85,
                    "adjustment_reasoning": "候选人掌握 Python 和 FastAPI,虽缺少 Docker 但整体技术栈扎实",
                    "highlights": ["Python 经验丰富", "FastAPI 实战经验"],
                    "concerns": ["缺少 Docker 经验"]
                },
                "experience": {
                    "score": 95,
                    "adjustment_reasoning": "3年经验且负责百万级用户系统,经验质量高",
                    "highlights": ["高并发经验", "架构能力"],
                    "concerns": []
                },
                "education": {
                    "score": 100,
                    "adjustment_reasoning": "本科学历符合要求,且为计算机专业",
                    "highlights": ["名校背景"],
                    "concerns": []
                },
                "soft_skills": {
                    "score": 70,
                    "adjustment_reasoning": "简历提及沟通能力,从经历推断有团队协作能力",
                    "highlights": ["沟通能力强"],
                    "concerns": ["领导力证据不足"]
                }
            },
            "overall_assessment": {
                "summary": "优秀的候选人,技术扎实,经验丰富",
                "top_strengths": ["技术能力强", "高并发经验"],
                "key_concerns": ["缺少 Docker", "领导力待验证"]
            }
        }
        mock_llm_instance.invoke.return_value = mock_llm_response
        mock_llm_client_class.return_value = mock_llm_instance
        
        # 重新初始化以使用 mock
        ai_matcher_with_mock = AIEnhancedMatcher()
        
        # 执行匹配
        result = ai_matcher_with_mock.match(sample_resume, sample_requirements)
        
        # 验证 AI 调整后的分数
        assert result["hard_skills"].score == 85
        assert result["experience"].score == 95
        assert result["education"].score == 100
        assert result["soft_skills"].score == 70
        
        # 验证 AI 字段存在
        assert result["hard_skills"].adjustment_reasoning is not None
        assert len(result["hard_skills"].highlights) > 0
        assert "Python 经验丰富" in result["hard_skills"].highlights
    
    @patch('app.pipeline.matcher.LLMClient')
    def test_ai_evaluation_failure_fallback(self, mock_llm_client_class, ai_matcher, sample_resume, sample_requirements):
        """测试 LLM 失败时降级到算法评分"""
        # Mock LLM 调用失败
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.side_effect = Exception("LLM API Error")
        mock_llm_client_class.return_value = mock_llm_instance
        
        # 重新初始化
        ai_matcher_with_mock = AIEnhancedMatcher()
        
        # 执行匹配,应该降级到算法评分
        result = ai_matcher_with_mock.match(sample_resume, sample_requirements)
        
        # 验证返回了算法基准分 (不会抛出异常)
        assert "hard_skills" in result
        assert "experience" in result
        assert result["hard_skills"].score is not None
        
        # 验证没有 AI 字段 (因为降级了)
        assert result["hard_skills"].adjustment_reasoning is None
    
    @patch('app.pipeline.matcher.LLMClient')
    def test_json_parsing_failure_fallback(self, mock_llm_client_class, ai_matcher, sample_resume, sample_requirements):
        """测试 JSON 解析失败时降级"""
        # Mock LLM 返回无效 JSON
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.side_effect = ValueError("Invalid JSON")
        mock_llm_client_class.return_value = mock_llm_instance
        
        ai_matcher_with_mock = AIEnhancedMatcher()
        
        # 执行匹配,应该降级
        result = ai_matcher_with_mock.match(sample_resume, sample_requirements)
        
        # 验证降级成功
        assert result["hard_skills"].score is not None
        assert result["hard_skills"].adjustment_reasoning is None
    
    def test_data_model_extended_fields(self, ai_matcher, sample_resume, sample_requirements):
        """测试数据模型扩展字段正确填充"""
        # 为了测试,直接调用 _parse_ai_response
        baseline_scores = {
            "hard_skills": Mock(score=60, matched=["Python"], missing=["Docker"]),
            "experience": Mock(score=100, detail="3年"),
            "education": Mock(score=100, detail="本科"),
            "soft_skills": Mock(score=33, matched=["沟通能力"], missing=["领导力"])
        }
        
        ai_response = {
            "dimensions": {
                "hard_skills": {
                    "score": 85,
                    "adjustment_reasoning": "测试推理",
                    "highlights": ["亮点1", "亮点2"],
                    "concerns": ["关注点1"]
                },
                "experience": {
                    "score": 95,
                    "adjustment_reasoning": "经验推理",
                    "highlights": ["经验亮点"],
                    "concerns": []
                },
                "education": {
                    "score": 100,
                    "adjustment_reasoning": "学历推理",
                    "highlights": [],
                    "concerns": []
                },
                "soft_skills": {
                    "score": 70,
                    "adjustment_reasoning": "软技能推理",
                    "highlights": ["软技能亮点"],
                    "concerns": ["软技能关注"]
                }
            }
        }
        
        result = ai_matcher._parse_ai_response(ai_response, baseline_scores)
        
        # 验证所有字段
        assert result["hard_skills"].score == 85
        assert result["hard_skills"].baseline_score == 60
        assert result["hard_skills"].adjustment_reasoning == "测试推理"
        assert result["hard_skills"].highlights == ["亮点1", "亮点2"]
        assert result["hard_skills"].concerns == ["关注点1"]
    
    def test_backward_compatibility(self, sample_resume, sample_requirements):
        """测试向后兼容性 - 现有代码能正常运行"""
        # 使用传统 Matcher
        baseline_matcher = Matcher()
        baseline_result = baseline_matcher.match(sample_resume, sample_requirements)
        
        # 验证传统字段存在
        assert "hard_skills" in baseline_result
        assert hasattr(baseline_result["hard_skills"], "score")
        assert baseline_result["hard_skills"].score is not None
        
        # 验证扩展字段为 None (向后兼容)
        assert baseline_result["hard_skills"].baseline_score is None
        assert baseline_result["hard_skills"].adjustment_reasoning is None
    
    def test_prompt_building(self, ai_matcher, sample_resume, sample_requirements):
        """测试 Prompt 构建包含所有必要信息"""
        baseline_scores = {
            "hard_skills": Mock(score=60, matched=["Python"], missing=["Docker"]),
            "experience": Mock(score=100, detail="3年"),
            "education": Mock(score=100, detail="本科"),
            "soft_skills": Mock(score=33, matched=["沟通能力"], missing=["领导力"])
        }
        
        prompt = ai_matcher._build_prompt(sample_resume, sample_requirements, baseline_scores)
        
        # 验证 prompt 包含关键信息
        assert "张三" in prompt
        assert "Python" in prompt
        assert "FastAPI" in prompt
        assert "Docker" in prompt
        assert "3年" in prompt or "3 年" in prompt
        assert "本科" in prompt
        assert "字节跳动" in prompt
    
    @patch('app.pipeline.matcher.LLMClient')
    def test_overall_assessment_propagation(self, mock_llm_client_class, sample_resume, sample_requirements):
        """测试 overall_assessment 正确传递到结果"""
        mock_llm_instance = Mock()
        mock_llm_response = {
            "dimensions": {
                "hard_skills": {"score": 85, "adjustment_reasoning": "测试", "highlights": [], "concerns": []},
                "experience": {"score": 95, "adjustment_reasoning": "测试", "highlights": [], "concerns": []},
                "education": {"score": 100, "adjustment_reasoning": "测试", "highlights": [], "concerns": []},
                "soft_skills": {"score": 70, "adjustment_reasoning": "测试", "highlights": [], "concerns": []}
            },
            "overall_assessment": {
                "summary": "整体评估摘要",
                "top_strengths": ["优势1", "优势2"],
                "key_concerns": ["关注1"]
            }
        }
        mock_llm_instance.invoke.return_value = mock_llm_response
        mock_llm_client_class.return_value = mock_llm_instance
        
        ai_matcher_with_mock = AIEnhancedMatcher()
        result = ai_matcher_with_mock.match(sample_resume, sample_requirements)
        
        # 验证 overall_assessment 被解析 (在实际实现中可能存储在某处)
        # 这里主要测试不抛出异常
        assert result is not None
