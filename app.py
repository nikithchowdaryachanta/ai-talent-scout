import json
import os
import re

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="TalentScout AI", page_icon="🤖", layout="wide")


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
        "seniority": "Not specified",
        "summary": "Could not parse JD reliably.",
    }
    parsed = safe_model_json(prompt, fallback)
    parsed["must_have_skills"] = parse_list(parsed.get("must_have_skills"))
    parsed["nice_to_have_skills"] = parse_list(parsed.get("nice_to_have_skills"))
    parsed["min_experience_years"] = extract_years(parsed.get("min_experience_years", 0))
    return parsed


def discover_candidates(pool, jd_data, max_results):
    must_have = {skill.lower() for skill in jd_data.get("must_have_skills", [])}
    min_years = jd_data.get("min_experience_years", 0)
    shortlisted = []

    for candidate in pool:
        cand_skills = {skill.lower() for skill in candidate["skills"]}
        matched_must = len(must_have.intersection(cand_skills))
        must_ratio = matched_must / len(must_have) if must_have else 0.5
        exp_ok = candidate["experience_years"] >= min_years

        # Lightweight "discovery" stage before deep LLM scoring.
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
    exp_ratio = min(1.0, candidate["experience_years"] / max(1, jd_data.get("min_experience_years", 0) or 1))

    base_match = clamp_score((must_ratio * 65) + (nice_ratio * 20) + (exp_ratio * 15))

    explain_prompt = f"""
You are evaluating candidate-job fit for recruiters.
Provide valid JSON only:
{{
  "match_score_adjustment": -10 to 10,
  "explanation": "2-3 bullet style sentences with concrete reasons"
}}

JD summary: {jd_data.get("summary")}
Role: {jd_data.get("role")}
Candidate: {candidate}
Matched must-have skills: {matched_must}
Missing must-have skills: {missing_must}
Matched nice-to-have skills: {matched_nice}
Base match score: {base_match}
"""

    explain_json = safe_model_json(
        explain_prompt,
        {"match_score_adjustment": 0, "explanation": "Rule-based match evaluation generated."},
    )
    adjustment = int(explain_json.get("match_score_adjustment", 0))
    final_match = clamp_score(base_match + adjustment)

    explainability = {
        "matched_must_have": matched_must,
        "missing_must_have": missing_must,
        "matched_nice_to_have": matched_nice,
        "base_match_score": base_match,
        "llm_adjustment": adjustment,
        "reason": explain_json.get("explanation", "No explanation returned."),
    }
    return final_match, explainability


def simulate_outreach_and_interest(jd_data, candidate):
    prompt = f"""
Simulate a short recruiter outreach conversation (4 turns total, Recruiter/Candidate alternating)
for this role and candidate profile.
Then return valid JSON only:
{{
  "interest_score": 0-100,
  "interest_reason": "short reason",
  "conversation": [
    "Recruiter: ...",
    "Candidate: ...",
    "Recruiter: ...",
    "Candidate: ..."
  ]
}}

Role: {jd_data.get("role")}
Location: {jd_data.get("location")}
Candidate profile: {candidate}
"""
    fallback = {
        "interest_score": 55,
        "interest_reason": "Neutral simulated interest due to unavailable model response.",
        "conversation": [
            "Recruiter: We have a role that aligns with your profile. Interested in a quick chat?",
            "Candidate: I am open to hearing details.",
            "Recruiter: Great. It involves strong ownership and hands-on execution.",
            "Candidate: Sounds promising. Please share full details and timeline.",
        ],
    }
    payload = safe_model_json(prompt, fallback)
    payload["interest_score"] = clamp_score(payload.get("interest_score", 55))
    payload["conversation"] = payload.get("conversation", fallback["conversation"])
    payload["interest_reason"] = payload.get("interest_reason", fallback["interest_reason"])
    return payload


# -----------------------------
# 🔐 API KEY + MODEL
# -----------------------------
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ API Key not found. Add GOOGLE_API_KEY to Streamlit secrets or local .env")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


# -----------------------------
# 🎛️ UI
# -----------------------------
st.title("🤖 TalentScout AI")
st.markdown("### AI-Powered Talent Scouting & Engagement Agent")
st.caption(
    "Paste a JD, discover best-fit candidates, simulate outreach, and get a ranked shortlist "
    "using Match Score + Interest Score."
)

st.sidebar.header("⚙️ Ranking Controls")
num_candidates = st.sidebar.slider("Shortlist size", 1, 8, 5)
match_weight_pct = st.sidebar.slider("Match Score weight (%)", 0, 100, 60, 5)
interest_weight_pct = 100 - match_weight_pct
st.sidebar.write(f"Interest Score weight: **{interest_weight_pct}%**")

jd = st.text_area("📄 Paste Job Description", height=220, placeholder="Enter full JD text...")

candidate_pool = [
    {
        "name": "Rahul N",
        "title": "ML Engineer",
        "skills": ["Python", "ML", "NLP", "Docker", "SQL"],
        "experience_years": 2,
        "location": "Bengaluru",
        "summary": "Built NLP APIs for customer support automation.",
    },
    {
        "name": "Anjali S",
        "title": "Backend Engineer",
        "skills": ["Java", "Spring", "Microservices", "AWS", "SQL"],
        "experience_years": 4,
        "location": "Hyderabad",
        "summary": "Owns backend services and performance tuning.",
    },
    {
        "name": "Kiran P",
        "title": "Data Scientist",
        "skills": ["Python", "Data Science", "SQL", "Pandas", "XGBoost"],
        "experience_years": 2,
        "location": "Remote",
        "summary": "Delivers forecasting and churn prediction models.",
    },
    {
        "name": "Sneha R",
        "title": "Frontend Engineer",
        "skills": ["React", "TypeScript", "JavaScript", "UI", "REST"],
        "experience_years": 3,
        "location": "Chennai",
        "summary": "Builds web apps with strong UX focus.",
    },
    {
        "name": "Arjun V",
        "title": "AI Engineer",
        "skills": ["Python", "Deep Learning", "Computer Vision", "PyTorch", "MLOps"],
        "experience_years": 5,
        "location": "Pune",
        "summary": "Productionized CV pipelines and model monitoring.",
    },
    {
        "name": "Meera T",
        "title": "Full Stack Engineer",
        "skills": ["Python", "React", "FastAPI", "PostgreSQL", "GCP"],
        "experience_years": 3,
        "location": "Remote",
        "summary": "Ships end-to-end features from API to UI.",
    },
    {
        "name": "Dev K",
        "title": "Data Engineer",
        "skills": ["Python", "Spark", "Airflow", "ETL", "AWS"],
        "experience_years": 4,
        "location": "Mumbai",
        "summary": "Designed scalable data pipelines for analytics.",
    },
    {
        "name": "Nisha A",
        "title": "Product Analyst",
        "skills": ["SQL", "Tableau", "A/B Testing", "Python", "Statistics"],
        "experience_years": 2,
        "location": "Bengaluru",
        "summary": "Supports product decisions with experimentation insights.",
    },
]

if st.button("🚀 Run Talent Scout Agent", type="primary"):
    if not jd.strip():
        st.warning("⚠️ Please paste a Job Description first.")
        st.stop()

    progress = st.progress(0, text="Parsing JD...")
    jd_data = parse_jd(jd)
    progress.progress(20, text="Discovering candidate pool...")

    discovered = discover_candidates(candidate_pool, jd_data, max_results=num_candidates)
    if not discovered:
        st.error("No candidates passed discovery filters. Try relaxing JD requirements.")
        st.stop()

    progress.progress(35, text="Running explainable match scoring...")
    results = []
    for idx, candidate in enumerate(discovered):
        match_score, explainability = score_match_with_explainability(jd_data, candidate)
        interest_payload = simulate_outreach_and_interest(jd_data, candidate)
        interest_score = interest_payload["interest_score"]

        final_score = clamp_score(
            (match_score * (match_weight_pct / 100.0))
            + (interest_score * (interest_weight_pct / 100.0))
        )

        results.append(
            {
                "name": candidate["name"],
                "title": candidate["title"],
                "location": candidate["location"],
                "match_score": match_score,
                "interest_score": interest_score,
                "final_score": final_score,
                "explainability": explainability,
                "interest_reason": interest_payload["interest_reason"],
                "conversation": interest_payload["conversation"],
                "candidate_summary": candidate["summary"],
            }
        )
        progress.progress(
            35 + int(((idx + 1) / len(discovered)) * 60),
            text=f"Scoring candidate {idx + 1}/{len(discovered)}...",
        )

    results.sort(key=lambda item: item["final_score"], reverse=True)
    progress.progress(100, text="Shortlist ready.")
    st.success("✅ Ranked shortlist generated successfully.")

    tab1, tab2, tab3 = st.tabs(["🏆 Ranked Shortlist", "🧠 JD Analysis", "📦 Discovery Pool"])

    with tab1:
        for rank, item in enumerate(results, start=1):
            st.markdown(f"### #{rank} {item['name']} — {item['title']} ({item['location']})")
            c1, c2, c3 = st.columns(3)
            c1.metric("Match Score", item["match_score"])
            c2.metric("Interest Score", item["interest_score"])
            c3.metric("Final Score", item["final_score"])
            st.caption(item["candidate_summary"])

            with st.expander("Why this candidate? (Explainability)"):
                exp = item["explainability"]
                st.write("**Matched must-have skills:**", exp["matched_must_have"] or "None")
                st.write("**Missing must-have skills:**", exp["missing_must_have"] or "None")
                st.write("**Matched nice-to-have skills:**", exp["matched_nice_to_have"] or "None")
                st.write("**Reasoning:**", exp["reason"])

            with st.expander("Simulated outreach conversation"):
                for turn in item["conversation"]:
                    st.write(turn)
                st.write("**Interest rationale:**", item["interest_reason"])

            st.markdown("---")

    with tab2:
        st.subheader("Extracted JD Insights")
        st.json(jd_data)

    with tab3:
        st.subheader("Candidates that passed discovery stage")
        st.json(discovered)