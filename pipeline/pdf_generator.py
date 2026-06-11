"""
PDF generator — converts a Markdown file to a styled PDF using Playwright + Chromium.
No extra system dependencies needed since Playwright is already installed.
"""

from pathlib import Path

import markdown2

# ── CSS templates ─────────────────────────────────────────────────────────────

_CV_CSS = """
@page { margin: 2cm 2.2cm; }
* { box-sizing: border-box; }
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1a1a1a;
}
h1 {
    font-size: 22pt;
    color: #0d2b55;
    margin: 0 0 2px 0;
    letter-spacing: 0.5px;
}
h2 {
    font-size: 12pt;
    color: #0d2b55;
    border-bottom: 2px solid #0d2b55;
    padding-bottom: 2px;
    margin-top: 18px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
h3 { font-size: 10.5pt; margin: 10px 0 2px 0; }
p  { margin: 3px 0 6px 0; }
ul { margin: 3px 0 6px 16px; padding: 0; }
li { margin-bottom: 2px; }
a  { color: #0d2b55; text-decoration: none; }
hr { border: none; border-top: 1px solid #ccc; margin: 12px 0; }
table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
td, th { padding: 3px 8px; font-size: 10pt; }
strong { font-weight: bold; }
em { font-style: italic; color: #444; }
"""

_COVER_LETTER_CSS = """
@page { margin: 3cm 2.5cm; }
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    line-height: 1.65;
    color: #1a1a1a;
}
p  { margin: 0 0 14px 0; }
strong { font-weight: bold; }
h1, h2, h3 { display: none; }   /* template headers — hide in final PDF */
hr { border: none; border-top: 1px solid #ccc; margin: 16px 0; }
"""


def _md_to_html(md_text: str, css: str) -> str:
    body = markdown2.markdown(md_text, extras=["tables", "fenced-code-blocks"])
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>{body}</body>
</html>"""


def markdown_to_pdf(md_path: Path, output_path: Path, is_cv: bool = True) -> Path:
    """
    Convert a Markdown file to a PDF.
    Uses Playwright + Chromium (already installed).
    Returns the output path.
    """
    from playwright.sync_api import sync_playwright

    md_text = md_path.read_text(encoding="utf-8")
    css     = _CV_CSS if is_cv else _COVER_LETTER_CSS
    html    = _md_to_html(md_text, css)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page    = browser.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
        )
        browser.close()

    return output_path


def generate_application_pdfs(out_dir: Path) -> tuple[Path, Path]:
    """
    Generate cv_adapted.pdf and cover_letter.pdf from the .md files in out_dir.
    Returns (cv_pdf_path, cl_pdf_path).
    """
    cv_pdf = markdown_to_pdf(out_dir / "cv_adapted.md",    out_dir / "cv_adapted.pdf",    is_cv=True)
    cl_pdf = markdown_to_pdf(out_dir / "cover_letter.md",  out_dir / "cover_letter.pdf",  is_cv=False)
    return cv_pdf, cl_pdf
