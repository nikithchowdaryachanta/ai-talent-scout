# TalentScout AI — release notes

## Recent improvements — April 2026

*Reliability, transparency, and recruiter-facing polish.*

The application has been refined for **accuracy, consistency, and professional usability** across the pipeline. This file is the **single source of truth** for release notes: the Streamlit app loads it for the in-app **Release notes** expander, and the README points here so judges and users always see the same story.

### Skill matching and scores

- Overlap ratios are computed **only** from actual JD requirements, so match percentages and on-screen explanations stay aligned. Inflated defaults when skill lists were missing have been removed.
- If the JD has **no** extracted skill lists, scoring falls back to **experience- and location-based** evaluation and does not introduce misleading skill signals.

### Trust safeguards

- Candidates with **zero** must-have skill overlap cannot receive an artificially boosted match score from a **positive** LLM adjustment to the headline match score.

### Parsing and discovery

- Parsing handles structured and semi-structured inputs more robustly, including **stringified JSON** skill arrays, with consistent **normalization and deduplication** for comparison.
- When skill requirements are absent from the parse, discovery uses an **experience-based** gate instead of assuming phantom skill overlap.

### UX and decisions

- **Recommended candidate** is shown prominently; **ranking and displayed final scores** use the same logic everywhere.
- Sidebar filters and in-tab skill chips use the **same matching rules** as JD-vs-profile skill comparison.

### Interface and explainability

- Higher-contrast styling, **card-based** layouts, clear matched vs missing skill treatment, and **metric-style** score blocks for quick scanning.
- Explainability uses structured summary cards and expandable conversation views.
- **JD analysis** and the **discovery pool** are presented in clean, recruiter-friendly formats instead of raw data dumps in the default view.
