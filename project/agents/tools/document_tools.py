"""Tool File For Document Processing"""

# import PyPDF2
# from python_docx import Document

import os
import json
from pathlib import Path
from typing import Any
import pandas as pd
# from pypdf import PdfReader, PdfWriter
from PyPDF2 import PdfReader, PdfWriter
from docx import Document as DocxDocument
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings

def _read_document(file):
    if file.endswith('.pdf'):
        with open(file, 'rb') as pdf_doc:
            pdf_reader = PyPDF2.PdfFileReader(pdf_doc)
            text = ""
            for page in range(pdf_reader.numPages):
                text += pdf_reader.getPage(page).extractText()
            return text

    elif file.endswith('.docx'):
        doc = DocxDocument(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    else:
        return "Unsupported file format"


# Directory where generated files are saved for frontend download serving
EXPORT_DIR = (Path(settings.MEDIA_ROOT) / "agent_exports").resolve()
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_document(file_path: str, max_chars: int = 15000) -> str:
    """
    Reads and extracts text from .pdf, .docx, .csv, .xlsx, .json, .py, .md, or .txt files.
    Note: Legacy binary .doc files should be converted to .docx first.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found at '{file_path}'."

    ext = path.suffix.lower()

    try:
        if ext == ".pdf":
            reader = PdfReader(str(path))
            pages = [f"--- Page {i+1} ---\n{page.extract_text() or ''}" for i, page in enumerate(reader.pages)]
            content = "\n".join(pages)

        elif ext == ".docx":
            doc = DocxDocument(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            tables = []
            for t_idx, table in enumerate(doc.tables, 1):
                rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
                tables.append(f"\n[Table {t_idx}]\n" + "\n".join(rows))
            content = "\n".join(paragraphs) + "\n".join(tables)

        elif ext in [".csv", ".xlsx", ".xls"]:
            df = pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)
            content = df.to_markdown(index=False)

        elif ext == ".doc":
            return "Error: Legacy .doc binary format detected. Please convert to .docx using LibreOffice first."

        else:
            # Handles .txt, .py, .js, .json, .md, .html, .log, etc.
            content = path.read_text(encoding="utf-8", errors="replace")

        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n...[Truncated: Total length {len(content)} characters]"
        return content or "File is empty or contains no extractable text."

    except Exception as e:
        return f"Failed to read '{path.name}': {str(e)}"


def analyze_document(file_path: str) -> str:
    """
    Inspects a file and returns structural metadata, statistics, column summaries, 
    or code/text metrics to help the agent analyze the file.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found at '{file_path}'."

    ext = path.suffix.lower()
    stats: dict[str, Any] = {
        "file_name": path.name,
        "extension": ext,
        "size_kb": round(path.stat().st_size / 1024, 2),
    }

    try:
        if ext in [".csv", ".xlsx", ".xls"]:
            df = pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)
            stats["rows"] = len(df)
            stats["columns"] = list(df.columns)
            stats["missing_values"] = df.isnull().sum().to_dict()
            stats["numeric_summary"] = df.describe().to_dict()

        elif ext == ".pdf":
            reader = PdfReader(str(path))
            stats["page_count"] = len(reader.pages)
            stats["metadata"] = dict(reader.metadata) if reader.metadata else {}

        elif ext == ".docx":
            doc = DocxDocument(str(path))
            stats["paragraph_count"] = len(doc.paragraphs)
            stats["table_count"] = len(doc.tables)

        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            stats["line_count"] = len(lines)
            stats["word_count"] = len(text.split())
            stats["char_count"] = len(text)

        return json.dumps(stats, indent=2, default=str)

    except Exception as e:
        return f"Analysis failed for '{path.name}': {str(e)}"


def create_document(
    filename: str,
    file_format: str,
    content: str | list[dict[str, Any]],
    title: str = "Generated Document"
) -> str:
    """
    Creates a downloadable file (.pdf, .docx, .xlsx, .csv, .txt, .py, .md) in the export folder.
    - For .pdf, .docx, .txt, .py, .md: pass 'content' as a string.
    - For .csv or .xlsx: pass 'content' as a list of dictionaries (JSON rows) or CSV string.
    Returns a JSON payload with the file path and download URL for the frontend.
    """
    fmt = file_format.lower().lstrip(".")
    safe_name = Path(filename).stem + f".{fmt}"
    output_path = EXPORT_DIR / safe_name

    try:
        if fmt == "docx":
            doc = DocxDocument()
            doc.add_heading(title, level=1)
            for block in str(content).split("\n\n"):
                if block.strip():
                    doc.add_paragraph(block.strip())
            doc.save(str(output_path))

        elif fmt == "pdf":
            pdf = SimpleDocTemplate(str(output_path), pagesize=letter)
            styles = getSampleStyleSheet()
            story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
            for block in str(content).split("\n\n"):
                if block.strip():
                    # Escape basic XML characters for ReportLab Paragraph
                    clean_block = block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(clean_block.replace("\n", "<br/>"), styles["Normal"]))
                    story.append(Spacer(1, 8))
            pdf.build(story)

        elif fmt in ["csv", "xlsx"]:
            if isinstance(content, list):
                df = pd.DataFrame(content)
            else:
                # Parse JSON string if LLM passed serialized list of dicts
                df = pd.DataFrame(json.loads(content))

            if fmt == "csv":
                df.to_csv(output_path, index=False)
            else:
                df.to_excel(output_path, index=False)

        else:
            # .txt, .py, .md, .json, .html, etc.
            output_path.write_text(str(content), encoding="utf-8")

        return json.dumps({
            "status": "success",
            "filename": safe_name,
            "local_path": str(output_path.resolve()),
            "download_url": f"/api/downloads/{safe_name}"
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def merge_pdfs(pdf_paths: list[str], output_filename: str) -> str:
    """Merges multiple PDF files into a single downloadable PDF."""
    safe_name = Path(output_filename).stem + ".pdf"
    output_path = EXPORT_DIR / safe_name

    try:
        writer = PdfWriter()
        for pdf_file in pdf_paths:
            if not Path(pdf_file).exists():
                return f"Error: File '{pdf_file}' does not exist."
            writer.append(pdf_file)

        with open(output_path, "wb") as f:
            writer.write(f)

        return json.dumps({
            "status": "success",
            "filename": safe_name,
            "local_path": str(output_path.resolve()),
            "download_url": f"/api/downloads/{safe_name}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})



# Example FastAPI Endpoint
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import FileResponse
# from pathlib import Path

# app = FastAPI()
# EXPORT_DIR = Path("./agent_exports").resolve()

# @app.get("/api/downloads/{filename}")
# async def download_generated_file(filename: str):
#     file_path = (EXPORT_DIR / filename).resolve()
#     # Prevent path traversal attacks
#     if not str(file_path).startswith(str(EXPORT_DIR)) or not file_path.is_file():
#         raise HTTPException(status_code=404, detail="File not found")
#     return FileResponse(path=file_path, filename=filename)





# import io
# import json
# from pathlib import Path
# from typing import Any
# import pandas as pd
# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image
# from docx import Document as DocxDocument
# from docx.shared import Inches, Pt, RGBColor
# from docx.enum.text import WD_ALIGN_PARAGRAPH
# from jinja2 import Environment, BaseLoader
# from weasyprint import HTML
# from django.conf import settings

# # Save generated files inside Django's MEDIA_ROOT for seamless URL serving
# EXPORT_SUBDIR = "agent_exports"
# EXPORT_DIR = Path(settings.MEDIA_ROOT) / EXPORT_SUBDIR
# EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# def _ocr_image(image_bytes: bytes) -> str:
#     """Runs Tesseract OCR on raw image bytes."""
#     img = Image.open(io.BytesIO(image_bytes))
#     return pytesseract.image_to_string(img)


# def read_document_with_ocr(file_path: str, max_chars: int = 18000) -> str:
#     """
#     Reads text from PDFs (with automatic OCR fallback for scanned pages),
#     images (.png, .jpg, .jpeg, .webp), .docx, .xlsx, .csv, and code/text files.
#     """
#     path = Path(file_path)
#     if not path.exists():
#         return f"Error: File not found at '{file_path}'."

#     ext = path.suffix.lower()

#     try:
#         # 1. Standalone Images -> Direct OCR
#         if ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
#             text = _ocr_image(path.read_bytes())
#             content = f"[OCR Extracted Text from {path.name}]\n{text.strip()}"

#         # 2. PDFs -> Native text extraction + automatic OCR fallback per page
#         elif ext == ".pdf":
#             doc = fitz.open(str(path))
#             pages_output = []
#             for idx, page in enumerate(doc, 1):
#                 native_text = page.get_text("text").strip()
#                 if len(native_text) > 30:
#                     pages_output.append(f"--- Page {idx} ---\n{native_text}")
#                 else:
#                     # Render page at 200 DPI and run OCR for scanned pages
#                     pix = page.get_pixmap(dpi=200)
#                     ocr_text = _ocr_image(pix.tobytes("png")).strip()
#                     pages_output.append(f"--- Page {idx} (OCR) ---\n{ocr_text}")
#             content = "\n\n".join(pages_output)

#         # 3. Word Documents (.docx)
#         elif ext == ".docx":
#             doc = DocxDocument(str(path))
#             paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
#             tables = []
#             for t_idx, table in enumerate(doc.tables, 1):
#                 rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
#                 tables.append(f"\n[Table {t_idx}]\n" + "\n".join(rows))
#             content = "\n".join(paragraphs) + "\n".join(tables)

#         # 4. Spreadsheets (.csv, .xlsx)
#         elif ext in [".csv", ".xlsx", ".xls"]:
#             df = pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)
#             content = df.to_markdown(index=False)

#         # 5. Plain Text & Code (.py, .txt, .json, .md, etc.)
#         else:
#             content = path.read_text(encoding="utf-8", errors="replace")

#         if len(content) > max_chars:
#             return content[:max_chars] + f"\n\n...[Truncated: Total {len(content)} chars]"
#         return content or "No readable text found."

#     except Exception as e:
#         return f"Failed to read '{path.name}': {str(e)}"


# # --- Custom Styled HTML Template for Branded PDFs ---
# REPORT_HTML_TEMPLATE = """
# <!DOCTYPE html>
# <html>
# <head>
# <meta charset="utf-8">
# <style>
#   @page { size: A4; margin: 2cm; }
#   body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.6; }
#   .header { border-bottom: 3px solid {{ accent_color }}; padding-bottom: 12px; margin-bottom: 24px; display: flex; justify-content: space-between; }
#   .brand { font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: {{ accent_color }}; font-weight: bold; }
#   h1 { font-size: 24px; margin: 6px 0 4px 0; color: #111827; }
#   .subtitle { font-size: 13px; color: #6b7280; }
#   .section { margin-bottom: 18px; }
#   h2 { font-size: 16px; color: {{ accent_color }}; border-left: 4px solid {{ accent_color }}; padding-left: 10px; margin-top: 20px; }
#   table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
#   th { background-color: {{ accent_color }}; color: #ffffff; text-align: left; padding: 8px 10px; }
#   td { border-bottom: 1px solid #e5e7eb; padding: 8px 10px; }
#   tr:nth-child(even) { background-color: #f9fafb; }
#   .footer { position: fixed; bottom: -1cm; left: 0; right: 0; text-align: center; font-size: 11px; color: #9ca3af; }
# </style>
# </head>
# <body>
#   <div class="header">
#     <div>
#       <div class="brand">{{ brand_name }}</div>
#       <h1>{{ title }}</h1>
#       {% if subtitle %}<div class="subtitle">{{ subtitle }}</div>{% endif %}
#     </div>
#   </div>

#   {% for sec in sections %}
#     <div class="section">
#       {% if sec.heading %}<h2>{{ sec.heading }}</h2>{% endif %}
#       {% if sec.body %}<p>{{ sec.body | replace('\n', '<br>') }}</p>{% endif %}
#       {% if sec.table %}
#         <table>
#           <thead>
#             <tr>{% for col in sec.table[0].keys() %}<th>{{ col }}</th>{% endfor %}</tr>
#           </thead>
#           <tbody>
#             {% for row in sec.table %}
#               <tr>{% for val in row.values() %}<td>{{ val }}</td>{% endfor %}</tr>
#             {% endfor %}
#           </tbody>
#         </table>
#       {% endif %}
#     </div>
#   {% endfor %}

#   <div class="footer">Generated automatically • Confidential</div>
# </body>
# </html>
# """


# def generate_styled_document(
#     filename: str,
#     file_format: str,
#     title: str,
#     sections: list[dict[str, Any]],
#     subtitle: str = "",
#     brand_name: str = "AI Research & Ops",
#     accent_color: str = "#2563eb"
# ) -> str:
#     """
#     Generates a professionally styled PDF or DOCX report with sections and optional data tables.
#     'sections' should be a list of dicts, e.g.:
#     [{"heading": "Summary", "body": "Text here...", "table": [{"Col1": "Val1", "Col2": "Val2"}]}]
#     Returns JSON with a Django download URL for the frontend.
#     """
#     fmt = file_format.lower().lstrip(".")
#     safe_name = f"{Path(filename).stem}.{fmt}"
#     output_path = EXPORT_DIR / safe_name

#     try:
#         if fmt == "pdf":
#             env = Environment(loader=BaseLoader(), autoescape=True)
#             template = env.from_string(REPORT_HTML_TEMPLATE)
#             rendered_html = template.render(
#                 title=title,
#                 subtitle=subtitle,
#                 brand_name=brand_name,
#                 accent_color=accent_color,
#                 sections=sections
#             )
#             HTML(string=rendered_html).write_pdf(str(output_path))

#         elif fmt == "docx":
#             doc = DocxDocument()
#             # Brand header
#             brand_p = doc.add_paragraph()
#             brand_run = brand_p.add_run(brand_name.upper())
#             brand_run.font.size = Pt(9)
#             brand_run.font.bold = True
#             brand_run.font.color.rgb = RGBColor(37, 99, 235)

#             # Title & Subtitle
#             doc.add_heading(title, level=0)
#             if subtitle:
#                 sub_p = doc.add_paragraph(subtitle)
#                 sub_p.runs[0].font.color.rgb = RGBColor(107, 114, 128)

#             # Content Sections & Styled Tables
#             for sec in sections:
#                 if sec.get("heading"):
#                     doc.add_heading(sec["heading"], level=1)
#                 if sec.get("body"):
#                     doc.add_paragraph(sec["body"])
#                 if sec.get("table") and isinstance(sec["table"], list) and len(sec["table"]) > 0:
#                     rows_data = sec["table"]
#                     cols = list(rows_data[0].keys())
#                     table = doc.add_table(rows=1, cols=len(cols))
#                     table.style = "Light Shading Accent 1"
#                     for i, col_name in enumerate(cols):
#                         table.rows[0].cells[i].text = str(col_name)
#                     for row_dict in rows_data:
#                         row_cells = table.add_row().cells
#                         for i, col_name in enumerate(cols):
#                             row_cells[i].text = str(row_dict.get(col_name, ""))

#             doc.save(str(output_path))

#         else:
#             return json.dumps({"status": "error", "message": "Supported styled formats: 'pdf' or 'docx'."})

#         # Build clean URL matching Django's download view
#         download_url = f"/api/agent/download/{safe_name}/"
#         return json.dumps({
#             "status": "success",
#             "filename": safe_name,
#             "download_url": download_url
#         })

#     except Exception as e:
#         return json.dumps({"status": "error", "message": str(e)})
