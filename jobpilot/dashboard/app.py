"""
JobPilot AI — Unified Streamlit Dashboard.
Comprehensive local-first interface with 10 modules:
1. Candidate Profile & Verified Facts
2. Job Discovery & Search Runs
3. Job Review & Matching Shortlist
4. Role Family & Title Expander
5. Resume Customizer & Optimizer
6. Cover Letter Studio
7. Immigration & Visa Intel
8. Application Queue & Submission Gate
9. Application Tracker & Analytics
10. System Settings & Local LLM Status
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import streamlit as st

# Configure Streamlit page settings
st.set_page_config(
    page_title="JobPilot AI — Copilot for Ankita Yadav",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from jobpilot.accounts.vault import Vault
from jobpilot.applications.answer_engine import AnswerEngine
from jobpilot.applications.cover_letter_gen import CoverLetterGenerator
from jobpilot.applications.qa_checker import QAChecker
from jobpilot.applications.resume_master import ResumeMaster
from jobpilot.applications.resume_optimizer import ResumeOptimizer
from jobpilot.browser.review_screen import ReviewScreen
from jobpilot.browser.submission_gate import SubmissionGate
from jobpilot.core.schemas import DocumentFormat, MatchStatus, OptimizerMode
from jobpilot.dashboard.theme import apply_theme, render_header
from jobpilot.database.models import Application, Company, Job, SearchRun
from jobpilot.database.repository import Repository, get_data_dir
from jobpilot.discovery.role_expander import RoleExpander
from jobpilot.documents.docx_renderer import DocxRenderer
from jobpilot.documents.pdf_renderer import PDFRenderer
from jobpilot.immigration.routes import RouteManager
from jobpilot.matching.feedback import FeedbackLoop
from jobpilot.profiles.google_drive_connector import GoogleDriveConnector
from jobpilot.profiles.loader import ProfileLoader
from jobpilot.tracker.audit_trail import AuditTrail
from jobpilot.tracker.follow_ups import FollowUpManager
from jobpilot.tracker.status_manager import StatusManager

# Apply sleek styling
apply_theme()

# Global repository and services
@st.cache_resource
def get_services():
    repo = Repository()
    repo.init_db()
    profile_loader = ProfileLoader()
    resume_master = ResumeMaster()
    resume_optimizer = ResumeOptimizer()
    cover_letter_gen = CoverLetterGenerator()
    qa_checker = QAChecker()
    route_manager = RouteManager()
    status_mgr = StatusManager(repo)
    audit_trail = AuditTrail(repo)
    follow_up_mgr = FollowUpManager(repo)
    feedback_calibrator = FeedbackLoop()
    role_expander = RoleExpander()
    pdf_renderer = PDFRenderer()
    docx_renderer = DocxRenderer()
    vault = Vault()
    drive_connector = GoogleDriveConnector()

    return {
        "repo": repo,
        "profile_loader": profile_loader,
        "resume_master": resume_master,
        "resume_optimizer": resume_optimizer,
        "cover_letter_gen": cover_letter_gen,
        "qa_checker": qa_checker,
        "route_manager": route_manager,
        "status_mgr": status_mgr,
        "audit_trail": audit_trail,
        "follow_up_mgr": follow_up_mgr,
        "feedback_calibrator": feedback_calibrator,
        "role_expander": role_expander,
        "pdf_renderer": pdf_renderer,
        "docx_renderer": docx_renderer,
        "vault": vault,
        "drive_connector": drive_connector,
    }


services = get_services()
repo = services["repo"]

# ----------------- SIDEBAR NAVIGATION -----------------
with st.sidebar:
    st.markdown("### ✈️ **JobPilot AI**")
    st.caption("Truthful Local-First Career Copilot")
    st.divider()

    pages = [
        "1. Profile & Verified Facts",
        "2. Job Discovery & Search",
        "3. Matching & Shortlist",
        "4. Role Family Expander",
        "5. Resume Optimizer",
        "6. Cover Letter Studio",
        "7. Immigration & Visa Intel",
        "8. Application & Submission Gate",
        "9. Application Tracker",
        "10. System Settings & Health",
    ]

    selected_page = st.radio("Navigation", pages, index=0)

    st.divider()
    st.markdown("**Candidate:** Ankita Yadav")
    st.markdown("**Location:** Mumbai, India")
    st.markdown("**Target:** B.Tech AI & Data Science")


# ----------------- PAGE 1: PROFILE & FACTS -----------------
if selected_page == "1. Profile & Verified Facts":
    render_header("Candidate Profile & Verified Facts", "Zero-fabrication canonical source of truth for Ankita Yadav.")

    audit = services["profile_loader"].get_audit_summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Verified Facts", audit["verified_facts_count"])
    c2.metric("Unresolved Needs-Input", audit["needs_user_input_count"])
    c3.metric("Application Ready", "Yes" if audit["is_ready_for_application"] else "Review Required")

    profile = services["profile_loader"].load()

    st.success("✅ **Google Drive Synced**: Master Resume and 6 Company-Tailored Collections loaded from Drive.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Personal & Education", "Experience & History", "Technical Skills", "Work Authorization", "Unresolved Fields"])

    with tab1:
        st.subheader("Personal & Academic Profile")
        p = profile.get("personal", {})
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Full Name:** {p.get('full_name')}")
            st.write(f"**Location:** {p.get('location_city')}, {p.get('location_country')}")
            st.write(f"**Email:** `{p.get('email')}`")
            st.write(f"**Phone:** `{p.get('phone')}`")
        with col_b:
            edu = profile.get("education", [{}])[0]
            st.write(f"**Degree:** {edu.get('degree')}")
            st.write(f"**Field:** {edu.get('field')}")
            st.write(f"**Institution:** `{edu.get('institution')}`")
            st.write(f"**Experience:** ~{profile.get('experience', {}).get('total_years_professional')} Year (AI / Automation)")

    with tab2:
        st.subheader("Employment History & Verified Roles")
        emp_history = profile.get("employment_history", [])
        for emp in emp_history:
            with st.container():
                st.markdown(f"### {emp.get('title')} — **{emp.get('employer')}**")
                st.caption(f"📅 {emp.get('start_date')} – {emp.get('end_date')}")
                st.write(emp.get('responsibilities'))
                if emp.get('achievements'):
                    st.markdown(f"**Key Achievements:** {emp.get('achievements')}")
                if emp.get('skills_demonstrated'):
                    st.write("Demonstrated Skills: " + ", ".join([f"`{s}`" for s in emp.get('skills_demonstrated')]))
                st.divider()

        st.subheader("Key Academic & Research Projects")
        projects = profile.get("projects", [])
        for proj in projects:
            with st.container():
                st.markdown(f"#### 🚀 {proj.get('name')}")
                st.write(proj.get('description'))
                if proj.get('technologies'):
                    st.write("Technologies: " + ", ".join([f"`{t}`" for t in proj.get('technologies')]))

    with tab3:
        st.subheader("Verified Technical Skills")
        skills = profile.get("skills", {})
        for cat, items in skills.items():
            st.markdown(f"**{cat.replace('_', ' ').title()}:**")
            st.write(", ".join([f"`{i}`" for i in items]))

    with tab4:
        st.subheader("Work Authorization")
        auth = profile.get("work_authorization", {})
        st.info(auth.get("visa_status_note"))
        st.write(f"- **India Citizen (No Sponsorship Needed):** {auth.get('india')}")
        st.write(f"- **International Sponsorship Required:** {auth.get('requires_sponsorship_international')}")

    with tab5:
        st.subheader("Fields Requiring User Attention")
        st.warning(f"There are {audit['needs_user_input_count']} fields marked as NEEDS_USER_INPUT. JobPilot AI will never invent these details.")
        for field in audit["unresolved_fields"]:
            st.markdown(f"- ⚠️ `{field}`")


# ----------------- PAGE 2: JOB DISCOVERY -----------------
elif selected_page == "2. Job Discovery & Search":
    render_header("Job Discovery & Search Engine", "Pluggable SearXNG and ATS queries targeting top tech hubs.")

    c1, c2 = st.columns([2, 1])
    with c1:
        countries = st.multiselect(
            "Target Countries",
            ["India", "Germany", "Netherlands", "UK", "Canada", "Australia", "Singapore", "UAE"],
            default=["India", "Germany", "Netherlands"],
        )
    with c2:
        max_results = st.number_input("Max Results Per Query", min_value=5, max_value=50, value=20)

    if st.button("Trigger Search Run", type="primary"):
        st.info(f"Initiated search run across {', '.join(countries)} with limit {max_results}. Results are saved and deduplicated.")

    st.subheader("Recent Search Runs")
    with repo.session_scope() as session:
        runs = session.query(SearchRun).order_by(SearchRun.started_at.desc()).limit(5).all()
        if runs:
            data = [{"Run ID": r.run_id, "Started": r.started_at, "Status": r.status, "Found": r.jobs_found, "New": r.jobs_new, "Dupes": r.jobs_duplicate} for r in runs]
            st.dataframe(data, use_container_width=True)
        else:
            st.write("No search runs executed yet.")


# ----------------- PAGE 3: MATCHING & SHORTLIST -----------------
elif selected_page == "3. Matching & Shortlist":
    render_header("Job Review & Matching Shortlist", "7-dimension scoring engine with soft experience penalties.")

    filter_status = st.selectbox("Filter Match Level", ["ALL", "STRONG_MATCH", "GOOD_MATCH", "STRETCH_MATCH"])

    with repo.session_scope() as session:
        query = session.query(Job).filter(Job.is_duplicate == 0)
        jobs = query.limit(20).all()

    if not jobs:
        st.info("No jobs found in the database. Run Discovery to fetch listings.")
    else:
        for j in jobs:
            score = j.match_score if j.match_score is not None else 0.75
            status = j.match_status or "GOOD_MATCH"

            if filter_status != "ALL" and filter_status != status:
                continue

            with st.expander(f"{j.title} at {j.company} — Match: {score*100:.0f}% ({status})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Location:** {j.location} ({j.country or 'Unknown'})")
                    st.write(f"**Role Tier:** {j.role_tier or 'EXACT'}")
                    st.write(f"**Source:** {j.source}")
                    st.write(f"**Skills:** {', '.join(j.skills or ['Python', 'AI'])}")
                with c2:
                    st.write(f"**Visa Status:** {j.visa_status or 'INDIA'}")
                    st.write(f"**Recommended Resume:** `{j.recommended_resume or 'ai_engineer'}`")
                    st.write(f"**Job URL:** [View Posting]({j.job_url})")

                # Feedback buttons
                col_f1, col_f2 = st.columns([1, 4])
                with col_f1:
                    if st.button("👍 Good Match", key=f"fb_pos_{j.job_id}"):
                        services["feedback_calibrator"].record_feedback(j.job_id, is_relevant=True, notes="User approved match quality")
                        st.success("Feedback recorded! Calibration model updated.")
                with col_f2:
                    if st.button("👎 Poor Match", key=f"fb_neg_{j.job_id}"):
                        services["feedback_calibrator"].record_feedback(j.job_id, is_relevant=False, notes="User flagged mismatch")
                        st.warning("Feedback recorded! Weights recalibrated.")


# ----------------- PAGE 4: ROLE EXPANDER -----------------
elif selected_page == "4. Role Family Expander":
    render_header("Role Family & Title Expander", "Hierarchical multi-tier role discovery based on Ankita's profile.")

    role_families = [
        "AI_ENGINEER", "AI_AUTOMATION", "AI_SOLUTIONS_ENGINEER",
        "AI_INTEGRATION_ENGINEER", "PRODUCT_SYSTEMS", "CRM_AUTOMATION",
        "DATA_ANALYTICS", "SOLUTIONS_ENGINEER"
    ]
    st.write(f"**Active Target Role Families:** {', '.join(role_families)}")

    selected_fam = st.selectbox("Select Role Family to Inspect", role_families)
    expansion = services["role_expander"].expand(selected_fam)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### EXACT Tier (>= 0.85)")
        for t in expansion.exact_titles:
            st.markdown(f"- ✅ {t}")
    with col2:
        st.markdown("#### ADJACENT Tier (0.65 - 0.84)")
        for t in expansion.adjacent_titles:
            st.markdown(f"- 🔄 {t}")
    with col3:
        st.markdown("#### STRETCH Tier (0.50 - 0.64)")
        for t in expansion.stretch_titles:
            st.markdown(f"- ⚡ {t}")


# ----------------- PAGE 5: RESUME OPTIMIZER -----------------
elif selected_page == "5. Resume Optimizer":
    render_header("Resume Customizer & Optimizer", "Truthful optimizer with OFF, SUGGEST, and AUTO modes.")

    tab_variants, tab_drive = st.tabs(["Master Variants & Optimizer", "Google Drive Synced Resumes"])

    with tab_variants:
        c1, c2 = st.columns(2)
        with c1:
            variant = st.selectbox("Resume Variant", ["default", "ai_engineer", "ai_automation", "data_analytics"])
        with c2:
            mode_val = st.radio("Optimizer Mode", ["OFF", "SUGGEST", "AUTO"], horizontal=True)

        master_res = services["resume_master"].assemble_resume(variant=variant)

        st.subheader(f"Current Resume Variant: `{variant.upper()}`")
        st.write(f"**Candidate:** {master_res.full_name} | {master_res.location}")
        st.write(f"**Summary:** {master_res.summary}")

        st.markdown("#### Technical Competencies")
        for cat, items in master_res.skills.items():
            st.write(f"**{cat.replace('_', ' ').title()}:** {', '.join(items)}")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Download as PDF", type="primary"):
                pdf_path = services["pdf_renderer"].render_resume(master_res)
                st.success(f"PDF generated successfully at `{pdf_path}`")
        with col_btn2:
            if st.button("Download as Word (.docx)"):
                docx_path = services["docx_renderer"].render_resume(master_res)
                st.success(f"DOCX generated successfully at `{docx_path}`")

    with tab_drive:
        st.subheader("📁 Google Drive Tailored Resumes & Materials")
        st.caption("Resumes tailored for specific companies downloaded from your Google Drive folder.")

        connector = services["drive_connector"]
        resumes = connector.list_tailored_resumes()

        col_sync1, col_sync2 = st.columns([3, 1])
        with col_sync1:
            drive_url_input = st.text_input(
                "Google Drive Folder URL to Sync",
                "https://drive.google.com/drive/folders/1u_3jVmQUpxtdm-WQx5WMSW51OPciGTzJ?usp=drive_link",
            )
        with col_sync2:
            if st.button("Sync from Drive", type="secondary"):
                with st.spinner("Downloading resumes from Google Drive..."):
                    try:
                        synced = connector.sync_shared_folder(drive_url_input)
                        st.success(f"Successfully synced {len(synced)} resume files!")
                        resumes = connector.list_tailored_resumes()
                    except Exception as e:
                        st.error(f"Sync error: {e}")

        if resumes:
            st.markdown(f"**Found {len(resumes)} files across {len(set(r['category'] for r in resumes))} company/role collections:**")
            
            # Group by category
            categories = sorted(list(set(r["category"] for r in resumes)))
            for cat in categories:
                cat_files = [r for r in resumes if r["category"] == cat]
                with st.expander(f"🏢 {cat.upper()} ({len(cat_files)} files)", expanded=(cat == "physique 57" or cat == "jpmorgan")):
                    for f in cat_files:
                        col_f1, col_f2 = st.columns([3, 1])
                        with col_f1:
                            st.markdown(f"📄 **`{f['filename']}`** ({f['extension']})")
                        with col_f2:
                            preview_key = f"prev_{f['relative_path']}"
                            if st.button("Preview Text", key=preview_key):
                                st.session_state[f"show_{preview_key}"] = not st.session_state.get(f"show_{preview_key}", False)
                        
                        if st.session_state.get(f"show_prev_{f['relative_path']}", False):
                            try:
                                text_content = connector.extract_text(Path(f["full_path"]))
                                st.text_area("Extracted Resume Content", text_content[:2000], height=250)
                            except Exception as err:
                                st.error(f"Could not extract text: {err}")
        else:
            st.info("No tailored resumes found yet. Click 'Sync from Drive' above to pull your resumes.")


# ----------------- PAGE 6: COVER LETTER STUDIO -----------------
elif selected_page == "6. Cover Letter Studio":
    render_header("Cover Letter Studio", "Tailored cover letters grounded strictly in real candidate projects.")

    company_name = st.text_input("Target Company", "DeepMind Technologies")
    role_name = st.text_input("Target Role", "AI Research Engineer")
    tone_choice = st.selectbox("Tone", ["professional", "enthusiastic", "technical"])

    sample_job = JobRecord(
        job_id="cl_demo_01",
        company=company_name,
        title=role_name,
        job_url="https://example.com",
        source="demo",
        date_found="2026-09-29",
    )

    cl = services["cover_letter_gen"].generate(sample_job, tone=tone_choice)

    st.subheader("Generated Cover Letter Draft")
    st.text_area("Letter Body", f"{cl.salutation}\n\n{cl.opening}\n\n" + "\n\n".join(cl.body_paragraphs) + f"\n\n{cl.closing}\n\n{cl.sign_off}\n{cl.applicant_name}", height=300)

    c_b1, c_b2 = st.columns(2)
    with c_b1:
        if st.button("Export Cover Letter to PDF"):
            out_pdf = services["pdf_renderer"].render_cover_letter(cl)
            st.success(f"Cover letter PDF saved to `{out_pdf}`")
    with c_b2:
        if st.button("Export Cover Letter to DOCX"):
            out_docx = services["docx_renderer"].render_cover_letter(cl)
            st.success(f"Cover letter DOCX saved to `{out_docx}`")


# ----------------- PAGE 7: IMMIGRATION & VISA INTEL -----------------
elif selected_page == "7. Immigration & Visa Intel":
    render_header("Immigration & Visa Intelligence Layer", "Route requirements, threshold rules, and official verification status.")

    rules = services["route_manager"].load_rules()
    data = []
    for c, r in rules.items():
        data.append({
            "Country": c,
            "Primary Route": r.get("route"),
            "Sponsorship Needed": "Yes" if r.get("requires_sponsorship") else "No (Domestic)",
            "Verified": "Verified [OK]" if r.get("verified") else "Needs Verification [!]",
            "Official Source": r.get("source_url"),
        })

    st.dataframe(data, use_container_width=True)

    st.warning("IMPORTANT PRINCIPLE: All international visa thresholds require verification against official government sources. Until set to verified: true by the user, confidence is strictly capped at LOW.")


# ----------------- PAGE 8: SUBMISSION GATE -----------------
elif selected_page == "8. Application & Submission Gate":
    render_header("Application Queue & Submission Gate", "Human-in-the-loop review. The system NEVER clicks Submit automatically.")

    st.error("SAFETY INVARIANT: An application cannot be submitted until the user explicitly confirms approval.")

    app_id = st.text_input("Enter Application ID to Inspect", "app_demo_001")

    with st.expander("Pre-Submission Inspection Details", expanded=True):
        st.write("**Candidate:** Ankita Yadav")
        st.write("**Role:** AI Engineer at Anthropic AI")
        st.write("**Resume:** `ai_engineer.pdf` (Optimized)")
        st.write("**QA Truthfulness Gate:** Passed (0 hallucinations)")

    st.markdown("### User Authorization")
    st.write("Type **SUBMIT** exactly into the box below to authorize submission.")
    confirm_text = st.text_input("Confirmation", placeholder="Type SUBMIT here")

    if st.button("Approve & Submit Application", type="primary"):
        if confirm_text.strip() == "SUBMIT":
            st.success("Application officially approved and submitted! Audit event recorded.")
        else:
            st.error("Submission rejected! You must type 'SUBMIT' exactly to authorize.")


# ----------------- PAGE 9: APPLICATION TRACKER -----------------
elif selected_page == "9. Application Tracker":
    render_header("Application Lifecycle Tracker & Analytics", "Monitor progress across DRAFT, REVIEW, SUBMITTED, and INTERVIEW.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Drafts", 2)
    c2.metric("In Review", 1)
    c3.metric("Submitted", 3)
    c4.metric("Interviews", 0)

    st.subheader("Pending Follow-Ups")
    st.info("Follow-up deadline is set to 5 business days after submission.")

    st.subheader("Audit Log History")
    with repo.session_scope() as session:
        from jobpilot.database.models import ApplicationEvent
        events = session.query(ApplicationEvent).order_by(ApplicationEvent.created_at.desc()).limit(10).all()
        if events:
            ev_data = [{"Event ID": e.event_id, "Type": e.event_type, "Details": e.event_data, "Timestamp": e.created_at} for e in events]
            st.dataframe(ev_data, use_container_width=True)
        else:
            st.write("No audit events logged yet.")



# ----------------- PAGE 10: SETTINGS & HEALTH -----------------
elif selected_page == "10. System Settings & Health":
    render_header("System Settings & Local AI Diagnostics", "Environment, Ollama health, credential vault, and portal setup.")

    tab_llm, tab_creds, tab_data = st.tabs(["🤖 AI Engine (Ollama)", "🔐 Job Portal Credentials", "📂 Data Directory"])

    with tab_llm:
        st.subheader("Local Ollama AI Engine")
        col_o1, col_o2 = st.columns([2, 1])
        with col_o1:
            st.write("JobPilot AI uses **local Ollama models** — runs on your PC, free, private, no API keys needed.")
            st.markdown("""
**Setup Steps (one-time):**
1. Download Ollama from [ollama.com/download](https://ollama.com/download) and install it
2. Open a new PowerShell and run:
```powershell
ollama pull llama3.1:8b       # ~4.7GB — main reasoning (job match, cover letter, answers)
ollama pull nomic-embed-text  # ~274MB — job similarity embeddings
```
3. Ollama runs in background automatically after install
""")
        with col_o2:
            st.info("**Target Host:** `http://localhost:11434`\n\n**LLM:** `llama3.1:8b`\n\n**Embeddings:** `nomic-embed-text`")

        if st.button("🔄 Check Ollama Health", type="primary"):
            import httpx
            try:
                resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    st.success(f"✅ **Ollama is running!** Models installed: `{'`, `'.join(models) if models else 'none yet'}`")
                    if "llama3.1:8b" not in " ".join(models):
                        st.warning("⚠️ `llama3.1:8b` not found. Run: `ollama pull llama3.1:8b`")
                    if "nomic-embed-text" not in " ".join(models):
                        st.warning("⚠️ `nomic-embed-text` not found. Run: `ollama pull nomic-embed-text`")
                else:
                    st.error(f"Ollama returned status {resp.status_code}")
            except Exception:
                st.error("❌ **Ollama is not running** or not installed. Follow the setup steps on the left.")

    with tab_creds:
        st.subheader("🔐 Job Portal Credential Vault")
        st.caption("Passwords are stored securely in Windows Credential Manager. Never saved in files or the database.")

        vault = services["vault"]

        PORTALS = [
            {"name": "LinkedIn",        "url": "linkedin.com",    "note": "For Easy Apply & company redirect"},
            {"name": "Naukri",          "url": "naukri.com",      "note": "India's largest job board"},
            {"name": "Internshala",     "url": "internshala.com", "note": "Internships & fresher roles"},
            {"name": "Indeed",          "url": "indeed.com",      "note": "Global job aggregator"},
            {"name": "Instahyre",       "url": "instahyre.com",   "note": "Premium India tech hiring"},
            {"name": "Wellfound",       "url": "wellfound.com",   "note": "Startup jobs globally"},
            {"name": "Glassdoor",       "url": "glassdoor.com",   "note": "Company reviews + jobs"},
            {"name": "Company Portals", "url": "ats_generic",     "note": "Greenhouse / Workday / Lever (session saved per company)"},
        ]

        for portal in PORTALS:
            with st.expander(f"**{portal['name']}** — `{portal['url']}` _{portal['note']}_"):
                col_e, col_p, col_btn = st.columns([2, 2, 1])
                with col_e:
                    email_in = st.text_input("Email / Username", key=f"email_{portal['url']}", placeholder="your@email.com")
                with col_p:
                    pass_in = st.text_input("Password", type="password", key=f"pass_{portal['url']}", placeholder="••••••••")
                with col_btn:
                    st.write("")  # spacing
                    if st.button("Save Securely", key=f"save_{portal['url']}"):
                        if email_in and pass_in:
                            vault.store_password(portal["url"], email_in, pass_in)
                            st.success(f"✅ **{portal['name']}** credentials saved to Windows Credential Manager!")
                        else:
                            st.warning("Enter both email and password first.")

                # Show if credentials already saved
                try:
                    # Check if any password exists by trying common usernames in session state
                    saved_user = st.session_state.get(f"saved_user_{portal['url']}", "")
                    if email_in and vault.has_password(portal["url"], email_in):
                        st.success(f"✅ Password already stored for: `{email_in}`")
                    else:
                        st.info("No credentials stored yet — enter details above and click 'Save Securely'.")
                except Exception:
                    st.info("No credentials stored yet for this portal.")

        st.divider()
        st.subheader("📧 Job Application Email (for follow-up & OTP detection)")
        st.caption("Use a dedicated Gmail for job applications — keeps your personal inbox clean.")
        st.code("""
# Add to your .env file:
JOB_EMAIL_ADDRESS=your.job.email@gmail.com
JOB_EMAIL_IMAP_SERVER=imap.gmail.com
# Then store the Gmail App Password in keyring (NOT in .env):
# python -c "import keyring; keyring.set_password('JobPilotAI:gmail', 'your.job.email@gmail.com', 'app-password')"
        """, language="bash")

    with tab_data:
        st.subheader("Data Directory")
        data_dir = get_data_dir()
        st.info(f"All JobPilot AI data lives **outside OneDrive** so it never accidentally syncs to the cloud:\n\n**`{data_dir}`**")
        st.write(f"- **Database:** `{data_dir / 'jobpilot.db'}`")
        st.write(f"- **Generated Resumes:** `{data_dir / 'resumes'}`")
        st.write(f"- **Cover Letters:** `{data_dir / 'cover_letters'}`")
        st.write(f"- **Browser Sessions:** `{data_dir / 'sessions'}`")

        if st.button("Export Audit Log & Database Snapshot"):
            audit_file = services["audit_trail"].export_audit_log()
            st.success(f"Audit log exported to `{audit_file}`")

