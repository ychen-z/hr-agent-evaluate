from fastapi import APIRouter, HTTPException, Header
from app.types.models import MatchRequest, MatchReport
from app.pipeline.jd_parser import JDParser
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter
import os

router = APIRouter()
_parser = None
matcher = Matcher()
reporter = Reporter()


def _get_parser() -> JDParser:
    global _parser
    if _parser is None:
        _parser = JDParser()
    return _parser


@router.post("/api/v1/match", response_model=MatchReport)
async def match_resume(
    request: MatchRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    api_key = os.getenv("API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not request.job_description or len(request.job_description.strip()) < 5:
        raise HTTPException(status_code=400, detail="Job description too short")
    
    try:
        requirements = _get_parser().parse(request.job_description)
        
        if not requirements.required_skills and requirements.experience_years == 0:
            raise HTTPException(status_code=400, detail="Unable to parse JD requirements")
        
        dimension_scores = matcher.match(request.resume, requirements)
        
        if not dimension_scores:
            raise HTTPException(status_code=500, detail="Unable to calculate scores")
        
        result = reporter.generate(dimension_scores)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

from fastapi.responses import HTMLResponse
from app.agent.hr_agent import HRAgent, AgentLoopError, _html_store
from app.types.models import AgentResult
import uuid


def _generate_mock_html(report: dict) -> str:
    """生成 Mock HTML 报告"""
    overall = report.get("overall_score", 0)
    recommendation = report.get("recommendation", "")
    reasons = report.get("reasons", [])
    dimensions = report.get("dimensions", {})
    
    rec_color = "#16A34A" if recommendation == "推荐" else "#DC2626"
    
    dim_labels = {
        "hard_skills": "技术技能",
        "experience": "工作经验",
        "education": "教育背景",
        "soft_skills": "软技能",
    }
    
    dim_bars = ""
    for key, label in dim_labels.items():
        dim = dimensions.get(key, {})
        score = dim.get("score", 0)
        matched = ", ".join(dim.get("matched", [])) or "—"
        dim_bars += f"""
        <div style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-weight:600;color:#1E293B">{label}</span>
            <span style="color:#2563EB;font-weight:700">{score}</span>
          </div>
          <div style="background:#E2E8F0;border-radius:999px;height:8px;">
            <div style="background:#2563EB;width:{score}%;height:8px;border-radius:999px;"></div>
          </div>
          <div style="font-size:12px;color:#64748B;margin-top:4px;">匹配项：{matched}</div>
        </div>"""
    
    reasons_html = "".join(f'<li style="margin-bottom:6px;">✓ {r}</li>' for r in reasons)
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>候选人评估报告</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: #F8FAFC;
      color: #1E293B;
      min-height: 100vh;
      padding: 40px 16px;
    }}
    .card {{
      max-width: 680px;
      margin: 0 auto;
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      overflow: hidden;
    }}
    .header {{
      background: #1E3A5F;
      padding: 32px 40px;
      color: #fff;
    }}
    .header h1 {{
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .score-row {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .score-circle {{
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: rgba(255,255,255,0.15);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border: 3px solid rgba(255,255,255,0.4);
    }}
    .score-num {{
      font-size: 28px;
      font-weight: 700;
      line-height: 1;
    }}
    .score-label {{
      font-size: 11px;
      opacity: 0.8;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 18px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 14px;
      background: {rec_color};
      color: #fff;
    }}
    .body {{ padding: 32px 40px; }}
    .section-title {{
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #64748B;
      margin-bottom: 16px;
    }}
    .reasons {{
      list-style: none;
      padding: 0;
      color: #16A34A;
    }}
    .divider {{
      border: none;
      border-top: 1px solid #E2E8F0;
      margin: 28px 0;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>候选人评估报告</h1>
      <div class="score-row">
        <div class="score-circle">
          <span class="score-num">{overall}</span>
          <span class="score-label">总分</span>
        </div>
        <div>
          <div class="badge">{recommendation}</div>
        </div>
      </div>
    </div>
    <div class="body">
      <div class="section-title">各维度评分</div>
      {dim_bars}
      <hr class="divider">
      <div class="section-title">评估理由</div>
      <ul class="reasons">{reasons_html}</ul>
    </div>
  </div>
</body>
</html>"""


def _run_mock_agent(resume, jd_text: str) -> AgentResult:
    """Mock Agent 用于演示"""
    session_id = str(uuid.uuid4())
    
    # 简单的技能匹配逻辑
    resume_skills = set(s.lower() for s in resume.skills)
    jd_lower = jd_text.lower()
    
    # 检测 JD 中的技能关键词
    skill_keywords = ["python", "java", "javascript", "react", "vue", "fastapi", "django", "flask", 
                      "postgresql", "mysql", "redis", "docker", "kubernetes", "aws", "golang", "rust"]
    required_skills = [s for s in skill_keywords if s in jd_lower]
    
    # 计算技能匹配
    matched_skills = [s for s in resume.skills if s.lower() in jd_lower or any(r in s.lower() for r in required_skills)]
    missing_skills = [s for s in required_skills if s not in [m.lower() for m in resume.skills]]
    
    hard_score = min(100, len(matched_skills) * 25) if matched_skills else 60
    
    # 经验评分
    exp_years = 0
    for exp in resume.experience:
        if "年" in exp.duration:
            try:
                exp_years += int(exp.duration.replace("年", ""))
            except:
                exp_years += 3
    exp_score = min(100, exp_years * 20 + 40)
    
    # 教育评分
    edu_score = 80
    for edu in resume.education:
        if edu.degree in ["硕士", "博士"]:
            edu_score = 100
            break
    
    # 软技能评分
    soft_score = min(100, len(resume.soft_skills) * 25 + 50)
    
    overall_score = int((hard_score * 0.4 + exp_score * 0.25 + edu_score * 0.15 + soft_score * 0.2))
    
    recommendation = "推荐" if overall_score >= 70 else "不推荐"
    
    reasons = []
    if hard_score >= 70:
        reasons.append(f"技术技能匹配度高，掌握 {', '.join(matched_skills[:3])}")
    if exp_score >= 80:
        reasons.append(f"具备 {exp_years} 年相关工作经验")
    if edu_score >= 80:
        reasons.append("教育背景符合要求")
    if soft_score >= 70:
        reasons.append("软技能表现优秀")
    if not reasons:
        reasons.append("综合评估完成")
    
    report_dict = {
        "overall_score": overall_score,
        "dimensions": {
            "hard_skills": {"score": hard_score, "matched": matched_skills[:5], "missing": missing_skills[:3], "detail": None},
            "experience": {"score": exp_score, "matched": [], "missing": [], "detail": f"{exp_years}年工作经验"},
            "education": {"score": edu_score, "matched": [], "missing": [], "detail": None},
            "soft_skills": {"score": soft_score, "matched": resume.soft_skills[:3], "missing": [], "detail": None},
        },
        "recommendation": recommendation,
        "reasons": reasons
    }
    
    html = _generate_mock_html(report_dict)
    _html_store[session_id] = html
    
    reasoning = f"经过全面评估，该候选人综合得分 {overall_score} 分。" + "；".join(reasons) + f"。综合建议：{recommendation}。"
    
    report = MatchReport(**report_dict)
    return AgentResult(
        session_id=session_id,
        report=report,
        html=html,
        reasoning=reasoning,
    )


@router.post("/api/v1/agent/match", response_model=AgentResult)
async def agent_match_resume(
    request: MatchRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    api_key = os.getenv("API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.job_description or len(request.job_description.strip()) < 5:
        raise HTTPException(status_code=400, detail="Job description too short")

    # 检查是否有 LLM API Key，没有则使用 Mock 模式
    use_mock = not os.getenv("DASHSCOPE_API_KEY") or not os.getenv("BASE_URL")
    print(os.getenv("DASHSCOPE_API_KEY"))
    print(os.getenv("BASE_URL"))
    print("user_mock", use_mock)
    if use_mock:
        # Mock 模式用于演示
        return _run_mock_agent(request.resume, request.job_description)

    try:
        agent = HRAgent()
        result = agent.run(request.resume, request.job_description)
        return result
    except AgentLoopError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@router.get("/api/v1/agent/report/{session_id}", response_class=HTMLResponse)
async def get_agent_report(session_id: str):
    html = _html_store.get(session_id)
    if html is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(content=html)
