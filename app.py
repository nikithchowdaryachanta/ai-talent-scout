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
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .block-container { padding-top: 1.25rem; padding-bottom: 2.5rem; max-width: 1200px; }
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdown"] > h1) {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        border-radius: 16px; padding: 1.5rem 1.75rem; margin-bottom: 1.5rem;
        border: 1px solid rgba(148,163,184,0.25);
    }
    h1 { color: #f8fafc !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    h1 + div p, h1 ~ div p { color: #cbd5e1 !important; }
    .metric-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 1rem 1.25rem; box-shadow: 0 1px 3px rgba(15,23,42,0.06);
    }
    div[data-baseweb="tab-highlight"] { background-color: #0ea5e9 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: #f1f5f9; padding: 6px; border-radius: 12px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; }
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


def location_compatibility_score(jd_location, cand_location):
    jd_l = (jd_location or "").lower().strip()
    cand_l = (cand_location or "").lower().strip()
    if not jd_l or jd_l == "not specified":
        return 85, "JD location unspecified — neutral fit."
    if "remote" in jd_l or "anywhere" in jd_l:
        return 100, "JD allows remote — strong compatibility."
    if "remote" in cand_l:
        return 95, "Candidate is remote — typically compatible with distributed teams."
    if jd_l in cand_l or cand_l in jd_l:
        return 90, "Location wording aligns with JD."
    if any(c in cand_l for c in ["india", "in "]):
        return 70, "Same broad region possible — confirm relocation/hybrid policy."
    return 55, "Location may need alignment — discuss with candidate."


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


def build_shortlist_pdf(rows, jd_title, feedback_map):
    if FPDF is None:
        return None
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "TalentScout AI - Shortlist Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Role context: {jd_title[:80]}", ln=True)
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
        pdf.cell(40, 7, (row["name"] or "")[:22], border=1)
        pdf.cell(25, 7, str(row["match_score"]), border=1)
        pdf.cell(25, 7, str(row["interest_score"]), border=1)
        pdf.cell(25, 7, str(fs), border=1)
        pdf.cell(40, 7, (row.get("pipeline_stage", "") or "")[:18], border=1)
        pdf.ln()
    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", errors="replace")
    return out


def parse_jd(jd_text):
    prompt = f"""
Extract structured hiring requirements from the Job Description.
Return valid JSON only:
{{
  "role": "short role title",
  "must_have_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill3"],
  "min_experience_years": 0,
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
        "location": "Not specified",
        "work_mode": "Not specified",
        "seniority": "Not specified",
        "summary": "Could not parse JD reliably.",
    }
    parsed = safe_model_json(prompt, fallback)
    parsed["must_have_skills"] = parse_list(parsed.get("must_have_skills"))
    parsed["nice_to_have_skills"] = parse_list(parsed.get("nice_to_have_skills"))
    parsed["min_experience_years"] = extract_years(parsed.get("min_experience_years", 0))
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


def score_match_with_explainability(jd_data, candidate):
    must_have = {skill.lower() for skill in jd_data.get("must_have_skills", [])}
    nice_to_have = {skill.lower() for skill in jd_data.get("nice_to_have_skills", [])}
    cand_skills = {skill.lower() for skill in candidate["skills"]}

    matched_must = sorted(must_have.intersection(cand_skills))
    missing_must = sorted(must_have.difference(cand_skills))
    matched_nice = sorted(nice_to_have.intersection(cand_skills))

    must_ratio = len(matched_must) / len(must_have) if must_have else 0.6
    nice_ratio = len(matched_nice) / len(nice_to_have) if nice_to_have else 0.5
    min_y = jd_data.get("min_experience_years", 0) or 1
    exp_ratio = min(1.0, candidate["experience_years"] / max(1, min_y))

    skill_overlap_pct = clamp_score(must_ratio * 100)
    experience_fit_pct = clamp_score(exp_ratio * 100)
    loc_score, loc_note = location_compatibility_score(jd_data.get("location"), candidate.get("location"))

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
Location compatibility score: {loc_score}
Base match score: {base_match}
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
        "experience_alignment_note": explain_json.get("experience_alignment_note", ""),
        "location_work_mode_note": explain_json.get("location_work_mode_note", loc_note),
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
]:
    if key not in st.session_state:
        st.session_state[key] = default

# -----------------------------
# Header
# -----------------------------
st.markdown("# TalentScout AI")
st.markdown(
    "**Production-grade talent intelligence** — explainable matching, resume ingestion, "
    "ATS pipeline, analytics, and JD coaching in one workspace."
)

st.sidebar.header("Controls")
num_candidates = st.sidebar.slider("Shortlist size", 1, 12, 6)
match_weight_pct = st.sidebar.slider("Match weight %", 0, 100, 60, 5)
interest_weight_pct = 100 - match_weight_pct
st.sidebar.caption(f"Interest weight: {interest_weight_pct}%")
min_final_threshold = st.sidebar.slider("Min final score", 0, 100, 0, 5)
st.sidebar.divider()
st.sidebar.subheader("Search & filters")
filter_skill = st.sidebar.text_input("Skill contains", placeholder="python")
filter_title = st.sidebar.text_input("Title contains", placeholder="engineer")
filter_loc = st.sidebar.text_input("Location contains", placeholder="remote")
min_exp_filter = st.sidebar.number_input("Min years exp", 0, 30, 0)
max_exp_filter = st.sidebar.number_input("Max years exp", 0, 30, 30)
remote_only = st.sidebar.toggle("Remote location only", value=False)
st.sidebar.divider()
if st.sidebar.button("Clear feedback & pipeline memory"):
    st.session_state["recruiter_feedback"] = {}
    st.session_state["pipeline_stage_by_name"] = {}
    st.sidebar.success("Reset.")

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
    if filtered_display:
        avg_m = sum(r["match_score"] for r in filtered_display) / len(filtered_display)
        avg_i = sum(r["interest_score"] for r in filtered_display) / len(filtered_display)
        top = max(filtered_display, key=lambda x: display_score(x))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("In view", len(filtered_display))
    m2.metric("Avg match", round(avg_m, 1))
    m3.metric("Avg interest", round(avg_i, 1))
    m4.metric(
        "Top pick",
        f"{top['name']} ({display_score(top)})" if top is not None else "—",
    )

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Export CSV",
            data=results_to_csv(filtered_display),
            file_name="shortlist.csv",
            mime="text/csv",
            disabled=not filtered_display,
        )
    with dl2:
        pdf_bytes = (
            build_shortlist_pdf(filtered_display, jd_data.get("role", "Role"), feedback) if filtered_display else None
        )
        if pdf_bytes:
            st.download_button(
                "Export PDF report",
                data=pdf_bytes,
                file_name="shortlist.pdf",
                mime="application/pdf",
                disabled=not filtered_display,
            )
        else:
            st.caption("PDF export: pip install fpdf2")

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
        for rank, item in enumerate(filtered_display, start=1):
            fs = display_score(item)
            with st.container():
                st.markdown(f"#### {rank}. {item['name']} · {item['title']}")
                st.caption(f"{item['location']} · Final **{fs}** (match {item['match_score']}, interest {item['interest_score']})")
                c1, c2, c3 = st.columns(3)
                c1.metric("Match", item["match_score"])
                c2.metric("Interest", item["interest_score"])
                c3.metric("Adjusted final", fs)
                st.progress(min(1.0, fs / 100.0))
                st.write(item["candidate_summary"])
                b1, b2, b3 = st.columns(3)
                if b1.button("Approve", key=f"app_{item['name']}"):
                    st.session_state["recruiter_feedback"][item["name"]] = 1
                    st.rerun()
                if b2.button("Reject", key=f"rej_{item['name']}"):
                    st.session_state["recruiter_feedback"][item["name"]] = -1
                    st.rerun()
                if b3.button("Clear vote", key=f"clr_{item['name']}"):
                    st.session_state["recruiter_feedback"].pop(item["name"], None)
                    st.rerun()
                vote = feedback.get(item["name"])
                if vote == 1:
                    st.success("Feedback: strong fit — future runs bias this profile positively (+3 final).")
                elif vote == -1:
                    st.warning("Feedback: poor fit — future runs bias down (-3 final).")
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
            st.write("**Narrative:**", exp.get("reason", ""))
            st.write("**Domain:**", exp.get("domain_relevance_note", ""))
            st.write("**Experience:**", exp.get("experience_alignment_note", ""))
            st.write("**Location / mode:**", exp.get("location_work_mode_note", ""))
            st.write("**Matched must-have:**", ", ".join(exp["matched_must_have"]) or "—")
            st.write("**Missing must-have:**", ", ".join(exp["missing_must_have"]) or "—")
            with st.expander("Outreach transcript"):
                for line in item["conversation"]:
                    st.write(line)
                st.json(item.get("signals", {}))
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
        st.json(discovered)

else:
    st.markdown(
        """
        **Getting started**
        1. Paste a JD and choose candidate source.  
        2. Click **Run agent**.  
        3. Use **Shortlist**, **Explainability**, **ATS pipeline**, **Analytics**, and **JD coach** tabs.
        """
    )
