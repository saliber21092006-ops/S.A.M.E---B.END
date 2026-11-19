from django.urls import path
from .views import download_agent_document

urlpatterns = [
    path("api/agent/download/<str:filename>/", download_agent_document, name="agent_doc_download"),
]
