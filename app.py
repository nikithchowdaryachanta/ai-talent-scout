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
      --saas-bg-deep: #0a0c10;
      --saas-bg-main: #0a0c10;
      --saas-bg-panel: #141821;
      --saas-bg-panel-hover: #1c2230;
      --saas-border: rgba(255, 255, 255, 0.12);
      --saas-text-primary: #f4f6ff;
      --saas-text-secondary: #c4c8e0;
      --saas-text-muted: #8b90ae;
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
      background: linear-gradient(145deg, #151a24 0%, #12161f 100%);
      border: 1px solid rgba(79, 142, 247, 0.35);
      border-left: 5px solid var(--saas-accent-blue);
      border-radius: 16px;
      padding: 1.25rem 1.45rem;
      margin: 0 0 1.35rem 0;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.45);
    }
    .insight-card h4 { color: var(--saas-text-primary) !important; margin: 0 0 0.5rem 0; font-size: 1.12rem; letter-spacing: -0.02em; }
    .insight-card ul { color: var(--saas-text-secondary); margin: 0.35rem 0 0 1.1rem; padding: 0; line-height: 1.55; }
    .insight-card .sub { color: var(--saas-text-muted); font-size: 0.88rem; margin-top: 0.65rem; }
    .reco-kpi {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--saas-border);
      border-radius: 10px;
      padding: 6px 12px;
      margin: 4px 8px 0 0;
      font-size: 0.88rem;
    }
    .reco-kpi strong { color: var(--saas-text-primary) !important; font-weight: 700; }
    .jd-coach-card {
      background: var(--saas-bg-panel);
      border: 1px solid var(--saas-border);
      border-radius: 14px;
      padding: 1.1rem 1.25rem;
      margin-bottom: 0.85rem;
    }
    .jd-coach-card h5 { color: var(--saas-text-primary) !important; margin: 0 0 0.35rem 0; font-size: 0.95rem; }
    .exp-mini-card {
      background: rgba(0,0,0,0.2);
      border: 1px solid var(--saas-border);
      border-radius: 12px;
      padding: 0.75rem 1rem;
      margin-bottom: 0.65rem;
    }

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


def _clean_jd_field_value(s, max_len=240):
    """Trim, collapse whitespace for display fields."""
    if s is None:
        return ""
    t = str(s).strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^[•\-\*\.\"'\s]+|[•\-\*\.\"'\s]+$", "", t)
    if max_len and len(t) > max_len:
        t = t[: max_len - 1].rstrip() + "…"
    return t


def _normalize_work_mode_display(s):
    """Map common phrases to stable UI labels."""
    if not s or not str(s).strip():
        return "Not specified"
    low = str(s).lower()
    if re.search(r"\bhybrid\b", low):
        return "Hybrid"
    if re.search(r"\bon[- ]?site\b|\bonsite\b|\bin[- ]?office\b", low):
        return "On-site"
    if re.search(r"\bremote\b", low):
        return "Remote"
    t = _clean_jd_field_value(s, 80)
    return t if t else "Not specified"


def _parse_experience_value_to_min_max(val):
    """
    Parse a single experience field value into (min_years, max_years_or_None).
    max None means 'do not override LLM max'; 0 means open-ended upper (matches app semantics).
    """
    if not val or not str(val).strip():
        return None, None
    v = str(val).strip()
    m_range = re.search(r"(\d+)\s*(?:[-–]|\s+to\s+)\s*(\d+)", v, re.IGNORECASE)
    if m_range:
        return int(m_range.group(1)), int(m_range.group(2))
    m_plus = re.search(r"(\d+)\s*\+", v)
    if m_plus:
        return int(m_plus.group(1)), 0
    y = extract_years(v)
    if y:
        return y, None
    return None, None


def extract_jd_labeled_fields_regex(jd_text):
    """
    Deterministic extraction from common labeled JD lines (Role:, Experience:, etc.).
    Only keys that are clearly present in the text are returned — caller merges over LLM output.
    """
    out = {}
    if not jd_text or not str(jd_text).strip():
        return out

    role_keys = frozenset(
        {
            "role",
            "job title",
            "position",
            "title",
            "job role",
            "position title",
            "opening",
        }
    )
    loc_keys = frozenset(
        {
            "location",
            "job location",
            "work location",
            "office location",
            "site location",
            "reporting location",
            "base",
            "office",
            "worksite",
            "work site",
            "based in",
            "city",
            "region",
        }
    )
    mode_keys = frozenset(
        {
            "work mode",
            "work style",
            "work arrangement",
            "remote status",
            "work type",
            "employment type",
            "workplace",
            "office attendance",
        }
    )
    comp_keys = frozenset(
        {
            "compensation",
            "salary",
            "salary range",
            "pay",
            "pay range",
            "remuneration",
            "package",
            "total compensation",
            "tc",
            "comp",
        }
    )
    exp_keys = frozenset(
        {
            "experience",
            "years of experience",
            "years experience",
            "yoe",
            "minimum experience",
            "min experience",
            "experience required",
            "experience level",
            "required experience",
        }
    )
    min_exp_keys = frozenset({"min experience", "minimum experience", "minimum years", "min years"})
    max_exp_keys = frozenset({"max experience", "maximum experience", "maximum years", "max years"})
    seniority_keys = frozenset({"seniority", "level", "grade"})
    summary_keys = frozenset({"summary", "role summary", "position summary"})

    for raw in str(jd_text).splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key_part, _, value_part = line.partition(":")
        key_norm = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*$", "", key_part).strip()
        key_norm = re.sub(r"\s+", " ", key_norm).lower()
        val = value_part.strip()
        if not val:
            continue
        val_one_line = val.split("\n")[0].strip()

        if key_norm in role_keys:
            r = _clean_jd_field_value(val_one_line, 160)
            if r and len(r) >= 2:
                out["role"] = r
        elif key_norm in loc_keys:
            loc = _clean_jd_field_value(val_one_line, 160)
            if loc:
                out["location"] = loc
        elif key_norm in mode_keys:
            out["work_mode"] = _normalize_work_mode_display(val_one_line)
        elif key_norm in exp_keys:
            mn, mx = _parse_experience_value_to_min_max(val_one_line)
            if mn is not None:
                out["min_experience_years"] = mn
            if mx is not None:
                out["max_experience_years"] = mx
        elif key_norm in min_exp_keys:
            y = extract_years(val_one_line)
            if y:
                out["min_experience_years"] = y
        elif key_norm in max_exp_keys:
            y = extract_years(val_one_line)
            if y:
                out["max_experience_years"] = y
        elif key_norm in seniority_keys:
            s = _clean_jd_field_value(val_one_line, 80)
            if s:
                out["seniority"] = s
        elif key_norm in summary_keys:
            s = _clean_jd_field_value(val, 500)
            if s:
                out["summary"] = s
        elif key_norm in comp_keys:
            c = _clean_jd_field_value(val_one_line, 200)
            if c:
                out["compensation_summary"] = c

    return out


def merge_regex_jd_fields_into_parsed(regex_fields, parsed):
    """Labeled regex wins over LLM fields when the regex produced a value."""
    if not regex_fields:
        return parsed
    for k, v in regex_fields.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, int) and k.endswith("_years") and v < 0:
            continue
        parsed[k] = v
    return parsed


def parse_json_response(raw_text):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# Split JD/candidate skill blobs: commas, semicolons, pipes, slashes, newlines, bullets, "and"
_SKILL_SPLIT_PATTERN = re.compile(r"[,;/|\n•]+|\s+(?:and|&)\s+", re.IGNORECASE)


def normalize_skill_key(s):
    """Lowercase, trimmed, collapsed whitespace for comparison."""
    if s is None:
        return ""
    t = str(s).strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^[•\-\*\.\s]+|[•\-\*\.\s]+$", "", t)
    return t.strip()


def parse_list(value):
    """Flatten nested lists and split strings on common skill delimiters."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        merged = []
        for item in value:
            merged.extend(parse_list(item))
        return [str(x).strip() for x in merged if str(x).strip()]
    if isinstance(value, dict):
        inner = value.get("skills") or value.get("name")
        return parse_list(inner) if inner is not None else []
    s = str(value).strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            inner = json.loads(s)
            if isinstance(inner, list):
                return parse_list(inner)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    parts = [p.strip() for p in _SKILL_SPLIT_PATTERN.split(s) if p and str(p).strip()]
    if not parts:
        return [s]
    return parts


def dedupe_skills_preserve_order(skills):
    """Unique skills by normalized key; keep first-seen display spelling (trimmed)."""
    seen = set()
    out = []
    for raw in skills or []:
        k = normalize_skill_key(raw)
        if not k or k in seen:
            continue
        seen.add(k)
        disp = str(raw).strip()
        if disp:
            out.append(disp)
    return out


def extract_must_skills_from_jd_text(jd_text, max_items=32):
    """Fallback when the model returns no must_have_skills: scan JD for Must have / Required blocks."""
    if not jd_text or not str(jd_text).strip():
        return []
    jd_full = str(jd_text)
    m = re.search(
        r"(?is)(?:^|\n)\s*(?:must[\s-]*have|must-have|required\s*(?:skills|technologies)|"
        r"key\s*skills|technical\s*skills)\s*[:.\-–]?\s*",
        jd_full,
    )
    if not m:
        return []
    window = jd_full[m.end() : m.end() + 4000]
    collected = []
    for raw_line in window.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(
            r"(?i)^(nice\s*to|good\s*to|preferred|optional|responsibilit|qualification|"
            r"what\s*you|you\s*will|benefits|about\s*us|experience\s*[:])",
            line,
        ):
            break
        if re.match(r"(?i)^must\s*have", line) and len(line) < 40:
            continue
        line = re.sub(r"^[\d\s)\.\-\*•>]+", "", line).strip()
        if 2 <= len(line) <= 90 and not line.endswith(":"):
            collected.extend(parse_list(line))
    return dedupe_skills_preserve_order(collected)[:max_items]


def skill_key_matches_jd_to_candidate(jd_skill_display, cand_skill_displays):
    """True if JD skill matches any candidate skill (exact normalized or short substring overlap)."""
    jk = normalize_skill_key(jd_skill_display)
    if not jk:
        return False
    cand_keys = [normalize_skill_key(c) for c in (cand_skill_displays or []) if normalize_skill_key(c)]
    if jk in cand_keys:
        return True
    for ck in cand_keys:
        if len(jk) >= 3 and len(ck) >= 3 and (jk in ck or ck in jk):
            return True
    return False


def partition_jd_skills_against_candidate(jd_skill_list, cand_skill_list):
    """
    Compare JD required skills to candidate profile skills.
    Returns (matched_display_strings, missing_display_strings) using JD wording for both.
    """
    jd_flat = dedupe_skills_preserve_order(parse_list(jd_skill_list))
    cand_flat = dedupe_skills_preserve_order(parse_list(cand_skill_list))
    matched, missing = [], []
    for jd_s in jd_flat:
        if skill_key_matches_jd_to_candidate(jd_s, cand_flat):
            matched.append(jd_s)
        else:
            missing.append(jd_s)
    return matched, missing


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
        "skills": dedupe_skills_preserve_order(parse_list(data.get("skills"))),
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
                "skills": dedupe_skills_preserve_order(parse_list(item["skills"])),
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


def _csv_cell(value):
    """RFC-style quoting when commas, quotes, or newlines appear."""
    s = str(value if value is not None else "")
    if any(c in s for c in ('"', ",", "\n", "\r")):
        return '"' + s.replace('"', '""') + '"'
    return s


def results_to_csv(rows, jd_data=None):
    """Per-candidate shortlist; repeats JD-level compensation on each row for audit / ATS import."""
    jd_comp = ""
    if jd_data:
        jd_comp = (jd_data.get("compensation_summary") or "").strip()
    output = StringIO()
    output.write(
        "rank,name,title,location,match_score,interest_score,final_score,pipeline_stage,"
        "matched_must,missing_must,matched_nice,skill_overlap_pct,exp_fit_pct,loc_fit_pct,"
        "jd_compensation_summary\n"
    )
    for idx, row in enumerate(rows, start=1):
        exp = row["explainability"]
        matched_must = "|".join(exp["matched_must_have"])
        missing_must = "|".join(exp["missing_must_have"])
        matched_nice = "|".join(exp["matched_nice_to_have"])
        stage = row.get("pipeline_stage", "Shortlisted")
        output.write(
            f"{idx},{_csv_cell(row['name'])},{_csv_cell(row['title'])},{_csv_cell(row['location'])},"
            f"{row['match_score']},{row['interest_score']},{row['final_score']},{_csv_cell(stage)},"
            f"{_csv_cell(matched_must)},{_csv_cell(missing_must)},{_csv_cell(matched_nice)},"
            f"{exp.get('skill_overlap_pct', '')},{exp.get('experience_fit_pct', '')},{exp.get('location_fit_pct', '')},"
            f"{_csv_cell(jd_comp)}\n"
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


def build_shortlist_pdf(rows, jd_title, feedback_map, jd_compensation_summary=None):
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
        comp = (jd_compensation_summary or "").strip()
        if comp:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 5, _latin1_pdf_text(f"JD compensation (informational): {comp}", 140), ln=True)
            pdf.set_font("Helvetica", "", 10)
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
    """Hybrid parse: labeled-line regex first, then Gemini JSON; regex wins on overlap."""
    regex_fields = extract_jd_labeled_fields_regex(jd_text)
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
  "summary": "1-2 lines",
  "compensation_summary": "short free-text comp line if stated, else empty string"
}}

Rules:
- must_have_skills and nice_to_have_skills MUST be JSON arrays of strings.
- Put ONE skill per array element (e.g. ["Python", "SQL"]); never one comma-joined string.
- If the JD lists skills in a paragraph, split them into separate array entries.
- If the JD already states Role / Experience / Location / Work mode on labeled lines, keep those values consistent in your JSON.

Job Description:
{jd_text}
"""
    fallback = {
        "role": regex_fields.get("role") or "Unknown Role",
        "must_have_skills": [],
        "nice_to_have_skills": [],
        "min_experience_years": int(regex_fields["min_experience_years"])
        if "min_experience_years" in regex_fields
        else 0,
        "max_experience_years": int(regex_fields["max_experience_years"])
        if "max_experience_years" in regex_fields
        else 0,
        "location": regex_fields.get("location") or "Not specified",
        "work_mode": regex_fields.get("work_mode") or "Not specified",
        "seniority": regex_fields.get("seniority") or "Not specified",
        "summary": regex_fields.get("summary") or "Could not parse JD reliably.",
        "compensation_summary": regex_fields.get("compensation_summary") or "",
    }
    parsed = safe_model_json(prompt, fallback)
    merge_regex_jd_fields_into_parsed(regex_fields, parsed)

    for _k in ("role", "location", "work_mode", "seniority", "summary", "compensation_summary"):
        if isinstance(parsed.get(_k), str):
            parsed[_k] = parsed[_k].strip()
            if _k == "work_mode":
                parsed[_k] = _normalize_work_mode_display(parsed[_k])

    parsed["must_have_skills"] = dedupe_skills_preserve_order(parse_list(parsed.get("must_have_skills")))
    parsed["nice_to_have_skills"] = dedupe_skills_preserve_order(parse_list(parsed.get("nice_to_have_skills")))
    if not parsed["must_have_skills"]:
        parsed["must_have_skills"] = extract_must_skills_from_jd_text(jd_text)
    parsed["min_experience_years"] = extract_years(parsed.get("min_experience_years", 0))
    mx = parsed.get("max_experience_years", 0)
    parsed["max_experience_years"] = extract_years(mx) if mx else 0
    cs = parsed.get("compensation_summary", "")
    parsed["compensation_summary"] = str(cs).strip() if cs is not None else ""
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
    jd_must = dedupe_skills_preserve_order(parse_list(jd_data.get("must_have_skills")))
    min_years = jd_data.get("min_experience_years", 0)
    shortlisted = []

    for candidate in pool:
        cand_flat = dedupe_skills_preserve_order(parse_list(candidate.get("skills")))
        exp_ok = candidate["experience_years"] >= min_years
        if jd_must:
            matched_cnt = sum(1 for s in jd_must if skill_key_matches_jd_to_candidate(s, cand_flat))
            must_ratio = matched_cnt / len(jd_must)
            discovery_score = (must_ratio * 70) + (30 if exp_ok else 10)
        else:
            # No must-haves extracted — do not assume fake skill overlap; gate mainly on experience
            discovery_score = (55 if exp_ok else 28)

        if discovery_score >= 40:
            shortlisted.append(candidate)

    shortlisted.sort(key=lambda c: c["experience_years"], reverse=True)
    return shortlisted[:max_results]


def jd_pool_skill_gaps(must_have_list, discovered_pool):
    """Must-have skills no one in the discovery pool lists on their profile."""
    gap = []
    jd_flat = dedupe_skills_preserve_order(parse_list(must_have_list))
    for m in jd_flat:
        found = False
        for c in discovered_pool or []:
            cand_flat = dedupe_skills_preserve_order(parse_list(c.get("skills")))
            if skill_key_matches_jd_to_candidate(m, cand_flat):
                found = True
                break
        if not found:
            gap.append(m)
    return gap


_JD_GENERIC_STRINGS = frozenset(
    {
        "",
        "—",
        "-",
        "n/a",
        "na",
        "tbd",
        "unknown",
        "unknown role",
        "not specified",
        "unspecified",
        "none",
    }
)


def jd_parse_quality_flags(jd_data):
    """
    Return human-facing issue codes when parsed JD fields look missing or placeholder-like.
    Does not affect scoring; for transparency only.
    """
    if not jd_data:
        return []
    issues = []
    role = (jd_data.get("role") or "").strip()
    if not role or role.lower() in _JD_GENERIC_STRINGS:
        issues.append("role")
    loc = (jd_data.get("location") or "").strip()
    if not loc or loc.lower() in _JD_GENERIC_STRINGS:
        issues.append("location")
    wm = (jd_data.get("work_mode") or "").strip()
    if not wm or wm.lower() in _JD_GENERIC_STRINGS:
        issues.append("work_mode")
    if not (jd_data.get("must_have_skills") or []):
        issues.append("must_have_skills")
    mn = int(jd_data.get("min_experience_years", 0) or 0)
    mx = int(jd_data.get("max_experience_years", 0) or 0)
    if mn == 0 and mx == 0:
        issues.append("experience_band")
    return issues


def render_jd_parse_quality_banner(jd_data):
    flags = jd_parse_quality_flags(jd_data)
    if not flags:
        return
    labels = {
        "role": "role / title",
        "location": "location",
        "work_mode": "work mode",
        "must_have_skills": "must-have skills",
        "experience_band": "experience band (years)",
    }
    txt = ", ".join(labels.get(f, f) for f in flags)
    st.markdown(
        f"""
<div class="jd-coach-card" style="border-left:4px solid #f59e0b;margin-bottom:0.85rem;">
  <p style="margin:0;color:#fde68a;font-size:0.88rem;line-height:1.55;">
    <strong style="color:#f4f6ff;">Parse data quality</strong> —
    these fields look missing or generic: <span style="color:#e7e9f7;">{html.escape(txt)}</span>.
    Add clearer labeled lines in the JD (e.g. <code style="font-size:0.82rem;">Role:</code>,
    <code style="font-size:0.82rem;">Location:</code>) or use the <strong style="color:#f4f6ff;">JD coach</strong> tab.
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_jd_human_card(jd_data, discovered=None, *, show_pool_gap=False):
    """Human-readable JD parse (no JSON) for recruiters."""
    if not jd_data or not jd_data.get("role"):
        return
    must = jd_data.get("must_have_skills") or []
    nice = jd_data.get("nice_to_have_skills") or []
    miny = jd_data.get("min_experience_years", 0)
    maxy = jd_data.get("max_experience_years", 0) or 0
    exp_line = f"{miny}+ years" if maxy <= 0 else f"{miny}–{maxy} years"
    must_disp = ", ".join(must) if must else "— none extracted — add a clear “Must have” list in the JD"
    nice_disp = ", ".join(nice) if nice else "—"
    summ = (jd_data.get("summary") or "").strip()
    summ_html = f'<p style="margin:10px 0 0 0;color:#c4c8e0;font-size:0.92rem;line-height:1.55;border-top:1px solid rgba(255,255,255,0.08);padding-top:10px;">{html.escape(summ)}</p>' if summ else ""
    senior = html.escape(str(jd_data.get("seniority") or "—"))
    comp = (jd_data.get("compensation_summary") or "").strip()
    comp_html = ""
    if comp:
        comp_html = f"""
  <p style="margin:10px 0 0 0;color:#c4c8e0;font-size:0.9rem;line-height:1.55;border-top:1px solid rgba(255,255,255,0.08);padding-top:10px;">
    <strong style="color:#f4f6ff;">Compensation (from JD):</strong> {html.escape(comp)}
  </p>"""
    gap_block = ""
    if show_pool_gap and discovered is not None:
        gap_must = jd_pool_skill_gaps(must, discovered)
        gap_block = f"""
  <p style="margin:12px 0 0 0;color:#fbbf24;font-size:0.92rem;">
    ⚠ <strong style="color:#f4f6ff;">Pool gap (no profile in this pool lists):</strong>
    {html.escape(", ".join(gap_must) if gap_must else "— none detected in this pool")}
  </p>"""
    st.markdown(
        f"""
<div class="ats-card" style="margin-bottom:1rem;">
  <div class="ats-section-title">Role profile · parsed from JD</div>
  <p style="margin:0 0 8px 0;color:#f4f6ff;font-size:1.2rem;font-weight:800;letter-spacing:-0.02em;">{html.escape(str(jd_data.get("role") or "—"))}</p>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
    <span class="ats-skill-pill" style="background:rgba(34,197,94,0.12);border-color:rgba(34,197,94,0.45);color:#86efac;">Seniority: {senior}</span>
    <span class="ats-skill-pill">Experience band: {html.escape(exp_line)}</span>
  </div>
  <p style="margin:0;color:#c4c8e0;font-size:0.95rem;line-height:1.65;">
    <strong style="color:#f4f6ff;">Where / how:</strong> {html.escape(str(jd_data.get("location") or "—"))}
    · {html.escape(str(jd_data.get("work_mode") or "—"))}<br/>
    <strong style="color:#f4f6ff;">Must-have ({len(must)}):</strong> {html.escape(must_disp)}<br/>
    <strong style="color:#f4f6ff;">Nice-to-have ({len(nice)}):</strong> {html.escape(nice_disp)}
  </p>{summ_html}{comp_html}{gap_block}
</div>
        """,
        unsafe_allow_html=True,
    )


def score_match_with_explainability(jd_data, candidate):
    jd_must_src = jd_data.get("must_have_skills") or []
    jd_nice_src = jd_data.get("nice_to_have_skills") or []
    cand_skills_src = candidate.get("skills") or []

    matched_must, missing_must = partition_jd_skills_against_candidate(jd_must_src, cand_skills_src)
    matched_nice, _missing_nice = partition_jd_skills_against_candidate(jd_nice_src, cand_skills_src)

    must_f = dedupe_skills_preserve_order(parse_list(jd_must_src))
    nice_f = dedupe_skills_preserve_order(parse_list(jd_nice_src))
    matched_must = sorted(matched_must, key=lambda x: normalize_skill_key(x))
    missing_must = sorted(missing_must, key=lambda x: normalize_skill_key(x))
    matched_nice = sorted(matched_nice, key=lambda x: normalize_skill_key(x))

    # Ratios strictly from list overlap — never invent overlap when JD lists are empty
    must_ratio = (len(matched_must) / len(must_f)) if must_f else 0.0
    nice_ratio = (len(matched_nice) / len(nice_f)) if nice_f else 0.0
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

    skill_overlap_pct = clamp_score(must_ratio * 100) if must_f else 0
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

    # When JD has no skill lists, weight experience + location more so scores stay interpretable
    if must_f or nice_f:
        base_match = clamp_score(
            (must_ratio * 50) + (nice_ratio * 20) + (exp_ratio * 15) + (loc_score / 100 * 15)
        )
    else:
        base_match = clamp_score((exp_ratio * 40) + (loc_score / 100 * 30))

    # Explicit location / experience modifiers (penalty for mismatch, small bonus when both strong)
    loc_penalty_pts = max(0, min(14, int(round((62 - loc_score) * 0.26))))
    exp_penalty_pts = max(0, min(14, int(round((62 - experience_fit_pct) * 0.24))))
    # Extra realism: years clearly below JD minimum
    if min_y > 0 and cand_y < min_y:
        exp_penalty_pts = min(14, exp_penalty_pts + min(6, 2 + (min_y - cand_y)))
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
    # Prevent LLM nudge from contradicting zero must-have overlap when the JD defines must-haves
    if must_f and not matched_must:
        adjustment = min(adjustment, 0)
    final_match = clamp_score(base_match + adjustment)

    explainability = {
        "matched_must_have": matched_must,
        "missing_must_have": missing_must,
        "matched_nice_to_have": matched_nice,
        "jd_must_skill_count": len(must_f),
        "base_match_score": base_match,
        "llm_adjustment": adjustment,
        "reason": explain_json.get("explanation", ""),
        "skill_overlap_pct": skill_overlap_pct,
        "nice_overlap_pct": clamp_score(nice_ratio * 100) if nice_f else 0,
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
    fs = lambda r: display_final_score(r, feedback_map)
    leader = max(rows, key=fs)
    e = leader.get("explainability") or {}
    jn = int(e.get("jd_must_skill_count", 0) or 0)
    mm = e.get("matched_must_have") or []
    overlap_line = (
        f"**Must-have coverage (#1):** {len(mm)}/{jn} JD skills matched · overlap **{e.get('skill_overlap_pct', 0)}%**."
        if jn
        else "**Must-have coverage:** no must-have list in the parsed JD — compare skills manually."
    )
    lines = [
        f"**#{1} — {leader['name']}** leads with final score **{fs(leader)}** "
        f"(match **{leader['match_score']}**, interest **{leader['interest_score']}**).",
        overlap_line,
    ]
    drivers = []
    if jn and e.get("skill_overlap_pct", 0) >= 65:
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
        rest = sorted([r for r in rows if r.get("name") != leader.get("name")], key=fs, reverse=True)
        s2 = rest[0]
        gap = fs(leader) - fs(s2)
        lines.append(
            f"**vs next ({s2['name']}, {fs(s2)}):** gap of **{gap}** points — "
            f"usually from a mix of match detail, interest signal, and recruiter feedback nudges."
        )
    return "\n\n".join(lines)


def _format_skill_phrase(skills):
    if not skills:
        return "—"
    return ", ".join(str(s).strip() for s in skills if str(s).strip())


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
    """Top decision block: recommended hire + why (ATS-style)."""
    if not rows:
        return
    top = max(rows, key=lambda r: display_final_score(r, feedback_map))
    fs = display_final_score(top, feedback_map)
    exp = top.get("explainability") or {}
    mm = exp.get("matched_must_have") or []
    miss = exp.get("missing_must_have") or []
    jd_must_n = int(exp.get("jd_must_skill_count", 0) or 0)
    skill_short = _format_skill_phrase(mm[:8]) if mm else "—"
    reason = html.escape(str(top.get("interest_reason", "") or "").strip())
    matched = _format_skill_phrase(mm) if mm else ("—" if jd_must_n else "N/A (no JD must-haves)")
    missing_preview = _format_skill_phrase(miss[:6]) if miss else "—"
    mc = _traffic_color(top.get("match_score", 0))
    ic = _traffic_color(top.get("interest_score", 0))
    fc = _traffic_color(fs)
    bullets_plain = []
    if jd_must_n == 0:
        bullets_plain.append("Parsed JD has no must-have skill list — use profile + interview to validate fit.")
    elif mm:
        bullets_plain.append(f"Covers {len(mm)}/{jd_must_n} JD must-haves: {skill_short}.")
    else:
        bullets_plain.append(f"0/{jd_must_n} JD must-haves on profile — technical gap vs this JD; match score reflects that.")
    if exp.get("experience_fit_pct", 0) >= 65:
        bullets_plain.append("Experience band lines up with the JD.")
    else:
        bullets_plain.append("Experience vs JD: see range note on the candidate card.")
    if exp.get("location_fit_pct", 0) >= 65:
        bullets_plain.append("Location / work mode is compatible with the JD.")
    if top.get("interest_score", 0) >= 65:
        bullets_plain.append("Simulated outreach: strong interest / availability signal.")
    elif top.get("interest_score", 0) >= 45:
        bullets_plain.append("Simulated outreach: moderate interest — still worth a screen.")
    bullets_plain = bullets_plain[:5]
    bullets_html = "".join(f"<li style='margin-bottom:6px;'>{html.escape(b)}</li>" for b in bullets_plain)
    st.markdown(
        f"""
<div class="insight-card">
  <div class="ats-section-title" style="margin-bottom:6px;">Recommended candidate</div>
  <h4 style="margin:0 0 10px 0;">{html.escape(str(top.get("name", "")))} · {html.escape((str(top.get("title") or ""))[:56])}</h4>
  <div style="margin-bottom:12px;">
    <span class="reco-kpi"><strong>Final</strong> <span style="color:{fc};font-weight:800;">{fs}</span></span>
    <span class="reco-kpi"><strong>Match</strong> <span style="color:{mc};font-weight:800;">{top.get("match_score", "—")}</span></span>
    <span class="reco-kpi"><strong>Interest</strong> <span style="color:{ic};font-weight:800;">{top.get("interest_score", "—")}</span></span>
    <span class="reco-kpi"><strong>Must-haves</strong> <span style="color:#c4c8e0;">{len(mm)}/{jd_must_n if jd_must_n else "—"}</span></span>
  </div>
  <p style="margin:0 0 6px 0;color:#f4f6ff;font-size:0.82rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;">Why this pick</p>
  <ul style="list-style:disc;color:#c4c8e0;margin:0;padding-left:1.15rem;line-height:1.55;font-size:0.93rem;">{bullets_html}</ul>
  <p class="sub"><strong style="color:#86efac;">Matched</strong> {html.escape(matched)}</p>
  <p class="sub"><strong style="color:#fca5a5;">Still missing</strong> {html.escape(missing_preview)}</p>
  {f'<p class="sub"><strong style="color:#f4f6ff;">Outreach read</strong> — {reason}</p>' if reason else ''}
</div>
        """,
        unsafe_allow_html=True,
    )


def passes_skill_refine(row, selected_skills):
    if not selected_skills:
        return True
    cand_displays = list(row.get("skills") or [])
    for need in selected_skills:
        if not skill_key_matches_jd_to_candidate(need, cand_displays):
            return False
    return True


def pay_context_card_style(toggle_on, jd_data):
    """
    Optional soft visual on shortlist cards: highlight when JD lists compensation, dim when absent.
    Returns a safe HTML fragment for the opening <div ...> of the card (empty string = default).
    """
    if not toggle_on or not jd_data:
        return ""
    comp = (jd_data.get("compensation_summary") or "").strip()
    if comp:
        return ' style="border:1px solid rgba(52,211,153,0.55);box-shadow:0 0 28px rgba(34,197,94,0.14);"'
    return ' style="opacity:0.78;filter:saturate(0.9);border:1px solid rgba(251,191,36,0.35);"'


def render_profile_card(item, rank, final_display_score, card_wrap_style=""):
    """ATS candidate card — fixed layout for scanability (matches common ATS tools)."""
    exp = item.get("explainability") or {}
    loc_line = html.escape(str(item.get("location", "")))
    title_line = html.escape(str(item.get("title", "")))
    name_line = html.escape(str(item.get("name", "")))
    sum_line = html.escape(str(item.get("candidate_summary", ""))[:220])
    yr = int(item.get("experience_years", 0) or 0)
    jmin = exp.get("jd_min_years", 0)
    jmax = exp.get("jd_max_years", 0)
    if jmin and jmax:
        jd_yr_txt = f"JD asks {jmin}–{jmax} yrs"
    elif jmin:
        jd_yr_txt = f"JD asks {jmin}+ yrs"
    else:
        jd_yr_txt = "JD experience band open"
    match_s = item.get("match_score", "—")
    interest_s = item.get("interest_score", "—")
    match_c = _traffic_color(match_s)
    interest_c = _traffic_color(interest_s)
    final_c = _traffic_color(final_display_score)
    matched_must = exp.get("matched_must_have") or []
    missing_must = exp.get("missing_must_have") or []
    jd_must_n = int(exp.get("jd_must_skill_count", -1))
    if jd_must_n < 0:
        jd_must_n = len(matched_must) + len(missing_must)
    overlap_badge = ""
    if jd_must_n > 0:
        pct = exp.get("skill_overlap_pct", int(round(100 * len(matched_must) / jd_must_n)))
        overlap_badge = f"""<span class="ats-skill-pill" style="margin-bottom:10px;background:rgba(79,142,247,0.15);border-color:rgba(127,168,249,0.5);color:#c8d9ff;">Must-have overlap: {len(matched_must)}/{jd_must_n} · {pct}%</span>"""
    if jd_must_n == 0:
        matched_txt = "— (no must-have skills extracted from JD — refine the JD and re-run)"
        missing_txt = "—"
    else:
        matched_txt = _format_skill_phrase(matched_must) if matched_must else "None — profile does not list these JD must-haves"
        miss_show = missing_must[:12]
        missing_txt = _format_skill_phrase(miss_show) if miss_show else "None"
        if missing_must and len(missing_must) > 12:
            missing_txt += f" (+{len(missing_must) - 12} more)"
    loc_fit = exp.get("location_fit_pct", "—")
    exp_fit = exp.get("experience_fit_pct", "—")
    yr_warn = ""
    if jmin and yr < jmin:
        yr_warn = f'<p style="margin:8px 0 0 0;color:#FBBF24;font-size:0.82rem;">⚠ Fewer years than JD minimum ({yr} vs {jmin}+) — scoring reflects this.</p>'
    wrap = card_wrap_style if isinstance(card_wrap_style, str) else ""
    card = f"""
<div class="ats-card"{wrap}>
  <div class="ats-section-title">Rank #{rank} · {html.escape(jd_yr_txt)}</div>
  <div style="font-size:1.45rem;font-weight:800;letter-spacing:-0.02em;color:#f4f6ff;line-height:1.2;margin-bottom:4px;">{name_line}</div>
  <div style="color:#c4c8e0;font-size:0.88rem;margin-bottom:10px;">{title_line}</div>
  <div style="color:#f4f6ff;font-size:0.95rem;font-weight:600;margin-bottom:12px;line-height:1.5;">
    {loc_line} · {yr} yrs experience
  </div>
  {overlap_badge}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
    <div style="background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 12px;">
      <div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:#8b90ae;font-weight:700;">Match</div>
      <div style="color:{match_c};font-weight:800;font-size:1.45rem;line-height:1.2;">{match_s}</div>
    </div>
    <div style="background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 12px;">
      <div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:#8b90ae;font-weight:700;">Interest</div>
      <div style="color:{interest_c};font-weight:800;font-size:1.45rem;line-height:1.2;">{interest_s}</div>
    </div>
  </div>
  <div style="margin-bottom:16px;font-size:1rem;padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,0.1);">
    <span style="color:#f4f6ff;font-weight:600;">Final score</span>
    <span style="color:{final_c};font-weight:800;font-size:1.4rem;"> {final_display_score}</span>
    <span style="color:#8b90ae;font-size:0.78rem;margin-left:8px;">Exp fit {exp_fit}% · Loc {loc_fit}%</span>
  </div>
  <div style="font-size:0.92rem;line-height:1.55;margin-bottom:8px;padding:10px;border-radius:10px;background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);">
    <span style="color:#86efac;font-weight:700;">Matched</span>
    <span style="color:#c4c8e0;"> {matched_txt}</span>
  </div>
  <div style="font-size:0.92rem;line-height:1.55;margin-bottom:10px;padding:10px;border-radius:10px;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.22);">
    <span style="color:#fca5a5;font-weight:700;">Missing</span>
    <span style="color:#c4c8e0;"> {missing_txt}</span>
  </div>
  {yr_warn}
  <div style="font-size:0.84rem;color:#6b6e8c;line-height:1.45;margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.06);">{sum_line}</div>
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

_release_notes_path = project_root / "RELEASE_NOTES.md"
try:
    _release_notes_md = _release_notes_path.read_text(encoding="utf-8")
except OSError:
    _release_notes_md = (
        "**Release notes** could not be loaded. Add `RELEASE_NOTES.md` next to `app.py`, "
        "or open that file in the repository for the full changelog."
    )
with st.expander("Release notes", expanded=False):
    st.markdown(_release_notes_md)

st.sidebar.header("Controls")
num_candidates = st.sidebar.slider("Shortlist size", 1, 12, 6)
match_weight_pct = st.sidebar.slider("Match weight %", 0, 100, 60, 5)
interest_weight_pct = 100 - match_weight_pct
st.sidebar.caption(f"Interest weight: {interest_weight_pct}%")
min_final_threshold = st.sidebar.slider("Min final score", 0, 100, 0, 5)
st.sidebar.divider()
st.sidebar.subheader("ATS filters")
st.sidebar.caption("Filter by experience, required skill, and location.")
min_exp_filter = st.sidebar.number_input("Minimum experience (years)", 0, 30, 0)
max_exp_filter = st.sidebar.number_input("Maximum experience (years)", 0, 30, 30)
filter_skill = st.sidebar.text_input("Required skill (contains)", placeholder="e.g. Python")
filter_title = st.sidebar.text_input("Title contains", placeholder="engineer")
filter_loc = st.sidebar.text_input("Location (contains)", placeholder="city / remote")
remote_only = st.sidebar.toggle("Remote location only", value=False)
strict_must_haves = st.sidebar.toggle("Require all JD must-have skills", value=False)
pay_context_viz = st.sidebar.toggle(
    "Soft pay context on roster",
    value=False,
    help="When on: green accent on shortlist cards if the parsed JD includes pay/comp text; "
    "amber tint + slight dim if no pay line was parsed. Informational only — does not filter.",
)
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
        exp = row.get("explainability") or {}
        cand_skills = []
        for c in discovered:
            if c["name"] == row["name"]:
                cand_skills = list(c.get("skills") or [])
                break
        combined_skills = cand_skills + list(exp.get("matched_must_have") or [])
        blob = (row["title"] + " " + row["candidate_summary"]).lower()
        if not skill_key_matches_jd_to_candidate(filter_skill, combined_skills) and filter_skill.lower() not in blob:
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

    if jd_data:
        render_jd_parse_quality_banner(jd_data)

    filtered_display.sort(key=display_score, reverse=True)

    if not filtered_display:
        st.warning("No candidates match your sidebar filters. Clear filters or widen experience range.")

    if filtered_display:
        render_top_candidate_insight(filtered_display, feedback, jd_data)

    avg_m = avg_i = avg_f = 0.0
    top = None
    top_skill = "—"
    if filtered_display:
        avg_m = sum(r["match_score"] for r in filtered_display) / len(filtered_display)
        avg_i = sum(r["interest_score"] for r in filtered_display) / len(filtered_display)
        avg_f = sum(display_score(r) for r in filtered_display) / len(filtered_display)
        top = max(filtered_display, key=lambda x: display_score(x))
        top_skill = _top_skill_in_rows(filtered_display)

    st.markdown("### Summary dashboard")
    st.caption("Data snapshot for this run · “In view” follows sidebar ATS filters.")
    d1, d2, d3, d4, d5, d6 = st.columns(6)
    d1.metric("Total candidates", len(results))
    d2.metric("In view", len(filtered_display))
    d3.metric("Avg match", round(avg_m, 1) if filtered_display else "—")
    d4.metric("Avg interest", round(avg_i, 1) if filtered_display else "—")
    d5.metric("Avg final (view)", round(avg_f, 1) if filtered_display else "—")
    d6.metric("Top skill", str(top_skill)[:20] + ("…" if len(str(top_skill)) > 20 else ""))

    dl1, dl2 = st.columns(2)
    with dl1:
        if filtered_display:
            csv_bytes = _ensure_download_bytes(results_to_csv(filtered_display, jd_data))
            st.download_button(
                "Download CSV",
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
            pdf_bytes = build_shortlist_pdf(
                filtered_display,
                jd_data.get("role", "Role"),
                feedback,
                jd_data.get("compensation_summary") or "",
            )
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
        if pay_context_viz:
            comp_ok = bool((jd_data.get("compensation_summary") or "").strip())
            st.caption(
                "Pay context (soft): roster cards use a **green** frame when the JD includes a parsed pay line, "
                "or **amber + dim** when no pay line was extracted — exports still include `jd_compensation_summary` when present."
                if comp_ok
                else "Pay context (soft): **amber + dim** — parsed JD has no compensation line; exports may have an empty pay column."
            )
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
                            wrap = pay_context_card_style(pay_context_viz, jd_data)
                            render_profile_card(item, rank, fs, wrap)
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
        st.caption("Fit breakdown — percentages match the same logic as the headline match score.")
        for item in filtered_display:
            exp = item["explainability"]
            st.markdown(f"#### {item['name']}")
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Must-have overlap", f"{exp.get('skill_overlap_pct', 0)}%")
            g2.metric("Nice-to-have", f"{exp.get('nice_overlap_pct', 0)}%")
            g3.metric("Experience fit", f"{exp.get('experience_fit_pct', 0)}%")
            g4.metric("Location fit", f"{exp.get('location_fit_pct', 0)}%")
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
                    f"Score shaping: −{lp} location, −{ep} experience, +{ab} alignment bonus (see match score on card)."
                )
            mm = exp.get("matched_must_have") or []
            miss = exp.get("missing_must_have") or []
            jn = int(exp.get("jd_must_skill_count", 0) or 0)
            st.markdown(
                f"""
<div class="exp-mini-card">
  <p style="margin:0 0 8px 0;color:#f4f6ff;font-weight:700;font-size:0.88rem;">Summary</p>
  <p style="margin:0;color:#c4c8e0;font-size:0.9rem;line-height:1.55;">{html.escape(str(exp.get("reason") or ""))}</p>
  <p style="margin:10px 0 4px 0;color:#8b90ae;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;">Skills vs JD</p>
  <p style="margin:0;color:#86efac;font-size:0.88rem;"><strong>Matched ({len(mm)}/{jn if jn else "—"})</strong> {html.escape(_format_skill_phrase(mm))}</p>
  <p style="margin:6px 0 0 0;color:#fca5a5;font-size:0.88rem;"><strong>Missing</strong> {html.escape(_format_skill_phrase(miss))}</p>
</div>
<div class="exp-mini-card">
  <p style="margin:0;color:#c4c8e0;font-size:0.88rem;line-height:1.5;"><strong style="color:#f4f6ff;">Domain</strong> {html.escape(str(exp.get("domain_relevance_note") or ""))}</p>
  <p style="margin:8px 0 0 0;color:#c4c8e0;font-size:0.88rem;"><strong style="color:#f4f6ff;">Experience</strong> {html.escape(str(exp.get("experience_range_note") or ""))}</p>
  <p style="margin:6px 0 0 0;color:#c4c8e0;font-size:0.88rem;">{html.escape(str(exp.get("experience_alignment_note") or ""))}</p>
  <p style="margin:8px 0 0 0;color:#c4c8e0;font-size:0.88rem;"><strong style="color:#f4f6ff;">Location</strong> {html.escape(str(exp.get("location_work_mode_note") or ""))}</p>
</div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Outreach transcript (simulated)"):
                for line in item["conversation"]:
                    st.markdown(f"- {line}")
                st.markdown("**Signals**")
                sig = item.get("signals") or {}
                if isinstance(sig, dict):
                    for k, v in sig.items():
                        st.markdown(f"- **{html.escape(str(k))}:** {html.escape(str(v))}")
                else:
                    st.caption("No structured signals returned.")
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
            clarity = sug.get("overall_clarity_score", "—")
            st.markdown(
                f"""
<div class="jd-coach-card" style="border-left:4px solid #4f8ef7;">
  <h5>JD clarity</h5>
  <p style="margin:0;font-size:1.75rem;font-weight:800;color:#7eb0ff;">{html.escape(str(clarity))}<span style="font-size:0.95rem;color:#8b90ae;font-weight:600;"> / 100</span></p>
  <p style="margin:6px 0 0 0;color:#8b90ae;font-size:0.85rem;">Higher = clearer expectations for candidates and better automated matching.</p>
</div>
                """,
                unsafe_allow_html=True,
            )
            sug_lines = "".join(
                f'<p style="margin:0 0 8px 0;color:#c4c8e0;font-size:0.9rem;line-height:1.5;">'
                f'<span style="color:#7eb0ff;font-weight:700;">{html.escape(str(s.get("type", "tip")).upper())}</span> — '
                f'{html.escape(str(s.get("message", "")))}</p>'
                for s in (sug.get("suggestions") or [])[:10]
            )
            st.markdown(
                f'<div class="jd-coach-card"><h5>Improvements</h5>{sug_lines or "<p style=color:#8b90ae>No suggestions returned.</p>"}</div>',
                unsafe_allow_html=True,
            )
            miss_items = sug.get("missing_or_vague_items") or []
            add_items = sug.get("recommended_must_have_additions") or []
            st.markdown(
                f"""
<div class="jd-coach-card">
  <h5>Still vague or missing</h5>
  <ul style="margin:0;padding-left:1.1rem;color:#c4c8e0;line-height:1.55;font-size:0.9rem;">
    {"".join(f"<li>{html.escape(str(m))}</li>" for m in miss_items[:12]) or "<li>Nothing flagged</li>"}
  </ul>
</div>
<div class="jd-coach-card">
  <h5>Suggested must-have lines</h5>
  <ul style="margin:0;padding-left:1.1rem;color:#c4c8e0;line-height:1.55;font-size:0.9rem;">
    {"".join(f"<li>{html.escape(str(m))}</li>" for m in add_items[:12]) or "<li>No additions suggested</li>"}
  </ul>
</div>
                """,
                unsafe_allow_html=True,
            )

    with tabs[5]:
        st.subheader("JD analysis & discovery pool")
        if not jd_data or not jd_data.get("role"):
            st.info("Run the agent to parse the JD and load the discovery pool.")
        else:
            render_jd_human_card(jd_data, discovered, show_pool_gap=True)
            summ = (jd_data.get("summary") or "").strip()
            if summ:
                st.markdown(
                    f'<div class="jd-coach-card"><h5>Role in one glance</h5><p style="margin:0;color:#c4c8e0;line-height:1.55;">{html.escape(summ)}</p></div>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                f'<p style="color:#8b90ae;font-size:0.85rem;margin:0 0 10px 0;">Discovery pool · <strong style="color:#f4f6ff;">{len(discovered)}</strong> profiles</p>',
                unsafe_allow_html=True,
            )
            if not discovered:
                st.caption("No candidates met the discovery gate for this run.")
            else:
                for c in discovered:
                    nm = html.escape(str(c.get("name", "")))
                    tl = html.escape(str(c.get("title", "")))
                    loc = html.escape(str(c.get("location", "")))
                    yrs = int(c.get("experience_years", 0) or 0)
                    sk_raw = (c.get("skills") or [])[:10]
                    sk_pills = "".join(
                        f'<span class="ats-skill-pill" style="font-size:0.75rem;padding:3px 8px;">{html.escape(str(s))}</span>'
                        for s in sk_raw
                    )
                    st.markdown(
                        f"""
<div class="ats-card" style="padding:1rem 1.15rem;margin-bottom:0.65rem;">
  <div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline;">
    <span style="color:#f4f6ff;font-weight:800;font-size:1.02rem;">{nm}</span>
    <span style="color:#7eb0ff;font-weight:700;font-size:0.88rem;">{yrs} yrs</span>
  </div>
  <p style="margin:4px 0 8px 0;color:#c4c8e0;font-size:0.88rem;">{tl} · {loc}</p>
  <div>{sk_pills}</div>
</div>
                        """,
                        unsafe_allow_html=True,
                    )

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
