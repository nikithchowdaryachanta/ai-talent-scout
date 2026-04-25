# TalentScout AI — release notes

## Recent improvements — April 2026

*Reliability, transparency, and recruiter-facing polish.*

The application has been refined for **accuracy, consistency, and professional usability** across the pipeline. This file is the **single source of truth** for release notes: the Streamlit app loads it for the in-app **Release notes** expander, and the README points here so judges, contributors, and end users see one consistent story.

### Skill matching and scores

- Overlap ratios are computed **only** from actual JD requirements, so match percentages and on-screen explanations stay aligned. Inflated defaults when skill lists were missing have been removed.
- If the JD has **no** extracted skill lists, scoring falls back to **experience- and location-based** evaluation and does not introduce misleading skill signals.

### Trust safeguards

- Candidates with **zero** must-have skill overlap cannot receive an artificially boosted match score from a **positive** LLM adjustment to the headline match score.

### Parsing and discovery

- Parsing handles structured and semi-structured inputs more robustly, including **stringified JSON** skill arrays, with consistent **normalization and deduplication** for comparison.
- When skill requirements are absent from the parse, discovery uses an **experience-based** gate instead of assuming phantom skill overlap.

### Hybrid JD parsing (regex + model)

- **Labeled-line regex** runs before Gemini for **role**, **experience** (ranges, `N+`, min/max lines), **location**, **work mode** (normalized to Remote / Hybrid / On-site), **seniority**, **summary**, and **compensation**-style labels. **Regex values win on merge** so common templates are deterministic; the model still extracts skills and narrative.
- **Extended label aliases** (e.g. job location, reporting location, salary / TC / pay range) improve real-world JD coverage; the alias sets are easy to extend.
- **`compensation_summary`** is stored for **display and exports only** — not used in scoring.

### Transparency and exports

- **Parse data quality** banner (amber callout) when role, location, work mode, must-haves, or experience band look missing or placeholder-like — helps recruiters know when to refine the JD or use **JD coach**.
- **CSV** includes **`jd_compensation_summary`** (JD-level, repeated per candidate row for audit/ATS workflows) with **safe quoting** for commas, quotes, and newlines in cells.
- **PDF** shortlist report can show an italic **JD compensation** line under role context when present.

### UX and decisions

- **Shortlist size** control allows up to **30** candidates per run (default **10**) for larger JSON/PDF pools.
- **Recommended candidate** is shown prominently; **ranking and displayed final scores** use the same logic everywhere.
- Sidebar filters and in-tab skill chips use the **same matching rules** as JD-vs-profile skill comparison.
- **Soft pay context on roster** (sidebar toggle): shortlist cards get a **green** frame when a pay line was parsed from the JD, or an **amber + dim** treatment when none was — **no filtering**, full transparency.

### Interface and explainability

- Higher-contrast styling, **card-based** layouts, clear matched vs missing skill treatment, and **metric-style** score blocks for quick scanning.
- Explainability uses structured summary cards and expandable conversation views.
- **JD analysis** and the **discovery pool** are presented in clean, recruiter-friendly formats instead of raw data dumps in the default view.
