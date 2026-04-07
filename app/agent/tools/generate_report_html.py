import json
import subprocess
from pathlib import Path
from app.utils.logger import traced_tool

_SKILL_SCRIPT = Path.home() / ".codemaker" / "skills" / "ui-ux-pro-max" / "scripts" / "search.py"

_DEFAULT_TOKENS = {
    "heading_font": "Inter",
    "body_font": "Inter",
    "google_fonts_import": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
    "primary": "#1E3A5F",
    "accent": "#2563EB",
    "background": "#F8FAFC",
    "text": "#1E293B",
    "muted": "#64748B",
}

# Enhanced styles for AI-driven reports
_ENHANCED_STYLES = """
    /* Highlight cards */
    .highlight-card {
        background: linear-gradient(135deg, #E0F2FE 0%, #DBEAFE 100%);
        border-left: 4px solid #3B82F6;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .highlight-card .icon {
        font-size: 1.5em;
        margin-right: 12px;
        display: inline-block;
    }
    .highlight-card .title {
        font-weight: 600;
        color: #1E40AF;
        margin-bottom: 4px;
    }
    
    /* Concern cards */
    .concern-card {
        background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
        border-left: 4px solid #F59E0B;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .concern-card .icon {
        font-size: 1.5em;
        margin-right: 12px;
        display: inline-block;
    }
    .concern-card .title {
        font-weight: 600;
        color: #92400E;
        margin-bottom: 4px;
    }
    
    /* AI reasoning box */
    .ai-reasoning-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        margin-top: 12px;
        font-size: 0.9em;
        line-height: 1.6;
    }
    .ai-reasoning-box .header {
        font-weight: 700;
        color: #6366F1;
        margin-bottom: 8px;
        display: block;
    }
    .ai-reasoning-box .header::before {
        content: '🤖 ';
    }
    .baseline-score {
        color: #94A3B8;
        text-decoration: line-through;
    }
    .adjusted-score {
        color: #16A34A;
        font-weight: 700;
    }
    
    /* Comparison table */
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 0.95em;
    }
    .comparison-table th {
        background: #F1F5F9;
        padding: 12px;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid #CBD5E1;
        color: #475569;
    }
    .comparison-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #E2E8F0;
    }
    .comparison-table .bar {
        font-family: monospace;
        color: #64748B;
    }
    .diff-positive {
        color: #16A34A;
        font-weight: 600;
    }
    .diff-negative {
        color: #DC2626;
        font-weight: 600;
    }
    .diff-neutral {
        color: #64748B;
    }
    
    /* Section containers */
    .section-container {
        margin-bottom: 32px;
    }
    .section-header {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748B;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #E2E8F0;
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        .highlight-card, .concern-card {
            padding: 12px 16px;
        }
        .highlight-card .icon, .concern-card .icon {
            font-size: 1.2em;
        }
        .ai-reasoning-box {
            font-size: 0.85em;
            padding: 12px;
        }
        .comparison-table {
            font-size: 0.8em;
        }
        .comparison-table th, .comparison-table td {
            padding: 8px 6px;
        }
    }
    @media (max-width: 480px) {
        .comparison-table .bar {
            display: none;
        }
    }
    
    /* Print styles */
    @media print {
        .highlight-card, .concern-card {
            background: #fff;
            border: 1px solid #ccc;
            box-shadow: none;
            page-break-inside: avoid;
        }
        .ai-reasoning-box {
            background: #fff;
            border: 1px solid #999;
            page-break-inside: avoid;
        }
        .comparison-table {
            page-break-inside: avoid;
        }
        body {
            padding: 0;
        }
        .card {
            box-shadow: none;
        }
    }
"""


def _run_search(query: str, domain: str) -> list:
    """Run ui-ux-pro-max search script, return parsed JSON list or [] on any failure."""
    try:
        result = subprocess.run(
            ["python3", str(_SKILL_SCRIPT), query, "--domain", domain],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except Exception:
        return []


def _extract_tokens(records: list, field_map: dict, tokens: dict) -> None:
    """Extract fields from first search result into tokens dict, skip if missing."""
    if not records:
        return
    first = records[0]
    for src_field, dst_key in field_map.items():
        value = first.get(src_field)
        if value:
            tokens[dst_key] = value


def _gather_design_tokens() -> dict:
    tokens = dict(_DEFAULT_TOKENS)

    product_records = _run_search("HR report professional", "product")
    _extract_tokens(product_records, {
        "description": "product_description",
    }, tokens)

    style_records = _run_search("minimal professional clean", "style")
    _extract_tokens(style_records, {
        "primary_color": "primary",
        "background": "background",
    }, tokens)

    typography_records = _run_search("corporate professional", "typography")
    _extract_tokens(typography_records, {
        "heading_font": "heading_font",
        "body_font": "body_font",
        "google_fonts_import": "google_fonts_import",
    }, tokens)

    color_records = _run_search("hr saas dashboard", "color")
    _extract_tokens(color_records, {
        "primary": "primary",
        "accent": "accent",
        "background": "background",
        "text": "text",
    }, tokens)

    return tokens


def _render_html(report: dict, tokens: dict) -> str:
    overall = report.get("overall_score", 0)
    recommendation = report.get("recommendation", "")
    reasons = report.get("reasons", [])
    dimensions = report.get("dimensions", {})

    rec_color = "#16A34A" if recommendation == "\u63a8\u8350" else "#DC2626"

    dim_labels = {
        "hard_skills": "\u6280\u672f\u6280\u80fd",
        "experience": "\u5de5\u4f5c\u7ecf\u9a8c",
        "education": "\u6559\u80b2\u80cc\u666f",
        "soft_skills": "\u8f6f\u6280\u80fd",
    }

    dim_bars = ""
    for key, label in dim_labels.items():
        dim = dimensions.get(key, {})
        score = dim.get("score", 0)
        matched = ", ".join(dim.get("matched", [])) or "\u2014"
        dim_bars += f"""
        <div style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-weight:600;color:{tokens['text']}">{label}</span>
            <span style="color:{tokens['accent']};font-weight:700">{score}</span>
          </div>
          <div style="background:#E2E8F0;border-radius:999px;height:8px;">
            <div style="background:{tokens['accent']};width:{score}%;height:8px;border-radius:999px;transition:width 0.6s;"></div>
          </div>
          <div style="font-size:12px;color:{tokens['muted']};margin-top:4px;">\u5339\u914d\u9879\uff1a{matched}</div>
        </div>"""

    reasons_html = "".join(f'<li style="margin-bottom:6px;">{r}</li>' for r in reasons)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>\u5019\u9009\u4eba\u8bc4\u4f30\u62a5\u544a</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="{tokens['google_fonts_import']}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: '{tokens['body_font']}', sans-serif;
      background: {tokens['background']};
      color: {tokens['text']};
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
      background: {tokens['primary']};
      padding: 32px 40px;
      color: #fff;
    }}
    .header h1 {{
      font-family: '{tokens['heading_font']}', sans-serif;
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 8px;
      opacity: 0.9;
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
      font-family: '{tokens['heading_font']}', sans-serif;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: {tokens['muted']};
      margin-bottom: 16px;
    }}
    .reasons {{
      list-style: none;
      padding: 0;
    }}
    .reasons li::before {{
      content: '\u2713 ';
      color: #16A34A;
      font-weight: 700;
    }}
    .divider {{
      border: none;
      border-top: 1px solid #E2E8F0;
      margin: 28px 0;
    }}
    @media (max-width: 480px) {{
      .header, .body {{ padding: 24px 20px; }}
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>\u5019\u9009\u4eba\u8bc4\u4f30\u62a5\u544a</h1>
      <div class="score-row">
        <div class="score-circle">
          <span class="score-num">{overall}</span>
          <span class="score-label">\u603b\u5206</span>
        </div>
        <div>
          <div class="badge">{recommendation}</div>
        </div>
      </div>
    </div>
    <div class="body">
      <div class="section-title">\u5404\u7ef4\u5ea6\u8bc4\u5206</div>
      {dim_bars}
      <hr class="divider">
      <div class="section-title">\u8bc4\u4f30\u7406\u7531</div>
      <ul class="reasons">{reasons_html}</ul>
    </div>
  </div>
</body>
</html>"""


# Helper functions for icon mapping
def _get_highlight_icon(text: str) -> str:
    """Map highlight text to appropriate emoji icon."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ['高并发', '并发', '高性能', '架构']):
        return '🚀'
    if any(kw in text_lower for kw in ['技术', '技能', '框架', '语言']):
        return '💻'
    if any(kw in text_lower for kw in ['学历', '学校', '大学', '背景']):
        return '🎓'
    if any(kw in text_lower for kw in ['经验', '项目', '工作']):
        return '💼'
    if any(kw in text_lower for kw in ['沟通', '协作', '团队']):
        return '🤝'
    return '⭐'


def _get_concern_icon(text: str) -> str:
    """Map concern text to appropriate emoji icon."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ['缺少', '缺乏', '没有']):
        return '⚡'
    if any(kw in text_lower for kw in ['领导', '管理', '带人']):
        return '👥'
    if any(kw in text_lower for kw in ['经验', '年限']):
        return '📅'
    return '⚠️'


def _render_bar_chart(score: int) -> str:
    """Generate text-based bar chart using Unicode block characters."""
    bars = int(score / 10)  # 1 bar per 10 points
    return '▓' * bars + '░' * (10 - bars)


def _has_ai_data(report: dict) -> bool:
    """Check if report contains AI-enhanced data."""
    # Check for top_strengths or key_concerns
    if report.get('top_strengths') or report.get('key_concerns'):
        return True
    
    # Check if any dimension has AI fields
    dimensions = report.get('dimensions', {})
    for dim in dimensions.values():
        if isinstance(dim, dict):
            if dim.get('adjustment_reasoning') or dim.get('highlights') or dim.get('concerns'):
                return True
    
    return False


def _should_show_comparison(dimensions: dict) -> bool:
    """Check if comparison table should be shown."""
    for dim in dimensions.values():
        if isinstance(dim, dict) and dim.get('baseline_score') is not None:
            return True
    return False


def _render_overview_section(report: dict, tokens: dict) -> str:
    """Render the overview section with score and recommendation."""
    overall = report.get("overall_score", 0)
    recommendation = report.get("recommendation", "")
    rec_color = "#16A34A" if recommendation == "推荐" else "#DC2626"
    rec_icon = "✅" if recommendation == "推荐" else "❌"
    
    # Generate summary text
    if recommendation == "推荐":
        summary = "该候选人综合实力突出,技术能力与项目经验俱佳,建议优先安排面试"
    else:
        summary = "该候选人与岗位要求存在一定差距,建议谨慎考虑"
    
    return f"""
    <div class="section-container">
        <div style="display: flex; align-items: center; gap: 24px; margin-bottom: 24px;">
            <div class="score-circle" style="width: 100px; height: 100px;">
                <span class="score-num" style="font-size: 32px;">{overall}</span>
                <span class="score-label">综合分</span>
                <span class="score-label" style="font-size: 10px;">满分100</span>
            </div>
            <div>
                <div style="display: inline-block; padding: 8px 20px; border-radius: 999px; font-weight: 700; font-size: 16px; background: {rec_color}; color: #fff; margin-bottom: 8px;">
                    {rec_icon} {recommendation}
                </div>
                <p style="color: {tokens['muted']}; font-size: 14px; line-height: 1.6;">{summary}</p>
            </div>
        </div>
    </div>
    """


def _render_highlights_section(top_strengths: list) -> str:
    """Render highlight cards section."""
    if not top_strengths:
        return ""
    
    cards_html = ""
    for strength in top_strengths:
        icon = _get_highlight_icon(strength)
        cards_html += f"""
        <div class="highlight-card">
            <span class="icon">{icon}</span>
            <span class="title">{strength}</span>
        </div>
        """
    
    return f"""
    <div class="section-container">
        <div class="section-header">💡 核心亮点</div>
        {cards_html}
    </div>
    """


def _render_concerns_section(key_concerns: list) -> str:
    """Render concern cards section."""
    if not key_concerns:
        return ""
    
    cards_html = ""
    for concern in key_concerns:
        icon = _get_concern_icon(concern)
        cards_html += f"""
        <div class="concern-card">
            <span class="icon">{icon}</span>
            <span class="title">{concern}</span>
            <div style="margin-left: 36px; font-size: 0.9em; color: #78350F; margin-top: 4px;">
                建议面试时重点确认
            </div>
        </div>
        """
    
    return f"""
    <div class="section-container">
        <div class="section-header">⚠️ 需要关注的点</div>
        {cards_html}
    </div>
    """


def _render_dimension_detail(dimension: dict, dim_name: str, dim_label: str, tokens: dict) -> str:
    """Render detailed scoring for a single dimension."""
    score = dimension.get('score', 0)
    matched = dimension.get('matched', [])
    missing = dimension.get('missing', [])
    detail = dimension.get('detail', '')
    
    matched_str = ", ".join(matched) if matched else "—"
    missing_str = ", ".join(missing) if missing else "—"
    
    # Progress bar
    progress_html = f"""
    <div style="background:#E2E8F0;border-radius:999px;height:10px;margin: 8px 0;">
        <div style="background:{tokens['accent']};width:{score}%;height:10px;border-radius:999px;"></div>
    </div>
    """
    
    # AI reasoning box (if available)
    ai_box_html = ""
    if dimension.get('adjustment_reasoning'):
        baseline = dimension.get('baseline_score', score)
        reasoning = dimension.get('adjustment_reasoning', '')
        
        ai_box_html = f"""
        <div class="ai-reasoning-box">
            <span class="header">AI 评估 (基准分: <span class="baseline-score">{baseline}</span> → 调整后: <span class="adjusted-score">{score}</span>)</span>
            <p>{reasoning}</p>
        </div>
        """
    
    return f"""
    <div style="margin-bottom: 24px; padding: 16px; background: #F9FAFB; border-radius: 8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-weight:700;font-size:16px;color:{tokens['text']}">{dim_label}</span>
            <span style="color:{tokens['accent']};font-weight:700;font-size:24px;">{score}</span>
        </div>
        {progress_html}
        <div style="font-size:13px;color:{tokens['muted']};margin-top:8px;">
            <div>🔍 匹配项: {matched_str}</div>
            {f'<div style="margin-top:4px;">❌ 缺失项: {missing_str}</div>' if missing else ''}
            {f'<div style="margin-top:4px;">📋 {detail}</div>' if detail else ''}
        </div>
        {ai_box_html}
    </div>
    """


def _render_comparison_table(dimensions: dict, tokens: dict) -> str:
    """Render algorithm vs AI comparison table."""
    if not _should_show_comparison(dimensions):
        return ""
    
    dim_labels = {
        "hard_skills": "技能",
        "experience": "经验",
        "education": "学历",
        "soft_skills": "软技能",
    }
    
    rows_html = ""
    total_baseline = 0
    total_adjusted = 0
    count = 0
    
    for key, label in dim_labels.items():
        dim = dimensions.get(key, {})
        if not isinstance(dim, dict):
            continue
            
        score = dim.get('score', 0)
        baseline = dim.get('baseline_score')
        
        if baseline is not None:
            diff = score - baseline
            diff_class = 'diff-positive' if diff > 0 else ('diff-negative' if diff < 0 else 'diff-neutral')
            diff_arrow = '⬆' if diff > 0 else ('⬇' if diff < 0 else '━')
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            
            baseline_bar = _render_bar_chart(baseline)
            adjusted_bar = _render_bar_chart(score)
            
            rows_html += f"""
            <tr>
                <td>{label}</td>
                <td>{baseline} <span class="bar">{baseline_bar}</span></td>
                <td>{score} <span class="bar">{adjusted_bar}</span></td>
                <td class="{diff_class}">{diff_str} {diff_arrow}</td>
            </tr>
            """
            
            total_baseline += baseline
            total_adjusted += score
            count += 1
    
    # Add total row
    if count > 0:
        avg_baseline = total_baseline // count
        avg_adjusted = total_adjusted // count
        diff = avg_adjusted - avg_baseline
        diff_class = 'diff-positive' if diff > 0 else ('diff-negative' if diff < 0 else 'diff-neutral')
        diff_arrow = '⬆' if diff > 0 else ('⬇' if diff < 0 else '━')
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        
        rows_html += f"""
        <tr style="font-weight: 700; border-top: 2px solid #CBD5E1;">
            <td>综合</td>
            <td>{avg_baseline} <span class="bar">{_render_bar_chart(avg_baseline)}</span></td>
            <td>{avg_adjusted} <span class="bar">{_render_bar_chart(avg_adjusted)}</span></td>
            <td class="{diff_class}">{diff_str} {diff_arrow}</td>
        </tr>
        """
    
    return f"""
    <div class="section-container">
        <div class="section-header">📈 评分对比分析 (算法 vs AI 增强)</div>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>维度</th>
                    <th>算法基准分</th>
                    <th>AI 调整后</th>
                    <th>差异</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <p style="font-size: 0.9em; color: {tokens['muted']}; margin-top: 8px;">
            💡 AI 增强识别了算法遗漏的技能和软技能证据,使评分更准确
        </p>
    </div>
    """


def _generate_interview_suggestions(dimensions: dict) -> list:
    """Generate interview suggestions based on evaluation results."""
    suggestions = []
    
    dim_labels = {
        "hard_skills": "技术技能",
        "experience": "工作经验",
        "education": "教育背景",
        "soft_skills": "软技能",
    }
    
    # Rule 1: From concerns
    for dim_name, dim in dimensions.items():
        if not isinstance(dim, dict):
            continue
            
        concerns = dim.get('concerns', [])
        if concerns:
            label = dim_labels.get(dim_name, dim_name)
            suggestions.append({
                'topic': f"{label}方面",
                'concerns': concerns,
                'advice': f"建议面试时重点考察{label}"
            })
    
    # Rule 2: From missing skills
    hard_skills = dimensions.get('hard_skills', {})
    if isinstance(hard_skills, dict):
        missing = hard_skills.get('missing', [])
        if missing:
            suggestions.append({
                'topic': '技能学习能力',
                'concerns': [f"缺少 {', '.join(missing[:3])} 等技能"],
                'advice': f"评估候选人学习 {missing[0]} 的意愿和能力"
            })
    
    # Rule 3: Low score dimensions
    for dim_name, dim in dimensions.items():
        if not isinstance(dim, dict):
            continue
            
        score = dim.get('score', 0)
        if score < 70 and dim_name in dim_labels:
            label = dim_labels[dim_name]
            suggestions.append({
                'topic': f"{label}深入了解",
                'concerns': [f"{label}评分较低 ({score}分)"],
                'advice': f"深入了解候选人在{label}方面的实际情况"
            })
    
    # Fallback: Generic suggestions
    if not suggestions:
        suggestions.append({
            'topic': '综合评估',
            'concerns': [],
            'advice': '验证项目经历真实性和技术深度'
        })
    
    return suggestions


def _render_interview_suggestions(dimensions: dict, tokens: dict) -> str:
    """Render interview suggestions section."""
    suggestions = _generate_interview_suggestions(dimensions)
    
    items_html = ""
    for i, sug in enumerate(suggestions[:5], 1):  # Limit to 5 suggestions
        topic = sug['topic']
        advice = sug['advice']
        concerns = sug.get('concerns', [])
        
        concerns_html = ""
        if concerns:
            concerns_html = "<ul style='margin: 8px 0 0 20px; font-size: 0.9em; color: #64748B;'>"
            for concern in concerns[:2]:  # Max 2 concerns per suggestion
                concerns_html += f"<li>{concern}</li>"
            concerns_html += "</ul>"
        
        items_html += f"""
        <div style="margin-bottom: 16px; padding: 12px; background: #F8FAFC; border-left: 3px solid {tokens['accent']}; border-radius: 4px;">
            <div style="font-weight: 600; color: {tokens['text']};">{i}️⃣ {topic}</div>
            <div style="margin-top: 6px; color: #475569;">{advice}</div>
            {concerns_html}
        </div>
        """
    
    return f"""
    <div class="section-container">
        <div class="section-header">🎯 面试建议</div>
        <p style="color: {tokens['muted']}; margin-bottom: 16px; font-size: 0.95em;">
            基于以上评估,建议面试时重点考察以下方面:
        </p>
        {items_html}
    </div>
    """


def _render_enhanced_html(report: dict, tokens: dict) -> str:
    """Render enhanced HTML report with AI insights and multi-section layout."""
    overall = report.get("overall_score", 0)
    recommendation = report.get("recommendation", "")
    dimensions = report.get("dimensions", {})
    top_strengths = report.get("top_strengths", [])
    key_concerns = report.get("key_concerns", [])
    
    rec_color = "#16A34A" if recommendation == "推荐" else "#DC2626"
    
    dim_labels = {
        "hard_skills": "技术技能匹配度",
        "experience": "工作经验匹配度",
        "education": "教育背景匹配度",
        "soft_skills": "软技能匹配度",
    }
    
    # Build sections
    overview_html = _render_overview_section(report, tokens)
    highlights_html = _render_highlights_section(top_strengths)
    concerns_html = _render_concerns_section(key_concerns)
    
    # Render each dimension detail
    dimensions_html = ""
    for dim_name, dim_label in dim_labels.items():
        dim_data = dimensions.get(dim_name)
        if dim_data and isinstance(dim_data, dict):
            dimensions_html += _render_dimension_detail(dim_data, dim_name, dim_label, tokens)
    
    comparison_html = _render_comparison_table(dimensions, tokens)
    suggestions_html = _render_interview_suggestions(dimensions, tokens)
    
    # Generate timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>候选人评估报告</title>
  <link href="{tokens['google_fonts_import']}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: '{tokens['body_font']}', sans-serif;
      background: {tokens['background']};
      color: {tokens['text']};
      min-height: 100vh;
      padding: 40px 16px;
    }}
    .report-container {{
      max-width: 800px;
      margin: 0 auto;
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      overflow: hidden;
    }}
    .header {{
      background: {tokens['primary']};
      padding: 24px 40px;
      color: #fff;
      border-bottom: 4px solid {tokens['accent']};
    }}
    .header h1 {{
      font-family: '{tokens['heading_font']}', sans-serif;
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 4px;
    }}
    .header .timestamp {{
      font-size: 12px;
      opacity: 0.8;
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
    .body {{
      padding: 32px 40px;
    }}
    {_ENHANCED_STYLES}
    @media (max-width: 480px) {{
      .header, .body {{ padding: 24px 20px; }}
    }}
  </style>
</head>
<body>
  <div class="report-container" role="main" aria-label="候选人评估报告">
    <div class="header">
      <h1>📋 候选人评估报告</h1>
      <div class="timestamp">生成时间: {timestamp}</div>
    </div>
    <div class="body">
      {overview_html}
      {highlights_html}
      {concerns_html}
      <div class="section-container">
        <div class="section-header">📊 详细维度评分</div>
        {dimensions_html}
      </div>
      {comparison_html}
      {suggestions_html}
      <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E2E8F0; text-align: center; font-size: 12px; color: #94A3B8;">
        <p>报告生成: AI 增强评分系统 v1.1 · Powered by hr-agent</p>
      </div>
    </div>
  </div>
</body>
</html>"""


@traced_tool("generate_report_html")
def run_generate_report_html(report: dict) -> str:
    """Generate a professional HTML report from a MatchReport dict. Returns raw HTML string."""
    import os
    import logging
    
    logger = logging.getLogger("hr_agent.generate_report_html")
    tokens = _gather_design_tokens()
    
    # Check if enhanced report is enabled
    use_enhanced = os.getenv("USE_ENHANCED_REPORT", "false").lower() == "true"
    
    if use_enhanced:
        logger.info("[generate_report_html] Using enhanced report layout")
        return _render_enhanced_html(report, tokens)
    else:
        logger.info("[generate_report_html] Using legacy report layout")
        return _render_html(report, tokens)
