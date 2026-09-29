"""
ATS-Friendly HTML and CSS Document Templates for JobPilot AI.
Generates structured HTML representations of resumes and cover letters
optimized for maximum ATS machine-parseability and clean human readability.
"""

from typing import Dict, List, Optional
from jobpilot.core.schemas import CoverLetterDoc, ResumeDoc


def render_resume_html(resume: ResumeDoc) -> str:
    """
    Renders ResumeDoc into clean, ATS-compliant single-column HTML with inline CSS.
    """
    # Build skills HTML
    skills_html_parts = []
    for cat, items in resume.skills.items():
        if items:
            cat_title = cat.replace("_", " ").title()
            skills_html_parts.append(f"<p><strong>{cat_title}:</strong> {', '.join(items)}</p>")
    skills_html = "\n".join(skills_html_parts)

    # Build experience HTML
    exp_html_parts = []
    for exp in resume.experience:
        employer = exp.get("employer", "")
        title = exp.get("title", "")
        bullets = exp.get("bullets", [])
        if employer or title:
            exp_html_parts.append(f"<div class='item'>")
            exp_html_parts.append(f"<h3>{title} &mdash; <em>{employer}</em></h3>")
            if bullets:
                exp_html_parts.append("<ul>")
                for b in bullets:
                    exp_html_parts.append(f"<li>{b}</li>")
                exp_html_parts.append("</ul>")
            exp_html_parts.append("</div>")
    exp_html = "\n".join(exp_html_parts)

    # Build projects HTML
    proj_html_parts = []
    for proj in resume.projects:
        name = proj.get("name", "")
        bullets = proj.get("bullets", [])
        if name:
            proj_html_parts.append(f"<div class='item'>")
            proj_html_parts.append(f"<h3>{name}</h3>")
            if bullets:
                proj_html_parts.append("<ul>")
                for b in bullets:
                    proj_html_parts.append(f"<li>{b}</li>")
                proj_html_parts.append("</ul>")
            proj_html_parts.append("</div>")
    proj_html = "\n".join(proj_html_parts)

    # Build education HTML
    edu_html_parts = []
    for edu in resume.education:
        deg = edu.get("degree", "")
        field = edu.get("field", "")
        inst = edu.get("institution", "")
        yr = edu.get("graduation_year", "")
        line = f"<h3>{deg} in {field}</h3>"
        sub = []
        if inst and inst != "NEEDS_USER_INPUT":
            sub.append(inst)
        if yr and yr != "NEEDS_USER_INPUT":
            sub.append(str(yr))
        sub_str = f"<p class='subtitle'>{', '.join(sub)}</p>" if sub else ""
        edu_html_parts.append(f"<div class='item'>{line}{sub_str}</div>")
    edu_html = "\n".join(edu_html_parts)

    contact_items = [resume.location]
    if resume.contact_email and resume.contact_email != "NEEDS_USER_INPUT":
        contact_items.append(resume.contact_email)
    if resume.contact_phone and resume.contact_phone != "NEEDS_USER_INPUT":
        contact_items.append(resume.contact_phone)
    contact_line = " &bull; ".join(contact_items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{resume.full_name} - Resume</title>
<style>
  body {{
    font-family: Arial, Helvetica, sans-serif;
    color: #222;
    margin: 0;
    padding: 24px;
    font-size: 10.5pt;
    line-height: 1.4;
    background: #fff;
  }}
  .header {{
    text-align: center;
    border-bottom: 2px solid #2b5797;
    padding-bottom: 12px;
    margin-bottom: 16px;
  }}
  h1 {{
    margin: 0 0 6px 0;
    font-size: 22pt;
    color: #1a365d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .contact {{
    font-size: 9.5pt;
    color: #555;
  }}
  h2 {{
    font-size: 12pt;
    color: #2b5797;
    border-bottom: 1px solid #ddd;
    padding-bottom: 3px;
    margin: 14px 0 8px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  h3 {{
    font-size: 10.5pt;
    margin: 4px 0 2px 0;
    color: #222;
  }}
  p {{
    margin: 3px 0;
  }}
  ul {{
    margin: 4px 0 8px 20px;
    padding: 0;
  }}
  li {{
    margin-bottom: 3px;
  }}
  .item {{
    margin-bottom: 10px;
  }}
  .subtitle {{
    color: #555;
    font-style: italic;
    font-size: 9.5pt;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>{resume.full_name}</h1>
  <div class="contact">{contact_line}</div>
</div>

<h2>Professional Summary</h2>
<p>{resume.summary}</p>

<h2>Technical Competencies</h2>
{skills_html}

{f"<h2>Technical Experience</h2>{exp_html}" if exp_html else ""}

{f"<h2>Featured Projects</h2>{proj_html}" if proj_html else ""}

<h2>Education</h2>
{edu_html}
</body>
</html>
"""


def render_cover_letter_html(cover_letter: CoverLetterDoc) -> str:
    """
    Renders CoverLetterDoc into professional letter HTML format with inline CSS.
    """
    body_html = "\n".join([f"<p>{p}</p>" for p in cover_letter.body_paragraphs])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cover Letter - {cover_letter.applicant_name}</title>
<style>
  body {{
    font-family: Arial, Helvetica, sans-serif;
    color: #222;
    margin: 0;
    padding: 40px;
    font-size: 11pt;
    line-height: 1.5;
    background: #fff;
  }}
  .header {{
    margin-bottom: 24px;
    border-bottom: 2px solid #2b5797;
    padding-bottom: 12px;
  }}
  h1 {{
    margin: 0;
    font-size: 20pt;
    color: #1a365d;
  }}
  .salutation {{
    font-weight: bold;
    margin-bottom: 16px;
  }}
  p {{
    margin: 0 0 14px 0;
    text-align: justify;
  }}
  .sign-off {{
    margin-top: 24px;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>{cover_letter.applicant_name}</h1>
</div>

<div class="salutation">{cover_letter.salutation}</div>

<p>{cover_letter.opening}</p>

{body_html}

<p>{cover_letter.closing}</p>

<div class="sign-off">
  <p>{cover_letter.sign_off}<br><br><strong>{cover_letter.applicant_name}</strong></p>
</div>
</body>
</html>
"""
