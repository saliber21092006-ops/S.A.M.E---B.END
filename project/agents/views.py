from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET

EXPORT_DIR = (Path(settings.MEDIA_ROOT) / "agent_exports").resolve()

@require_GET
def download_agent_document(request, filename: str):
    file_path = (EXPORT_DIR / filename).resolve()

    # Security check: block directory traversal (e.g., ../../settings.py)
    if not str(file_path).startswith(str(EXPORT_DIR)) or not file_path.is_file():
        raise Http404("Requested document does not exist.")

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=file_path.name
    )
