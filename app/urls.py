from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from typing import List
from model.model import CategoryResponse, FileTextsResponse, IncidentResponse, SearchResponse
from views import (
    root, incidents_root, documents_root, quick_response, metrics,
    health_check, get_all_categories, create_category, update_category,
    delete_category, create_file, delete_file, search_texts, get_texts_by_file,
    create_text_entries, update_text_entries, delete_text_batch, get_all_incidents,
    create_incident, update_incident, delete_incident, update_text_single, delete_text_single
)

api_router = APIRouter()
documents_api_router = APIRouter(prefix='/documents')
incidents_api_rooter = APIRouter(prefix='/incidents')

api_router.get("/", response_class=HTMLResponse, tags=["AI Chatbot"])(root)
api_router.post("/chat", tags=["AI Chatbot"])(quick_response)
api_router.get("/metrics", tags=["AI Chatbot"])(metrics)

documents_api_router.get("", response_class=HTMLResponse, tags=["Knowledge Base"])(documents_root)
documents_api_router.get("/health", tags=["Knowledge Base"])(health_check)
documents_api_router.get("/categories", response_model=List[CategoryResponse], tags=["Knowledge Base"])(get_all_categories)
documents_api_router.post("/categories", status_code=201, tags=["Knowledge Base"])(create_category)
documents_api_router.put("/categories/update", tags=["Knowledge Base"])(update_category)
documents_api_router.delete("/categories/{category_id}", tags=["Knowledge Base"])(delete_category)
documents_api_router.post("/files", status_code=201, tags=["Knowledge Base"])(create_file)
documents_api_router.delete("/files/{file_id}", tags=["Knowledge Base"])(delete_file)
documents_api_router.get("/files/{file_id}/texts", response_model=FileTextsResponse, tags=["Knowledge Base"])(get_texts_by_file)
documents_api_router.post("/files/{file_id}/texts", status_code=201, tags=["Knowledge Base"])(create_text_entries)
documents_api_router.get("/texts/search", response_model=SearchResponse, tags=["Knowledge Base"])(search_texts)
documents_api_router.put("/texts/update", tags=["Knowledge Base"])(update_text_entries)
documents_api_router.delete("/texts/batch", tags=["Knowledge Base"])(delete_text_batch)
documents_api_router.put("/texts/{text_id:path}", tags=["Knowledge Base"])(update_text_single)
documents_api_router.delete("/texts/{text_id:path}", tags=["Knowledge Base"])(delete_text_single)

incidents_api_rooter.get("", response_class=HTMLResponse, tags=["Incident Management System"])(incidents_root)
incidents_api_rooter.get("/list", response_model=List[IncidentResponse], tags=["Incident Management System"])(get_all_incidents)
incidents_api_rooter.post("/incident", status_code=201, tags=["Incident Management System"])(create_incident)
incidents_api_rooter.put("/incident/update", tags=["Incident Management System"])(update_incident)
incidents_api_rooter.delete("/incident", tags=["Incident Management System"])(delete_incident)