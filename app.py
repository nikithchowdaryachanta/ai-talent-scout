import html
import json
import os
import re
from io import BytesIO, StringIO
from pathlib import Path

import google.generativeai as genai
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

st.set_page_config(page_title="TalentScout AI", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

    :root {
      --saas-bg-deep: #0e1117;
      --saas-bg-main: #0e1117;
      --saas-bg-panel: #1c1f26;
      --saas-bg-panel-hover: #252830;
      --saas-border: rgba(255, 255, 255, 0.08);
      --saas-text-primary: #ffffff;
      --saas-text-secondary: #a0a3bd;
      --saas-text-muted: #6b6e8c;
      --saas-accent-blue: #4f8ef7;
      --saas-accent-blue-soft: rgba(79, 142, 247, 0.18);
      --saas-accent-green: #22c55e;
      --saas-accent-green-soft: rgba(34, 197, 94, 0.16);
      --saas-traffic-amber: #fbbf24;
      --saas-traffic-red: #ef4444;
    }

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .block-container {
      padding-top: 1.5rem;
      padding-bottom: 3rem;
      max-width: 1180px;
    }

    /* App shell: deep navy SaaS */
    .stApp {
      background: var(--saas-bg-deep) !important;
      color: var(--saas-text-primary);
    }
    [data-testid="stAppViewContainer"] > .main {
      background: var(--saas-bg-deep) !important;
    }
    section[data-testid="stMain"] > div {
      background: transparent !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
      background: var(--saas-bg-panel) !important;
      border-right: 1px solid var(--saas-border) !important;
    }
    [data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
      color: var(--saas-text-secondary) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
      color: var(--saas-text-primary) !important;
      font-weight: 700 !important;
    }

    /* Primary copy + hierarchy */
    .main .stMarkdown h1 { font-size: 2rem !important; font-weight: 700 !important; letter-spacing: -0.03em; }
    .main .stMarkdown h2 { font-size: 1.45rem !important; font-weight: 700 !important; margin-top: 0.25rem; }
    .main .stMarkdown h3 { font-size: 1.2rem !important; font-weight: 700 !important; color: var(--saas-text-primary) !important; }
    .main .stMarkdown h4, .main .stMarkdown h5 { font-weight: 700 !important; color: var(--saas-text-primary) !important; }
    .main .stMarkdown p, .main .stMarkdown li { color: var(--saas-text-secondary); line-height: 1.55; font-size: 0.95rem; }
    .main .stMarkdown strong { color: var(--saas-text-primary) !important; }

    [data-testid="stCaptionContainer"] {
      color: var(--saas-text-muted) !important;
      font-size: 0.9rem !important;
    }

    /* Hero: first title block */
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdown"] > h1:first-child) {
      background: linear-gradient(135deg, #1c1f26 0%, #252a35 100%);
      border-radius: 16px;
      padding: 1.65rem 1.85rem;
      margin-bottom: 1.5rem;
      border: 1px solid var(--saas-border);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
    }
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdown"] > h1:first-child) h1 {
      color: var(--saas-text-primary) !important;
      font-weight: 700 !important;
      letter-spacing: -0.02em;
    }

    /* Metrics */
    [data-testid="stMetric"] {
      background: var(--saas-bg-panel);
      border: 1px solid var(--saas-border);
      border-radius: 12px;
      padding: 0.85rem 1rem !important;
    }
    [data-testid="stMetricLabel"] { color: var(--saas-text-muted) !important; font-weight: 600 !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.04em; }
    [data-testid="stMetricValue"] { color: var(--saas-text-primary) !important; font-weight: 700 !important; }
    [data-testid="stMetricDelta"] { color: var(--saas-accent-green) !important; }

    /* Primary buttons */
    button[kind="primary"], [data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #4f8ef7 0%, #3b7ae8 100%) !important;
      border: 1px solid rgba(127, 168, 249, 0.55) !important;
      color: #fff !important;
      font-weight: 600 !important;
    }
    button[kind="primary"]:hover { filter: brightness(1.08); }

    /* Secondary buttons */
    button[kind="secondary"] {
      background: var(--saas-bg-panel) !important;
      color: var(--saas-text-primary) !important;
      border: 1px solid var(--saas-border) !important;
    }

    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stNumberInput input, [data-baseweb="select"] > div {
      background-color: var(--saas-bg-panel) !important;
      color: var(--saas-text-primary) !important;
      border-color: var(--saas-border) !important;
    }
    .stTextInput label, .stTextArea label, .stNumberInput label, .stSlider label, .stMultiSelect label, .stSelectbox label {
      color: var(--saas-text-secondary) !important;
      font-weight: 600 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
      gap: 8px;
      background-color: var(--saas-bg-panel) !important;
      padding: 10px 12px !important;
      border-radius: 12px;
      border: 1px solid var(--saas-border);
    }
    .stTabs [data-baseweb="tab"] {
      border-radius: 8px;
      color: var(--saas-text-secondary) !important;
      background-color: transparent !important;
      font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
      background-color: var(--saas-bg-panel-hover) !important;
      color: var(--saas-text-primary) !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
      background: linear-gradient(180deg, #4f8ef7 0%, #3b7ae8 100%) !important;
      color: #ffffff !important;
    }
    .stTabs [data-baseweb="tab-highlight"] { visibility: hidden; }
    .stTabs [data-baseweb="tab-panel"] {
      padding-top: 1.35rem;
      color: var(--saas-text-secondary) !important;
    }
    .stTabs button[role="tab"] { color: var(--saas-text-secondary) !important; }
    .stTabs button[role="tab"][aria-selected="true"] { color: #ffffff !important; }

    /* Progress */
    [data-testid="stProgress"] > div > div > div > div {
      background: linear-gradient(90deg, #4f8ef7, #7eb0ff) !important;
    }

    /* Dividers */
    hr { border-color: var(--saas-border) !important; margin: 1.35rem 0 !important; }

    /* Expanders */
    [data-testid="stExpander"] {
      background: var(--saas-bg-panel);
      border: 1px solid var(--saas-border);
      border-radius: 12px;
    }
    [data-testid="stExpander"] summary { color: var(--saas-text-primary) !important; font-weight: 600 !important; }

    /* Alerts */
    .stAlert { border-radius: 12px; border: 1px solid var(--saas-border); }

    /* Radio */
    .stRadio label { color: var(--saas-text-secondary) !important; }

    /* Custom cards (HTML) */
    .metric-card {
      background: var(--saas-bg-panel);
      border: 1px solid var(--saas-border);
      border-radius: 12px;
      padding: 1.1rem 1.3rem;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
    }
    .ats-card {
      background: var(--saas-bg-panel);
      border: 1px solid var(--saas-border);
      border-radius: 16px;
      padding: 1.35rem 1.5rem;
      margin-bottom: 1.15rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.28);
    }
    .ats-section-title {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--saas-text-muted);
      margin-bottom: 0.4rem;
    }
    .ats-candidate-name { color: var(--saas-text-primary); font-weight: 700; }
    .ats-score-final { font-weight: 800; letter-spacing: -0.02em; }
    .ats-score-final--high { color: var(--saas-accent-green) !important; text-shadow: 0 0 24px rgba(34, 197, 94, 0.25); }
    .ats-score-final--mid { color: #fbbf24 !important; }
    .ats-score-final--low { color: #ef4444 !important; }
    .ats-match-chip { color: #7eb0ff !important; font-weight: 700; }
    .ats-interest-chip { color: #b8b9e8 !important; font-weight: 700; }
    .ats-skill-pill {
      display: inline-block;
      background: var(--saas-accent-blue-soft);
      color: #c8d9ff;
      border: 1px solid rgba(79, 142, 247, 0.4);
      padding: 5px 12px;
      border-radius: 999px;
      margin: 4px 4px 0 0;
      font-size: 0.82rem;
      font-weight: 600;
    }

    /* JSON / code-ish blocks */
    [data-testid="stJson"] {
      background: var(--saas-bg-panel) !important;
      border: 1px solid var(--saas-border) !important;
      border-radius: 12px !important;
      color: var(--saas-text-secondary) !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] { border: 1px solid var(--saas-border); border-radius: 12px; }

    .insight-card {
      background: var(--saas-bg-panel);
      border: 1px solid var(--saas-border);
      border-left: 4px solid var(--saas-accent-blue);
      border-radius: 14px;
      padding: 1.15rem 1.35rem;
      margin: 0 0 1.25rem 0;
    }
    .insight-card h4 { color: var(--saas-text-primary) !important; margin: 0 0 0.5rem 0; font-size: 1.05rem; }
    .insight-card ul { color: var(--saas-text-secondary); margin: 0.35rem 0 0 1.1rem; padding: 0; line-height: 1.55; }
    .insight-card .sub { color: var(--saas-text-muted); font-size: 0.88rem; margin-top: 0.65rem; }

    </style>
    """,
    unsafe_allow_html=True,
)

PIPELINE_STAGES = ["Applied", "Screened", "Shortlisted", "Interviewed", "Selected"]


def clamp_score(value):
    return max(0, min(100, int(round(value))))


def extract_years(text):
    if not text:
        return 0
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else 0


def parse_json_response(raw_text):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def parse_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def safe_model_json(prompt, fallback):
    try:
        response = model.generate_content(prompt)
        return parse_json_response(response.text)
    except Exception:
        return fallback


def extract_text_from_pdf(file_bytes):
    if PdfReader is None:
        return None, "Install pypdf: pip install pypdf"
    try:
        reader = PdfReader(BytesIO(file_bytes))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip(), None
    except Exception as exc:
        return None, str(exc)


def parse_resume_text_to_candidate(resume_text, label):
    prompt = f"""
Extract a single candidate profile from this resume text as valid JSON only:
{{
  "name": "full name or Unknown",
  "title": "current or most recent job title",
  "skills": ["skill1", "skill2"],
  "experience_years": 0,
  "location": "city or Remote if stated",
  "summary": "2 sentences max",
  "education": "short string or empty"
}}

Resume text:
{resume_text[:12000]}
"""
    fallback = {
        "name": label,
        "title": "Unknown",
        "skills": [],
        "experience_years": 0,
        "location": "Not specified",
        "summary": resume_text[:400] if resume_text else "Could not parse resume.",
        "education": "",
    }
    data = safe_model_json(prompt, fallback)
    return {
        "name": str(data.get("name") or label).strip(),
        "title": str(data.get("title") or "Unknown").strip(),
        "skills": parse_list(data.get("skills")),
        "experience_years": extract_years(data.get("experience_years", 0)),
        "location": str(data.get("location") or "Not specified").strip(),
        "summary": str(data.get("summary") or "").strip(),
        "education": str(data.get("education") or "").strip(),
        "source": "resume_pdf",
    }


def parse_candidate_json(raw_text):
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return None, "Invalid JSON. Please check syntax."

    if not isinstance(parsed, list):
        return None, "JSON must be a list of candidate objects."

    normalized = []
    required_fields = {"name", "title", "skills", "experience_years", "location", "summary"}
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            return None, f"Candidate #{idx} is not a JSON object."
        missing = required_fields.difference(item.keys())
        if missing:
            return None, f"Candidate #{idx} missing required keys: {sorted(missing)}"
        normalized.append(
            {
                "name": str(item["name"]).strip(),
                "title": str(item["title"]).strip(),
                "skills": parse_list(item["skills"]),
                "experience_years": extract_years(item["experience_years"]),
                "location": str(item["location"]).strip(),
                "summary": str(item["summary"]).strip(),
                "source": "json",
            }
        )
    return normalized, None


def location_compatibility_score(jd_location, cand_location, jd_work_mode=None):
    jd_l = (jd_location or "").lower().strip()
    cand_l = (cand_location or "").lower().strip()
    jd_wm = (jd_work_mode or "").lower().strip()
    if not jd_l or jd_l == "not specified":
        score, note = 85, "JD location unspecified — neutral fit."
    elif "remote" in jd_l or "anywhere" in jd_l:
        score, note = 100, "JD allows remote — strong compatibility."
    elif "remote" in cand_l:
        score, note = 95, "Candidate is remote — typically compatible with distributed teams."
    elif jd_l in cand_l or cand_l in jd_l:
        score, note = 90, "Location wording aligns with JD."
    elif any(c in cand_l for c in ["india", "in "]):
        score, note = 70, "Same broad region possible — confirm relocation/hybrid policy."
    else:
        score, note = 55, "Location may need alignment — discuss with candidate."

    # Work mode vs location realism (skip if JD is explicitly remote-first)
    if jd_wm and "remote" not in jd_l and "anywhere" not in jd_l:
        if "on-site" in jd_wm or "onsite" in jd_wm or jd_wm == "on-site":
            if "remote" in cand_l and "hybrid" not in cand_l:
                score = max(32, score - 28)
                note = f"{note} JD is on-site; profile is remote-first — confirm willingness to be on-site."
        elif "hybrid" in jd_wm:
            if "remote" in cand_l and not any(
                x in cand_l
                for x in (
                    "hybrid",
                    "bengaluru",
                    "bangalore",
                    "mumbai",
                    "pune",
                    "chennai",
                    "hyderabad",
                    "delhi",
                    "gurgaon",
                    "noida",
                )
            ):
                score = max(40, score - 18)
                note = f"{note} JD is hybrid; validate in-office cadence vs candidate location."

    return clamp_score(score), note


def results_to_csv(rows):
    output = StringIO()
    output.write(
        "rank,name,title,location,match_score,interest_score,final_score,pipeline_stage,"
        "matched_must,missing_must,matched_nice,skill_overlap_pct,exp_fit_pct,loc_fit_pct\n"
    )
    for idx, row in enumerate(rows, start=1):
        exp = row["explainability"]
        matched_must = "|".join(exp["matched_must_have"])
        missing_must = "|".join(exp["missing_must_have"])
        matched_nice = "|".join(exp["matched_nice_to_have"])
        stage = row.get("pipeline_stage", "Shortlisted")
        output.write(
            f"{idx},{row['name']},{row['title']},{row['location']},{row['match_score']},"
            f"{row['interest_score']},{row['final_score']},{stage},"
            f"{matched_must},{missing_must},{matched_nice},"
            f"{exp.get('skill_overlap_pct', '')},{exp.get('experience_fit_pct', '')},{exp.get('location_fit_pct', '')}\n"
        )
    return output.getvalue().encode("utf-8")


def display_final_score(row, feedback_map):
    """Base final score on row; recruiter feedback applies a small nudge (demo learning loop)."""
    adj = feedback_map.get(row["name"], 0)
    return clamp_score(row["final_score"] + adj * 3)


def _latin1_pdf_text(value, max_len=80):
    """FPDF core fonts need Latin-1-safe strings for reliable PDF bytes."""
    text = str(value or "")[:max_len]
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _ensure_download_bytes(data):
    """Streamlit download_button requires bytes (or str); fpdf2 may return bytearray/memoryview."""
    if data is None:
        return None
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    if isinstance(data, str):
        return data.encode("utf-8")
    return bytes(data)


def build_shortlist_pdf(rows, jd_title, feedback_map):
    if FPDF is None:
        return None
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, _latin1_pdf_text("TalentScout AI - Shortlist Report", 120), ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, _latin1_pdf_text(f"Role context: {jd_title}", 120), ln=True)
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(40, 8, "Name", border=1)
        pdf.cell(25, 8, "Match", border=1)
        pdf.cell(25, 8, "Interest", border=1)
        pdf.cell(25, 8, "Final", border=1)
        pdf.cell(40, 8, "Stage", border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for row in rows[:30]:
            fs = display_final_score(row, feedback_map)
            pdf.cell(40, 7, _latin1_pdf_text(row.get("name"), 22), border=1)
            pdf.cell(25, 7, _latin1_pdf_text(row.get("match_score"), 8), border=1)
            pdf.cell(25, 7, _latin1_pdf_text(row.get("interest_score"), 8), border=1)
            pdf.cell(25, 7, _latin1_pdf_text(fs, 8), border=1)
            pdf.cell(40, 7, _latin1_pdf_text(row.get("pipeline_stage", ""), 18), border=1)
            pdf.ln()
        out = pdf.output(dest="S")
        raw = _ensure_download_bytes(out)
        return raw if raw and len(raw) > 0 else None
    except Exception:
        return None


def parse_jd(jd_text):
    prompt = f"""
Extract structured hiring requirements from the Job Description.
Return valid JSON only:
{{
  "role": "short role title",
  "must_have_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill3"],
  "min_experience_years": 0,
  "max_experience_years": 0,
  "location": "location or Remote",
  "work_mode": "Remote|Hybrid|On-site|Not specified",
  "seniority": "Intern/Junior/Mid/Senior/Lead",
  "summary": "1-2 lines"
}}

Job Description:
{jd_text}
"""
    fallback = {
        "role": "Unknown Role",
        "must_have_skills": [],
        "nice_to_have_skills": [],
        "min_experience_years": 0,
        "max_experience_years": 0,
        "location": "Not specified",
        "work_mode": "Not specified",
        "seniority": "Not specified",
        "summary": "Could not parse JD reliably.",
    }
    parsed = safe_model_json(prompt, fallback)
    parsed["must_have_skills"] = parse_list(parsed.get("must_have_skills"))
    parsed["nice_to_have_skills"] = parse_list(parsed.get("nice_to_have_skills"))
    parsed["min_experience_years"] = extract_years(parsed.get("min_experience_years", 0))
    mx = parsed.get("max_experience_years", 0)
    parsed["max_experience_years"] = extract_years(mx) if mx else 0
    return parsed


def suggest_jd_improvements(jd_text, jd_data):
    prompt = f"""
You are an expert recruiter. Analyze this job description and structured parse.
Return valid JSON only:
{{
  "overall_clarity_score": 0-100,
  "suggestions": [
    {{"type": "skills|experience|title|benefits|clarity", "message": "actionable improvement"}}
  ],
  "missing_or_vague_items": ["item1"],
  "recommended_must_have_additions": ["skill or phrase"]
}}

JD text (truncated):
{jd_text[:6000]}

Structured parse:
{json.dumps(jd_data, indent=2)[:4000]}
"""
    return safe_model_json(
        prompt,
        {
            "overall_clarity_score": 70,
            "suggestions": [{"type": "clarity", "message": "Add explicit years of experience and must-have tools."}],
            "missing_or_vague_items": ["Compensation range", "Team size"],
            "recommended_must_have_additions": [],
        },
    )


def discover_candidates(pool, jd_data, max_results):
    must_have = {skill.lower() for skill in jd_data.get("must_have_skills", [])}
    min_years = jd_data.get("min_experience_years", 0)
    shortlisted = []

    for candidate in pool:
        cand_skills = {skill.lower() for skill in candidate["skills"]}
        matched_must = len(must_have.intersection(cand_skills))
        must_ratio = matched_must / len(must_have) if must_have else 0.5
        exp_ok = candidate["experience_years"] >= min_years

        discovery_score = (must_ratio * 70) + (30 if exp_ok else 10)
        if discovery_score >= 40:
            shortlisted.append(candidate)

    shortlisted.sort(key=lambda c: c["experience_years"], reverse=True)
    return shortlisted[:max_results]


def jd_pool_skill_gaps(must_have_list, discovered_pool):
    """Must-have skills no one in the discovery pool lists on their profile."""
    gap = []
    for m in must_have_list or []:
        sk = str(m).lower()
        found = False
        for c in discovered_pool or []:
            for s in c.get("skills") or []:
                if sk in str(s).lower() or str(s).lower() in sk:
                    found = True
                    break
            if found:
                break
        if not found:
            gap.append(m)
    return gap


def render_jd_human_card(jd_data, discovered=None, *, show_pool_gap=False):
    """Human-readable JD parse (no JSON) for recruiters."""
    if not jd_data or not jd_data.get("role"):
        return
    must = jd_data.get("must_have_skills") or []
    nice = jd_data.get("nice_to_have_skills") or []
    miny = jd_data.get("min_experience_years", 0)
    maxy = jd_data.get("max_experience_years", 0) or 0
    exp_line = f"{miny}+ years" if maxy <= 0 else f"{miny}–{maxy} years"
    must_disp = ", ".join(must) if must else "—"
    nice_disp = ", ".join(nice) if nice else "—"
    gap_block = ""
    if show_pool_gap and discovered is not None:
        gap_must = jd_pool_skill_gaps(must, discovered)
        gap_block = f"""
  <p style="margin:12px 0 0 0;color:#fbbf24;font-size:0.92rem;">
    ⚠ <strong style="color:#FFFFFF;">Pool gap (no candidate lists this):</strong>
    {html.escape(", ".join(gap_must) if gap_must else "— none detected in this pool")}
  </p>"""
    st.markdown(
        f"""
<div class="ats-card" style="margin-bottom:1rem;">
  <div class="ats-section-title">Parsed job (human view)</div>
  <p style="margin:0 0 8px 0;color:#FFFFFF;font-size:1.2rem;font-weight:800;letter-spacing:-0.02em;">{html.escape(str(jd_data.get("role") or "—"))}</p>
  <p style="margin:0;color:#A0A3BD;font-size:0.95rem;line-height:1.6;">
    <strong style="color:#FFFFFF;">Experience:</strong> {html.escape(exp_line)}<br/>
    <strong style="color:#FFFFFF;">Location / mode:</strong> {html.escape(str(jd_data.get("location") or "—"))}
    · {html.escape(str(jd_data.get("work_mode") or "—"))}<br/>
    <strong style="color:#FFFFFF;">Must-have skills:</strong> {html.escape(must_disp)}<br/>
    <strong style="color:#FFFFFF;">Nice-to-have:</strong> {html.escape(nice_disp)}
  </p>{gap_block}
</div>
        """,
        unsafe_allow_html=True,
    )


def score_match_with_explainability(jd_data, candidate):
    must_have = {skill.lower() for skill in jd_data.get("must_have_skills", [])}
    nice_to_have = {skill.lower() for skill in jd_data.get("nice_to_have_skills", [])}
    cand_skills = {skill.lower() for skill in candidate["skills"]}

    matched_must = sorted(must_have.intersection(cand_skills))
    missing_must = sorted(must_have.difference(cand_skills))
    matched_nice = sorted(nice_to_have.intersection(cand_skills))

    must_ratio = len(matched_must) / len(must_have) if must_have else 0.6
    nice_ratio = len(matched_nice) / len(nice_to_have) if nice_to_have else 0.5
    min_y = jd_data.get("min_experience_years", 0) or 0
    max_y = jd_data.get("max_experience_years", 0) or 0
    cand_y = int(candidate.get("experience_years", 0) or 0)

    # Experience range fit: in-band = full credit; below min scales down; above max slight taper (realistic hiring bands)
    if min_y <= 0 and max_y <= 0:
        exp_ratio = 0.85
        exp_range_note = "JD did not specify years — neutral experience fit."
    elif max_y > 0 and cand_y >= min_y and cand_y <= max_y:
        exp_ratio = 1.0
        exp_range_note = f"Within JD band ({min_y}–{max_y} yrs): strong alignment."
    elif max_y > 0 and cand_y < min_y:
        exp_ratio = max(0.35, cand_y / max(1, min_y))
        exp_range_note = f"Below JD minimum ({min_y} yrs); still evaluated on skills and interest."
    elif max_y > 0 and cand_y > max_y:
        over = cand_y - max_y
        exp_ratio = max(0.72, 1.0 - 0.04 * over)
        exp_range_note = f"Above stated band ({max_y} yrs); may be strong but check level/seniority vs role budget."
    else:
        # Only min specified
        if cand_y >= min_y:
            exp_ratio = min(1.0, 0.75 + 0.25 * min(1.0, cand_y / max(min_y, 1)))
            exp_range_note = f"Meets/exceeds minimum ({min_y}+ yrs)."
        else:
            exp_ratio = max(0.35, cand_y / max(1, min_y))
            exp_range_note = f"Under minimum ({min_y} yrs); flagged for hiring manager judgment."

    skill_overlap_pct = clamp_score(must_ratio * 100)
    experience_fit_pct = clamp_score(exp_ratio * 100)
    loc_score, loc_note = location_compatibility_score(
        jd_data.get("location"), candidate.get("location"), jd_data.get("work_mode")
    )

    jd_role = (jd_data.get("role") or "").lower()
    cand_title = (candidate.get("title") or "").lower()
    domain_keywords = set(re.findall(r"[a-z]{3,}", jd_role + " " + cand_title))
    domain_overlap = len(domain_keywords) >= 1
    domain_note = (
        "Title and role show overlapping domain keywords."
        if domain_overlap
        else "Consider title vs role alignment for domain fit."
    )

    base_match = clamp_score((must_ratio * 50) + (nice_ratio * 20) + (exp_ratio * 15) + (loc_score / 100 * 15))

    # Explicit location / experience modifiers (penalty for mismatch, small bonus when both strong)
    loc_penalty_pts = max(0, min(12, int(round((60 - loc_score) * 0.22))))
    exp_penalty_pts = max(0, min(12, int(round((60 - experience_fit_pct) * 0.2))))
    alignment_bonus_pts = 0
    if loc_score >= 86 and experience_fit_pct >= 84:
        alignment_bonus_pts = 5
    elif loc_score >= 78 and experience_fit_pct >= 72:
        alignment_bonus_pts = 2
    base_match = clamp_score(base_match - loc_penalty_pts - exp_penalty_pts + alignment_bonus_pts)

    explain_prompt = f"""
You are evaluating candidate-job fit for recruiters (Explainable AI).
Return valid JSON only:
{{
  "match_score_adjustment": -10 to 10,
  "explanation": "2-4 short bullet sentences: skill overlap, experience vs JD, domain/title fit, location/work mode",
  "domain_relevance_note": "one sentence",
  "experience_alignment_note": "one sentence",
  "location_work_mode_note": "one sentence"
}}

JD summary: {jd_data.get("summary")}
JD role: {jd_data.get("role")} | work_mode: {jd_data.get("work_mode", "N/A")}
Candidate: {json.dumps(candidate)[:2000]}
Matched must-have: {matched_must}
Missing must-have: {missing_must}
Matched nice-to-have: {matched_nice}
Skill overlap % (must): {skill_overlap_pct}
Experience fit %: {experience_fit_pct}
Experience range context: {exp_range_note}
Location compatibility score: {loc_score}
ATS-style adjustments applied: location penalty {loc_penalty_pts}, experience penalty {exp_penalty_pts}, alignment bonus +{alignment_bonus_pts}
Base match score (after alignment): {base_match}
"""

    explain_json = safe_model_json(
        explain_prompt,
        {
            "match_score_adjustment": 0,
            "explanation": "Automated explainability: review skill overlap, experience, and location notes below.",
            "domain_relevance_note": domain_note,
            "experience_alignment_note": "Compare candidate years to JD minimum.",
            "location_work_mode_note": loc_note,
        },
    )
    adjustment = int(explain_json.get("match_score_adjustment", 0))
    final_match = clamp_score(base_match + adjustment)

    explainability = {
        "matched_must_have": matched_must,
        "missing_must_have": missing_must,
        "matched_nice_to_have": matched_nice,
        "base_match_score": base_match,
        "llm_adjustment": adjustment,
        "reason": explain_json.get("explanation", ""),
        "skill_overlap_pct": skill_overlap_pct,
        "nice_overlap_pct": clamp_score(nice_ratio * 100),
        "experience_fit_pct": experience_fit_pct,
        "location_fit_pct": loc_score,
        "location_note": loc_note,
        "domain_relevance_note": explain_json.get("domain_relevance_note", domain_note),
        "experience_alignment_note": explain_json.get("experience_alignment_note", exp_range_note),
        "location_work_mode_note": explain_json.get("location_work_mode_note", loc_note),
        "experience_range_note": exp_range_note,
        "jd_min_years": min_y,
        "jd_max_years": max_y,
        "candidate_years": cand_y,
        "loc_penalty_pts": loc_penalty_pts,
        "exp_penalty_pts": exp_penalty_pts,
        "alignment_bonus_pts": alignment_bonus_pts,
    }
    return final_match, explainability


def simulate_outreach_and_interest(jd_data, candidate):
    prompt = f"""
Simulate a realistic multi-turn recruiter–candidate conversation (8 messages total, alternating Recruiter then Candidate).
Capture enthusiasm, availability, compensation sensitivity if natural, and role fit.
Then return valid JSON only:
{{
  "interest_score": 0-100,
  "interest_reason": "short reason citing enthusiasm, availability, fit",
  "signals": {{
    "enthusiasm": "low|medium|high",
    "availability": "immediate|2-4 weeks|passive|unclear",
    "role_fit_self_assessment": "strong|moderate|weak"
  }},
  "conversation": [
    "Recruiter: ...",
    "Candidate: ...",
    ... exactly 8 strings ...
  ]
}}

Role: {jd_data.get("role")}
Location / mode: {jd_data.get("location")} ({jd_data.get("work_mode", "")})
Candidate profile: {json.dumps(candidate)[:2500]}
"""
    fallback_conv = [
        "Recruiter: Thanks for connecting — we have a role that maps well to your recent work. Are you open to a brief call this week?",
        "Candidate: Yes, I can do 30 minutes Thursday afternoon.",
        "Recruiter: Great. The team cares about ownership in production ML and clear communication with PMs.",
        "Candidate: That aligns with what I want next; I've owned models end-to-end before.",
        "Recruiter: Timeline-wise, are you actively interviewing or more exploratory?",
        "Candidate: I'm selective but serious for the right scope and team.",
        "Recruiter: Compensation band is competitive for the level; we can share specifics on the call.",
        "Candidate: Sounds good — send the JD highlights and I'll confirm Thursday.",
    ]
    fallback = {
        "interest_score": 58,
        "interest_reason": "Moderate interest: open to call, selective but engaged.",
        "signals": {"enthusiasm": "medium", "availability": "2-4 weeks", "role_fit_self_assessment": "moderate"},
        "conversation": fallback_conv,
    }
    payload = safe_model_json(prompt, fallback)
    conv = payload.get("conversation") or fallback["conversation"]
    if isinstance(conv, list) and len(conv) > 8:
        conv = conv[:8]
    elif isinstance(conv, list) and len(conv) < 8:
        conv = conv + fallback_conv[len(conv) :]

    payload["interest_score"] = clamp_score(payload.get("interest_score", 58))
    payload["conversation"] = conv if isinstance(conv, list) else fallback_conv
    payload["interest_reason"] = payload.get("interest_reason", fallback["interest_reason"])
    payload["signals"] = payload.get("signals", fallback["signals"])
    return payload


def build_ranking_summary(rows, feedback_map, jd_data):
    """Human-readable why #1 leads (no extra LLM call)."""
    if not rows:
        return ""
    leader = rows[0]
    fs = lambda r: display_final_score(r, feedback_map)
    lines = [
        f"**#{1} — {leader['name']}** leads with final score **{fs(leader)}** "
        f"(match {leader['match_score']}, interest {leader['interest_score']})."
    ]
    e = leader.get("explainability") or {}
    drivers = []
    if e.get("skill_overlap_pct", 0) >= 65:
        drivers.append("strong must-have skill overlap")
    if e.get("experience_fit_pct", 0) >= 75:
        drivers.append("solid experience fit vs the JD range")
    if e.get("location_fit_pct", 0) >= 80:
        drivers.append("high location / work-mode compatibility")
    if leader.get("interest_score", 0) >= 72:
        drivers.append("strong simulated interest from outreach")
    if drivers:
        lines.append("**Primary ranking drivers:** " + "; ".join(drivers) + ".")
    lines.append(
        f"**Weights in effect:** {jd_data.get('_match_w', 60)}% match · {jd_data.get('_interest_w', 40)}% interest "
        "(set in sidebar)."
    )
    if len(rows) > 1:
        s2 = rows[1]
        gap = fs(leader) - fs(s2)
        lines.append(
            f"**vs #2 ({s2['name']}, {fs(s2)}):** gap of **{gap}** points — "
            f"usually from a mix of match detail, interest signal, and recruiter feedback nudges."
        )
    return "\n\n".join(lines)


def _format_skill_phrase(skills):
    if not skills:
        return "—"
    return ", ".join(str(s).strip().title() for s in skills if str(s).strip())


def _traffic_color(score):
    """Green = strong, amber = medium, red = weak (recruiter scan)."""
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "#A0A3BD"
    if s >= 70:
        return "#22C55E"
    if s >= 45:
        return "#FBBF24"
    return "#EF4444"


def _top_skill_in_rows(rows):
    counts = {}
    for r in rows or []:
        for sk in r.get("skills") or []:
            counts[sk] = counts.get(sk, 0) + 1
    if not counts:
        return "—"
    return max(counts.items(), key=lambda x: x[1])[0]


def render_top_candidate_insight(rows, feedback_map, jd_data):
    """Decision-focused callout: top pick + why selected (recruiter narrative)."""
    if not rows:
        return
    top = max(rows, key=lambda r: display_final_score(r, feedback_map))
    fs = display_final_score(top, feedback_map)
    exp = top.get("explainability") or {}
    mm = exp.get("matched_must_have") or []
    skill_line = _format_skill_phrase(mm[:8]) if mm else "Skills evaluated vs JD must-haves"
    bullets = []
    if mm:
        bullets.append(f"Strong skill alignment ({skill_line})")
    elif exp.get("skill_overlap_pct", 0) >= 55:
        bullets.append("Solid skill overlap vs the JD profile")
    if exp.get("experience_fit_pct", 0) >= 68:
        bullets.append("Experience matches stated requirements")
    if exp.get("location_fit_pct", 0) >= 68:
        bullets.append("Location & work mode compatible with the JD")
    if top.get("interest_score", 0) >= 68:
        bullets.append("High interest score from simulated outreach")
    if exp.get("matched_nice_to_have"):
        bullets.append("Adds nice-to-have depth beyond core must-haves")
    if not bullets:
        bullets.append("Highest weighted composite score in the current filtered view")
    reason = html.escape(str(top.get("interest_reason", "") or "").strip())
    matched = _format_skill_phrase(mm)
    mc = _traffic_color(top.get("match_score", 0))
    ic = _traffic_color(top.get("interest_score", 0))
    bullets_html = "".join(f"<li>{html.escape(b)}</li>" for b in bullets[:6])
    st.markdown(
        f"""
<div class="insight-card">
  <h4>🏆 Top candidate: {html.escape(str(top.get("name", "")))}</h4>
  <p style="margin:0;color:#A0A3BD;font-size:0.95rem;">
    Composite <strong style="color:#4F8EF7;">{fs}</strong>
    · Match <strong style="color:{mc};">{top.get("match_score", "—")}</strong>
    · Interest <strong style="color:{ic};">{top.get("interest_score", "—")}</strong>
  </p>
  <p style="margin:12px 0 6px 0;color:#FFFFFF;font-size:0.82rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">Why selected?</p>
  <ul style="list-style:disc;">{bullets_html}</ul>
  <p class="sub">Must-haves covered: {matched}</p>
  {f'<p class="sub">Interest signal: {reason}</p>' if reason else ''}
</div>
        """,
        unsafe_allow_html=True,
    )


def passes_skill_refine(row, selected_skills):
    if not selected_skills:
        return True
    blob = " ".join(row.get("skills", [])).lower()
    for need in selected_skills:
        if need.lower() not in blob:
            return False
    return True


def _final_score_css_class(score):
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "ats-score-final--mid"
    if s >= 75:
        return "ats-score-final--high"
    if s >= 45:
        return "ats-score-final--mid"
    return "ats-score-final--low"


def render_profile_card(item, rank, final_display_score):
    """LinkedIn / ATS-style card: bold name, location & tenure, skills, traffic-light scores, JD gaps."""
    exp = item.get("explainability") or {}
    skills = item.get("skills", []) or []
    pills = "".join(
        f'<span class="ats-skill-pill">{html.escape(str(s))}</span>' for s in skills[:10]
    )
    if len(skills) > 10:
        pills += f'<span style="color:#6b6e8c;font-size:0.78rem;"> +{len(skills) - 10} more</span>'
    loc_line = html.escape(str(item.get("location", "")))
    title_line = html.escape(str(item.get("title", "")))
    name_line = html.escape(str(item.get("name", "")))
    sum_line = html.escape(str(item.get("candidate_summary", ""))[:200])
    yr = int(item.get("experience_years", 0) or 0)
    jmin = exp.get("jd_min_years", 0)
    jmax = exp.get("jd_max_years", 0)
    if jmin and jmax:
        jd_yr_txt = f"{jmin}–{jmax} yrs (JD)"
    elif jmin:
        jd_yr_txt = f"{jmin}+ yrs (JD)"
    else:
        jd_yr_txt = "JD band open"
    final_cls = _final_score_css_class(final_display_score)
    match_s = item.get("match_score", "—")
    interest_s = item.get("interest_score", "—")
    match_c = _traffic_color(match_s)
    interest_c = _traffic_color(interest_s)
    matched_must = exp.get("matched_must_have") or []
    missing_must = exp.get("missing_must_have") or []
    matched_txt = _format_skill_phrase(matched_must) if matched_must else "— (no JD must-haves or none matched)"
    missing_txt = _format_skill_phrase(missing_must[:10]) if missing_must else "—"
    if missing_must and len(missing_must) > 10:
        missing_txt += f" (+{len(missing_must) - 10} more)"
    loc_fit = exp.get("location_fit_pct", "—")
    exp_fit = exp.get("experience_fit_pct", "—")
    card = f"""
<div class="ats-card">
  <div class="ats-section-title">Rank #{rank} · {html.escape(jd_yr_txt)}</div>
  <div class="ats-candidate-name" style="font-size:1.45rem;font-weight:800;letter-spacing:-0.02em;line-height:1.2;margin-bottom:6px;">{name_line}</div>
  <div style="color:#A0A3BD;font-size:0.92rem;font-weight:600;margin-bottom:8px;">{title_line}</div>
  <div style="color:#A0A3BD;font-size:0.95rem;margin-bottom:12px;line-height:1.5;">
    <strong style="color:#FFFFFF;">Experience:</strong> {yr} yrs
    &nbsp;·&nbsp; <strong style="color:#FFFFFF;">Location:</strong> {loc_line}<br/>
    <span style="font-size:0.85rem;">Loc alignment <strong style="color:#4F8EF7;">{loc_fit}</strong>% · Exp alignment <strong style="color:#4F8EF7;">{exp_fit}</strong>%</span>
  </div>
  <div class="ats-section-title" style="margin-top:4px;">Profile skills</div>
  <div style="margin-bottom:14px;">{pills or '<span style="color:#6b6e8c;">No skills listed</span>'}</div>
  <div style="display:flex;flex-wrap:wrap;gap:16px 28px;margin-bottom:14px;padding:12px 0;border-top:1px solid rgba(255,255,255,0.07);border-bottom:1px solid rgba(255,255,255,0.07);">
    <div><span style="color:#A0A3BD;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Match score</span><br/>
      <span style="font-size:1.5rem;font-weight:800;color:{match_c};">{match_s}</span></div>
    <div><span style="color:#A0A3BD;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Interest score</span><br/>
      <span style="font-size:1.5rem;font-weight:800;color:{interest_c};">{interest_s}</span></div>
    <div><span style="color:#A0A3BD;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Final</span><br/>
      <span class="ats-score-final {final_cls}" style="font-size:1.5rem;">{final_display_score}</span></div>
  </div>
  <div style="font-size:0.92rem;color:#FFFFFF;line-height:1.55;margin-bottom:6px;">
    <span style="color:#22C55E;">✔</span> <strong>Matched (JD must-have):</strong>
    <span style="color:#A0A3BD;">{matched_txt}</span>
  </div>
  <div style="font-size:0.92rem;color:#FFFFFF;line-height:1.55;margin-bottom:8px;">
    <span style="color:#EF4444;">✕</span> <strong>Missing (must-have):</strong>
    <span style="color:#A0A3BD;">{missing_txt}</span>
  </div>
  <div style="font-size:0.86rem;color:#6b6e8c;line-height:1.5;">{sum_line}</div>
</div>
"""
    st.markdown(card, unsafe_allow_html=True)


# -----------------------------
# API KEY + MODEL
# -----------------------------
project_root = Path(__file__).resolve().parent
load_dotenv(dotenv_path=project_root / ".env")

try:
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
except Exception:
    api_key = ""

if not api_key:
    api_key = os.getenv("GOOGLE_API_KEY", "")

api_key = str(api_key).strip().strip('"').strip("'")

if not api_key:
    st.error("❌ API Key not found. Add GOOGLE_API_KEY to Streamlit secrets or local .env")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Session defaults
for key, default in [
    ("last_results", []),
    ("last_jd_data", {}),
    ("last_discovered", []),
    ("last_jd_text", ""),
    ("recruiter_feedback", {}),
    ("jd_suggestions", None),
    ("pipeline_stage_by_name", {}),
    ("saved_shortlist", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# -----------------------------
# Header
# -----------------------------
st.markdown("# TalentScout AI")
st.caption(
    "Production-grade talent intelligence — explainable matching, resume ingestion, "
    "ATS pipeline, analytics, and JD coaching in one workspace."
)

st.sidebar.header("Controls")
num_candidates = st.sidebar.slider("Shortlist size", 1, 12, 6)
match_weight_pct = st.sidebar.slider("Match weight %", 0, 100, 60, 5)
interest_weight_pct = 100 - match_weight_pct
st.sidebar.caption(f"Interest weight: {interest_weight_pct}%")
min_final_threshold = st.sidebar.slider("Min final score", 0, 100, 0, 5)
st.sidebar.divider()
st.sidebar.subheader("ATS filters")
min_exp_filter = st.sidebar.number_input("Minimum experience (years)", 0, 30, 0)
max_exp_filter = st.sidebar.number_input("Maximum experience (years)", 0, 30, 30)
filter_skill = st.sidebar.text_input("Required skill (contains)", placeholder="e.g. Python")
filter_title = st.sidebar.text_input("Title contains", placeholder="engineer")
filter_loc = st.sidebar.text_input("Location (contains)", placeholder="city / remote")
remote_only = st.sidebar.toggle("Remote location only", value=False)
strict_must_haves = st.sidebar.toggle("Require all JD must-have skills", value=False)
st.sidebar.divider()
if st.sidebar.button("Clear feedback & pipeline memory"):
    st.session_state["recruiter_feedback"] = {}
    st.session_state["pipeline_stage_by_name"] = {}
    st.sidebar.success("Reset.")
st.sidebar.divider()
st.sidebar.subheader("Saved shortlist")
if st.session_state.get("saved_shortlist"):
    for s in st.session_state["saved_shortlist"][:8]:
        st.sidebar.caption(f"{s.get('name', '')} · {s.get('final', '')}")
    if st.sidebar.button("Clear saved"):
        st.session_state["saved_shortlist"] = []
        st.rerun()
else:
    st.sidebar.caption("Save from Shortlist tab after a run.")

col_main, col_side = st.columns([2.2, 1], gap="large")
with col_main:
    jd = st.text_area("Job description", height=240, placeholder="Paste full JD...", key="jd_input")
with col_side:
    st.markdown("##### Candidate source")
    source_option = st.radio(
        "Source",
        ["Built-in pool", "JSON paste", "PDF resume(s)"],
        label_visibility="collapsed",
    )

default_candidate_pool = [
    {
        "name": "Rahul N",
        "title": "ML Engineer",
        "skills": ["Python", "ML", "NLP", "Docker", "SQL"],
        "experience_years": 2,
        "location": "Bengaluru",
        "summary": "Built NLP APIs for customer support automation.",
        "source": "builtin",
    },
    {
        "name": "Anjali S",
        "title": "Backend Engineer",
        "skills": ["Java", "Spring", "Microservices", "AWS", "SQL"],
        "experience_years": 4,
        "location": "Hyderabad",
        "summary": "Owns backend services and performance tuning.",
        "source": "builtin",
    },
    {
        "name": "Kiran P",
        "title": "Data Scientist",
        "skills": ["Python", "Data Science", "SQL", "Pandas", "XGBoost"],
        "experience_years": 2,
        "location": "Remote",
        "summary": "Delivers forecasting and churn prediction models.",
        "source": "builtin",
    },
    {
        "name": "Sneha R",
        "title": "Frontend Engineer",
        "skills": ["React", "TypeScript", "JavaScript", "UI", "REST"],
        "experience_years": 3,
        "location": "Chennai",
        "summary": "Builds web apps with strong UX focus.",
        "source": "builtin",
    },
    {
        "name": "Arjun V",
        "title": "AI Engineer",
        "skills": ["Python", "Deep Learning", "Computer Vision", "PyTorch", "MLOps"],
        "experience_years": 5,
        "location": "Pune",
        "summary": "Productionized CV pipelines and model monitoring.",
        "source": "builtin",
    },
    {
        "name": "Meera T",
        "title": "Full Stack Engineer",
        "skills": ["Python", "React", "FastAPI", "PostgreSQL", "GCP"],
        "experience_years": 3,
        "location": "Remote",
        "summary": "Ships end-to-end features from API to UI.",
        "source": "builtin",
    },
    {
        "name": "Dev K",
        "title": "Data Engineer",
        "skills": ["Python", "Spark", "Airflow", "ETL", "AWS"],
        "experience_years": 4,
        "location": "Mumbai",
        "summary": "Designed scalable data pipelines for analytics.",
        "source": "builtin",
    },
    {
        "name": "Nisha A",
        "title": "Product Analyst",
        "skills": ["SQL", "Tableau", "A/B Testing", "Python", "Statistics"],
        "experience_years": 2,
        "location": "Bengaluru",
        "summary": "Supports product decisions with experimentation insights.",
        "source": "builtin",
    },
]

candidate_pool = list(default_candidate_pool)

if source_option == "JSON paste":
    raw_json = st.text_area(
        "Candidates JSON",
        height=140,
        placeholder='[{"name":"...","title":"...","skills":["Python"],"experience_years":3,"location":"Remote","summary":"..."}]',
    )
    if raw_json.strip():
        parsed, err = parse_candidate_json(raw_json)
        if err:
            st.error(err)
            st.stop()
        candidate_pool = parsed

elif source_option == "PDF resume(s)":
    uploads = st.file_uploader("Upload one or more PDF resumes", type=["pdf"], accept_multiple_files=True)
    if uploads:
        merged = []
        for uf in uploads:
            text, err = extract_text_from_pdf(uf.getvalue())
            if err or not text:
                st.warning(f"{uf.name}: {err or 'No text extracted'}")
                continue
            cand = parse_resume_text_to_candidate(text, uf.name.replace(".pdf", ""))
            merged.append(cand)
        if merged:
            candidate_pool = merged
        else:
            st.error("No usable resume text. Try another PDF or built-in pool.")
            st.stop()

run = st.button("Run agent", type="primary", use_container_width=True)

if run:
    if not jd.strip():
        st.warning("Paste a job description first.")
        st.stop()

    progress = st.progress(0, text="Parsing JD...")
    jd_data = parse_jd(jd)
    st.session_state["last_jd_text"] = jd
    st.session_state["last_jd_data"] = jd_data
    progress.progress(15, text="JD coaching...")
    st.session_state["jd_suggestions"] = suggest_jd_improvements(jd, jd_data)
    jd_data["_match_w"] = match_weight_pct
    jd_data["_interest_w"] = interest_weight_pct

    progress.progress(25, text="Discovering candidates...")
    discovered = discover_candidates(candidate_pool, jd_data, max_results=num_candidates)
    if not discovered:
        st.error("No candidates passed discovery. Loosen JD must-haves or add resumes.")
        st.stop()

    progress.progress(40, text="Scoring & simulations...")
    results = []

    for idx, candidate in enumerate(discovered):
        match_score, explainability = score_match_with_explainability(jd_data, candidate)
        interest_payload = simulate_outreach_and_interest(jd_data, candidate)
        interest_score = interest_payload["interest_score"]
        base_final = clamp_score(
            (match_score * (match_weight_pct / 100.0)) + (interest_score * (interest_weight_pct / 100.0))
        )
        row = {
            "name": candidate["name"],
            "title": candidate["title"],
            "location": candidate["location"],
            "experience_years": candidate.get("experience_years", 0),
            "match_score": match_score,
            "interest_score": interest_score,
            "final_score": base_final,
            "explainability": explainability,
            "interest_reason": interest_payload["interest_reason"],
            "conversation": interest_payload["conversation"],
            "signals": interest_payload.get("signals", {}),
            "candidate_summary": candidate["summary"],
            "pipeline_stage": st.session_state["pipeline_stage_by_name"].get(candidate["name"], "Shortlisted"),
        }
        results.append(row)
        progress.progress(40 + int((idx + 1) / len(discovered) * 55), text=f"Candidate {idx + 1}/{len(discovered)}")

    results.sort(key=lambda r: r["final_score"], reverse=True)
    filtered = [r for r in results if r["final_score"] >= min_final_threshold] or results
    st.session_state["last_results"] = filtered
    st.session_state["last_discovered"] = discovered
    progress.progress(100, text="Done")
    st.success("Shortlist updated.")

# Post-run: apply client-side filters to display copy
results = list(st.session_state.get("last_results", []))
jd_data = st.session_state.get("last_jd_data", {})
discovered = st.session_state.get("last_discovered", [])


def passes_filters(row):
    if strict_must_haves:
        exp = row.get("explainability") or {}
        if exp.get("missing_must_have"):
            return False
    if filter_skill:
        blob = (row["title"] + row["candidate_summary"]).lower()
        for c in discovered:
            if c["name"] == row["name"]:
                blob += " " + " ".join(c.get("skills", [])).lower()
        exp = row.get("explainability") or {}
        blob += " " + " ".join(exp.get("matched_must_have", [])).lower()
        if filter_skill.lower() not in blob:
            return False
    if filter_title and filter_title.lower() not in row["title"].lower():
        return False
    if filter_loc and filter_loc.lower() not in row["location"].lower():
        return False
    ey = row.get("experience_years", 0)
    for c in discovered:
        if c["name"] == row["name"]:
            ey = c.get("experience_years", ey)
    if ey < min_exp_filter or ey > max_exp_filter:
        return False
    if remote_only and "remote" not in row["location"].lower():
        return False
    return True


# enrich rows with experience_years from discovered for filters
name_to_cand = {c["name"]: c for c in discovered}
for r in results:
    if r["name"] in name_to_cand:
        r["experience_years"] = name_to_cand[r["name"]].get("experience_years", r.get("experience_years", 0))
        r["skills"] = name_to_cand[r["name"]].get("skills", [])

filtered_display = [r for r in results if passes_filters(r)]

if results:
    feedback = st.session_state["recruiter_feedback"]

    def display_score(row):
        return display_final_score(row, feedback)

    if not filtered_display:
        st.warning("No candidates match your sidebar filters. Clear filters or widen experience range.")

    avg_m = avg_i = 0.0
    top = None
    top_skill = "—"
    if filtered_display:
        avg_m = sum(r["match_score"] for r in filtered_display) / len(filtered_display)
        avg_i = sum(r["interest_score"] for r in filtered_display) / len(filtered_display)
        top = max(filtered_display, key=lambda x: display_score(x))
        top_skill = _top_skill_in_rows(filtered_display)

    st.markdown("### Dashboard summary")
    st.caption("Snapshot of this run · sidebar filters shape “In view” and averages below.")
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Total analyzed", len(results))
    d2.metric("In view", len(filtered_display))
    d3.metric("Avg match", round(avg_m, 1) if filtered_display else "—")
    d4.metric("Avg interest", round(avg_i, 1) if filtered_display else "—")
    d5.metric("Top skill (view)", str(top_skill)[:24] + ("…" if len(str(top_skill)) > 24 else ""))

    if filtered_display:
        render_top_candidate_insight(filtered_display, feedback, jd_data)

    dl1, dl2 = st.columns(2)
    with dl1:
        if filtered_display:
            csv_bytes = _ensure_download_bytes(results_to_csv(filtered_display))
            st.download_button(
                "Download Shortlist",
                data=csv_bytes,
                file_name="talentscout_shortlist.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.caption("CSV export appears when at least one candidate matches filters.")
    with dl2:
        pdf_bytes = None
        if filtered_display and FPDF is not None:
            pdf_bytes = build_shortlist_pdf(filtered_display, jd_data.get("role", "Role"), feedback)
            pdf_bytes = _ensure_download_bytes(pdf_bytes)
        if pdf_bytes and isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 0:
            st.download_button(
                "Download PDF report",
                data=pdf_bytes,
                file_name="talentscout_shortlist.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        elif FPDF is None:
            st.caption("PDF: add **fpdf2** to requirements and redeploy.")
        else:
            st.caption("PDF: could not build file (try ASCII-safe names or re-run).")

    st.divider()
    st.markdown("### Command center")
    st.caption("Decision context · ranking rationale · JD alignment")
    jd_ctx = st.columns(4)
    jd_ctx[0].metric("JD role", (jd_data.get("role") or "—")[:28])
    jd_ctx[1].metric("Min experience (JD)", jd_data.get("min_experience_years", "—"))
    _mx = jd_data.get("max_experience_years", 0) or 0
    jd_ctx[2].metric("Max experience (JD)", str(_mx) if _mx else "open")
    jd_ctx[3].metric("Work mode", (jd_data.get("work_mode") or "—")[:20])
    st.markdown("#### Why this order?")
    rank_md = build_ranking_summary(filtered_display, feedback, jd_data)
    if rank_md:
        st.markdown(rank_md)
    else:
        st.caption("Run the agent and ensure at least one candidate is in view to see ranking rationale.")

    tabs = st.tabs(
        [
            "Shortlist",
            "Explainability & fit",
            "ATS pipeline",
            "Analytics",
            "JD coach",
            "Discovery",
        ]
    )

    with tabs[0]:
        st.markdown("##### Shortlist · refine & decide")
        st.caption("Sidebar ATS filters apply first. Use chips below to require skills on the profile.")
        rows_view = []
        if not filtered_display:
            st.warning("No candidates match your sidebar filters — widen experience or clear text filters.")
        else:
            skill_opts = sorted({s for r in filtered_display for s in (r.get("skills") or [])})
            pick_skills = st.multiselect(
                "Candidate must include these skills",
                options=skill_opts,
                key="refine_skills_tab",
            )
            rows_view = [r for r in filtered_display if passes_skill_refine(r, pick_skills)]
            if not rows_view:
                st.info("No candidate has all selected skills. Clear chips or pick fewer skills.")
            else:
                st.markdown("###### Candidate roster")
                st.caption("Up to three profiles per row — open **feedback** for recruiter actions.")
                sv, _ = st.columns([1, 2])
                with sv:
                    if st.button("Save this view to sidebar", key="save_shortlist_view"):
                        st.session_state["saved_shortlist"] = [
                            {
                                "name": r["name"],
                                "title": r["title"],
                                "final": display_score(r),
                            }
                            for r in rows_view
                        ]
                        st.success("Saved — see **Saved shortlist** in the sidebar.")
                for row_start in range(0, len(rows_view), 3):
                    chunk = rows_view[row_start : row_start + 3]
                    pad = 3 - len(chunk)
                    chunk = chunk + [None] * pad
                    col_slots = st.columns(3)
                    for col_idx in range(3):
                        item = chunk[col_idx]
                        with col_slots[col_idx]:
                            if item is None:
                                st.empty()
                                continue
                            rank = row_start + col_idx + 1
                            fs = display_score(item)
                            render_profile_card(item, rank, fs)
                            st.progress(min(1.0, fs / 100.0))
                            exp_lbl = re.sub(r"[^\w\- ]", "", item["name"])[:40]
                            with st.expander(f"#{rank} · {exp_lbl} — feedback"):
                                b1, b2, b3 = st.columns(3)
                                if b1.button("Approve", key=f"app_{rank}_{item['name']}"):
                                    st.session_state["recruiter_feedback"][item["name"]] = 1
                                    st.rerun()
                                if b2.button("Reject", key=f"rej_{rank}_{item['name']}"):
                                    st.session_state["recruiter_feedback"][item["name"]] = -1
                                    st.rerun()
                                if b3.button("Clear", key=f"clr_{rank}_{item['name']}"):
                                    st.session_state["recruiter_feedback"].pop(item["name"], None)
                                    st.rerun()
                                vote = feedback.get(item["name"])
                                if vote == 1:
                                    st.success("+3 display nudge this session.")
                                elif vote == -1:
                                    st.warning("−3 display nudge this session.")
                    st.divider()

    with tabs[1]:
        for item in filtered_display:
            exp = item["explainability"]
            st.markdown(f"### {item['name']}")
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Must-have overlap %", exp.get("skill_overlap_pct", 0))
            g2.metric("Nice-to-have %", exp.get("nice_overlap_pct", 0))
            g3.metric("Experience fit %", exp.get("experience_fit_pct", 0))
            g4.metric("Location fit %", exp.get("location_fit_pct", 0))
            st.bar_chart(
                pd.DataFrame(
                    {
                        "Metric": ["Must skills", "Nice skills", "Experience", "Location"],
                        "Score": [
                                    exp.get("skill_overlap_pct", 0),
                                    exp.get("nice_overlap_pct", 0),
                                    exp.get("experience_fit_pct", 0),
                                    exp.get("location_fit_pct", 0),
                                ],
                    }
                ).set_index("Metric")
            )
            lp, ep, ab = exp.get("loc_penalty_pts", 0), exp.get("exp_penalty_pts", 0), exp.get("alignment_bonus_pts", 0)
            if lp or ep or ab:
                st.caption(
                    f"Location / experience shaping in match score: −{lp} pts location gap, "
                    f"−{ep} pts experience gap, +{ab} pts strong-alignment bonus."
                )
            st.write("**Narrative:**", exp.get("reason", ""))
            st.write("**Domain:**", exp.get("domain_relevance_note", ""))
            st.write("**Experience (range vs JD):**", exp.get("experience_range_note", ""))
            st.write("**Experience (detail):**", exp.get("experience_alignment_note", ""))
            st.write("**Location / mode:**", exp.get("location_work_mode_note", ""))
            st.write("**Matched must-have:**", ", ".join(exp["matched_must_have"]) or "—")
            st.write("**Missing must-have:**", ", ".join(exp["missing_must_have"]) or "—")
            with st.expander("Outreach transcript"):
                for line in item["conversation"]:
                    st.write(line)
                st.markdown("**Signals (simulated)**")
                sig = item.get("signals") or {}
                if isinstance(sig, dict):
                    for k, v in sig.items():
                        st.markdown(f"- **{html.escape(str(k))}:** {html.escape(str(v))}")
                else:
                    st.write(sig)
            st.divider()

    with tabs[2]:
        st.markdown("Move candidates through your pipeline (ATS-style).")
        for item in filtered_display:
            current = st.session_state["pipeline_stage_by_name"].get(item["name"], "Shortlisted")
            if current not in PIPELINE_STAGES:
                current = "Shortlisted"
            new_stage = st.selectbox(
                f"{item['name']}",
                PIPELINE_STAGES,
                index=PIPELINE_STAGES.index(current),
                key=f"pipe_{item['name']}",
            )
            st.session_state["pipeline_stage_by_name"][item["name"]] = new_stage
            item["pipeline_stage"] = new_stage

        st.subheader("Pipeline summary")
        counts = {s: 0 for s in PIPELINE_STAGES}
        for item in filtered_display:
            stg = st.session_state["pipeline_stage_by_name"].get(item["name"], "Shortlisted")
            counts[stg] = counts.get(stg, 0) + 1
        st.bar_chart(pd.DataFrame({"Stage": list(counts.keys()), "Count": list(counts.values())}).set_index("Stage"))

    with tabs[3]:
        st.subheader("Recruitment analytics")
        if not filtered_display:
            st.info("No rows after filters.")
        else:
            skill_counter = {}
            for item in filtered_display:
                for sk in item.get("skills", []):
                    skill_counter[sk] = skill_counter.get(sk, 0) + 1
            if skill_counter:
                top_skills = dict(sorted(skill_counter.items(), key=lambda x: -x[1])[:12])
                st.markdown("**Top skills in current view**")
                st.bar_chart(pd.DataFrame({"skill": list(top_skills.keys()), "count": list(top_skills.values())}).set_index("skill"))
            exp_buckets = {"0-2": 0, "3-5": 0, "6+": 0}
            for item in filtered_display:
                y = item.get("experience_years", 0)
                if y <= 2:
                    exp_buckets["0-2"] += 1
                elif y <= 5:
                    exp_buckets["3-5"] += 1
                else:
                    exp_buckets["6+"] += 1
            st.markdown("**Experience distribution**")
            st.bar_chart(pd.DataFrame({"bucket": list(exp_buckets.keys()), "n": list(exp_buckets.values())}).set_index("bucket"))
            loc_counter = {}
            for item in filtered_display:
                loc_counter[item["location"]] = loc_counter.get(item["location"], 0) + 1
            st.markdown("**Geography**")
            st.bar_chart(pd.DataFrame({"loc": list(loc_counter.keys()), "n": list(loc_counter.values())}).set_index("loc"))

    with tabs[4]:
        sug = st.session_state.get("jd_suggestions")
        if not sug:
            st.info("Run the agent once to generate JD coaching, or paste JD and click Run.")
        else:
            if jd_data.get("role"):
                render_jd_human_card(jd_data, discovered=None, show_pool_gap=False)
            st.markdown("#### Coaching & gaps")
            st.metric("JD clarity score (model)", sug.get("overall_clarity_score", "—"))
            for s in sug.get("suggestions", [])[:12]:
                st.markdown(f"- **{s.get('type', 'tip')}**: {s.get('message', '')}")
            st.markdown("**Missing / vague**")
            for m in sug.get("missing_or_vague_items", []):
                st.write(f"- {m}")
            st.markdown("**Suggested must-have additions**")
            for m in sug.get("recommended_must_have_additions", []):
                st.write(f"- {m}")

    with tabs[5]:
        st.subheader("JD analysis & discovery pool")
        if not jd_data or not jd_data.get("role"):
            st.info("Run the agent to parse the JD and load the discovery pool.")
        else:
            render_jd_human_card(jd_data, discovered, show_pool_gap=True)
            st.markdown(f"**Summary:** {jd_data.get('summary', '')}")
            st.markdown(f"**Discovered candidates ({len(discovered)}):**")
            if not discovered:
                st.caption("No rows in the discovery pool for this run.")
            else:
                for c in discovered:
                    sk = ", ".join((c.get("skills") or [])[:8])
                    st.markdown(
                        f"- **{c.get('name', '')}** — _{c.get('title', '')}_ · "
                        f"{c.get('location', '')} · **{c.get('experience_years', 0)}** yrs · _{sk}_"
                    )
            with st.expander("Raw pool JSON (debug)"):
                st.json(discovered)

else:
    st.markdown(
        """
<div class="ats-card" style="max-width:720px;">
  <div class="ats-section-title">Getting started</div>
  <p style="color:#A0A3BD;margin:0 0 12px 0;line-height:1.6;font-size:0.98rem;">
    <strong style="color:#FFFFFF;">1.</strong> Paste a JD and choose a candidate source.<br/>
    <strong style="color:#FFFFFF;">2.</strong> Click <strong style="color:#4F8EF7;">Run agent</strong>.<br/>
    <strong style="color:#FFFFFF;">3.</strong> Use <strong style="color:#FFFFFF;">Shortlist</strong>,
    <strong style="color:#FFFFFF;">Explainability</strong>, <strong style="color:#FFFFFF;">ATS pipeline</strong>,
    <strong style="color:#FFFFFF;">Analytics</strong>, and <strong style="color:#FFFFFF;">JD coach</strong> tabs.
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )
