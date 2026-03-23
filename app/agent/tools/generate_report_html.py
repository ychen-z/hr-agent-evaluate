import json
import subprocess
from pathlib import Path

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


def run_generate_report_html(report: dict) -> str:
    """Generate a professional HTML report from a MatchReport dict. Returns raw HTML string."""
    tokens = _gather_design_tokens()
    return _render_html(report, tokens)
