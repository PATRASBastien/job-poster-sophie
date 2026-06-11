# apply-jobs

Sophie gives you a list of jobs she wants to apply to. You execute every step yourself.

## Input

Sophie will provide job IDs (e.g. "apply to jobs 12, 34, 56") or reference the review CSV ("apply to the approved jobs in review/jobs_2024-01-15_0800.csv").

If she gives a CSV path, extract the IDs yourself:
```python
import csv, sys
sys.path.insert(0, ".")
ids = []
with open("<csv_path>", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if row.get("action","").strip().lower() in ("approve","approved"):
            ids.append(int(row["id"]))
print(ids)
```

## For each job ID, execute these steps in order

### Step 1 — Adapt CV and cover letter

Run this and capture the output directory:
```python
import sys; sys.path.insert(0,".")
from dotenv import load_dotenv; load_dotenv(".env")
from pipeline.adapter import adapt_for_job
result = adapt_for_job(<job_id>)
print(result["output_dir"])
print("score:", result.get("match_score"))
print("notes:", result.get("match_notes"))
```

Report the match score and notes to Sophie before continuing.

### Step 2 — Generate PDFs

```python
import sys; sys.path.insert(0,".")
from pathlib import Path
from pipeline.pdf_generator import generate_application_pdfs
cv_pdf, cl_pdf = generate_application_pdfs(Path("<output_dir>"))
print("CV PDF:", cv_pdf)
print("CL PDF:", cl_pdf)
```

### Step 3 — Read the email draft

```python
import json
from pathlib import Path
meta = json.loads(Path("<output_dir>/meta.json").read_text(encoding="utf-8"))
print("Subject:", meta.get("email_subject"))
print()
print(meta.get("email_body"))
```

Show Sophie the subject and body. Ask her to confirm or edit before sending.

### Step 4 — Get the recruiter email

First check the contacts table:
```python
import sys; sys.path.insert(0,".")
from pipeline.database import get_contacts
contacts = get_contacts(<job_id>)
for c in contacts:
    print(c["name"], c["email"])
```

If no email is found, ask Sophie: "What is the recruiter's email for \<Company\> — \<Title\>?"

### Step 5 — Send the email (or save draft)

```python
import sys; sys.path.insert(0,".")
from dotenv import load_dotenv; load_dotenv(".env")
from pathlib import Path
from pipeline.emailer import build_message, send, save_eml

msg = build_message(
    to="<recruiter_email>",
    subject="<subject>",
    body="""<body>""",
    cv_pdf=Path("<cv_pdf_path>"),
    cover_letter_pdf=Path("<cl_pdf_path>"),
)

sent = send(msg)
if sent:
    print("SENT")
else:
    eml = save_eml(msg, Path("<output_dir>"))
    print("DRAFT:", eml)
```

Tell Sophie whether the email was sent or where the `.eml` draft is saved.

### Step 6 — Record the application

```python
import sys; sys.path.insert(0,".")
from pipeline.tracker import record_application
record_application(
    job_id=<job_id>,
    cv_path="<cv_pdf_path>",
    cover_letter_path="<cl_pdf_path>",
    application_mode="email",   # or "manual" if no email sent
    notes="email_to=<recruiter_email> | subject: <subject>",
)
print("recorded")
```

Confirm to Sophie that the application is logged in `applications.csv`.

---

## After all jobs

Show Sophie a summary table:

| Job | Company | Sent to | Status |
|-----|---------|---------|--------|
| 12 | Acme Corp | hr@acme.com | sent |
| 34 | EU Agency | — | .eml draft |

---

## Notes

- If adaptation fails for a job, skip it, report the error, and continue with the next.
- If the PDF already exists in the output folder, skip regeneration.
- If Sophie has already applied to a job (status = applied in DB), warn her and ask whether to reapply.
- The `.eml` draft can be opened in Outlook or any email client and sent manually.
- SMTP auto-send requires `SMTP_PASSWORD` in `.env`. Without it, drafts are saved.
