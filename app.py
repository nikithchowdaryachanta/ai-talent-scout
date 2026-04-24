import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re

# -----------------------------
# 🔐 Load API Key (LOCAL + CLOUD)
# -----------------------------
try:
    api_key = st.secrets["GOOGLE_API_KEY"]  # Streamlit Cloud
except:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")   # Local

if not api_key:
    st.error("❌ API Key not found. Check .env or Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-pro")

# -----------------------------
# 🎨 UI CONFIG
# -----------------------------
st.set_page_config(page_title="TalentScout AI", page_icon="🤖", layout="wide")

st.title("🤖 TalentScout AI")
st.markdown("### AI-Powered Talent Scouting & Engagement Agent")

# -----------------------------
# 📌 SIDEBAR
# -----------------------------
st.sidebar.header("⚙️ Settings")
num_candidates = st.sidebar.slider("Number of Candidates", 1, 5, 3)

# -----------------------------
# 📄 JD INPUT
# -----------------------------
jd = st.text_area("📄 Paste Job Description", height=180)

# -----------------------------
# 👥 MOCK CANDIDATES
# -----------------------------
all_candidates = [
    {"name": "Rahul", "skills": "Python, ML, NLP", "experience": "2 years"},
    {"name": "Anjali", "skills": "Java, Backend, Spring", "experience": "3 years"},
    {"name": "Kiran", "skills": "Python, Data Science, SQL", "experience": "1 year"},
    {"name": "Sneha", "skills": "React, JS, Frontend", "experience": "2 years"},
    {"name": "Arjun", "skills": "Python, Deep Learning, CV", "experience": "3 years"},
]

candidates = all_candidates[:num_candidates]

# -----------------------------
# 🧠 FUNCTIONS
# -----------------------------
def parse_jd(jd):
    prompt = f"""
    Extract structured info from this JD:

    {jd}

    Return JSON:
    {{
      "role": "",
      "skills": [],
      "experience": "",
      "location": ""
    }}
    """
    res = model.generate_content(prompt)

    try:
        return json.loads(res.text)
    except:
        return {"raw_output": res.text}


def get_match_score(jd, c):
    prompt = f"""
    Compare JD and candidate.

    JD: {jd}
    Candidate: {c}

    Output:
    Match Score: <0-100>
    Reason: <short explanation>
    """
    return model.generate_content(prompt).text


def get_interest_score(c):
    prompt = f"""
    Simulate recruiter conversation:

    Recruiter: Are you interested in this role?
    Candidate: ...

    Then return:
    Interest Score: <0-100>
    Reason: <short explanation>

    Candidate:
    {c}
    """
    return model.generate_content(prompt).text


def extract_score(text):
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else 0


# -----------------------------
# 🚀 RUN AGENT
# -----------------------------
if st.button("🚀 Scout Candidates"):

    if not jd.strip():
        st.warning("⚠️ Please enter a Job Description")
        st.stop()

    st.info("Running AI pipeline...")
    progress = st.progress(0)

    # STEP 1: JD Parse
    jd_data = parse_jd(jd)
    progress.progress(20)

    results = []

    for i, c in enumerate(candidates):
        match_text = get_match_score(jd, c)
        interest_text = get_interest_score(c)

        match_score = extract_score(match_text)
        interest_score = extract_score(interest_text)

        final_score = 0.55 * match_score + 0.45 * interest_score

        results.append({
            "name": c["name"],
            "match": match_score,
            "interest": interest_score,
            "final": final_score,
            "match_text": match_text,
            "interest_text": interest_text
        })

        progress.progress(40 + int((i+1)/len(candidates)*50))

    results = sorted(results, key=lambda x: x["final"], reverse=True)

    progress.progress(100)
    st.success("✅ Candidates Ranked Successfully")

    # -----------------------------
    # 📑 TABS
    # -----------------------------
    tab1, tab2 = st.tabs(["🏆 Results", "🧠 JD Analysis"])

    # -----------------------------
    # 🏆 RESULTS
    # -----------------------------
    with tab1:
        for i, r in enumerate(results):
            st.markdown(f"## 🏆 Rank #{i+1}: {r['name']}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Match Score", r["match"])
            col2.metric("Interest Score", r["interest"])
            col3.metric("Final Score", round(r["final"], 2))

            with st.expander("📊 View Details"):
                st.write("### Match Explanation")
                st.write(r["match_text"])

                st.write("### Conversation Simulation")
                st.code(r["interest_text"])

            st.markdown("---")

    # -----------------------------
    # 🧠 JD ANALYSIS
    # -----------------------------
    with tab2:
        st.subheader("Extracted JD Insights")
        st.json(jd_data)