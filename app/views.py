import json
import logging, time
from datetime import datetime
from typing import Union
from fastapi import Request, HTTPException, Depends
from fastapi.responses import Response, JSONResponse
from fastapi.templating import Jinja2Templates
from model.model import *
from language import identify_language
from chain import generate_answer
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from utils import execute_query, execute_single_query, execute_insert, execute_update, execute_delete, check_record_exists, check_database_health, DatabaseError
from vdb_utils import *
from documents_logger import documents_logger

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("chat_logs.log"),
        logging.StreamHandler()
    ]
)

# Метрики Prometheus
REQUEST_COUNT = Counter("request_count", "Total number of requests received")
ERROR_COUNT = Counter("error_count", "Total number of errors encountered")
RESPONSE_TIME = Histogram("response_time_seconds", "Time taken to generate response")

templates = Jinja2Templates(directory="templates")

def metrics():
    """
    GET method for "/metrics" web endpoint
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def root(request: Request):
    """
    GET method for default web endpoint
    """
    return templates.TemplateResponse("index.html", {"request": request})


def incidents_root(request: Request):
    """
    GET method for incidents page web endpoint
    """
    return templates.TemplateResponse(request=request, name="incident.html")


def documents_root(request: Request):
    """
    GET method for incidents page web endpoint
    """
    return templates.TemplateResponse(request=request, name="knowledge-base.html")


async def quick_response(request: QuestionRequest):
    """
    POST method for "/chat/" web endpoint
    """
    REQUEST_COUNT.inc()
    session_id = request.session_id if request.session_id else str(time.time())
    language = identify_language(request.question)
    logging.info(f"Language identified: {language}")

    try:
        start_time = time.perf_counter()
        with RESPONSE_TIME.time():
            response, db_time, api_time = generate_answer(request.question, session_id, language)
        execution_time = time.perf_counter() - start_time

        logging.info(
            f"Response generated in {execution_time:.3f} sec | "
            f"API: {api_time:.3f} sec | DB: {db_time:.3f} sec "
            f"for session_id={session_id}"
        )
        logging.info(f'Response: {response}')
        converted_response = json.loads(response)

        return {"response": f'Ответ: {converted_response["response"]}\n\nКатегория: {converted_response["category"]}', "session_id": session_id}
    except Exception as e:
        ERROR_COUNT.inc()
        logging.error(f"Error processing request: {e}", exc_info=True)
        return {"error": "Сервис недоступен. Попробуйте позже.", "details": str(e)}


async def check_db_health():
    """Dependency to ensure database connectivity before processing requests."""
    health = check_database_health()
    if health["status"] != "healthy":
        raise HTTPException(status_code=503, detail="Database is not available")


async def health_check():
    """Check the overall health of the application and database connectivity."""
    try:
        db_health = check_database_health()
        return {
            "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_health
        }
    except Exception as e:
        documents_logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


# ==================== CATEGORY ENDPOINTS ====================

async def get_all_categories(db_check=Depends(check_db_health)):
    """Retrieve all categories with their associated files."""
    try:
        query = """
            SELECT 
                c.category_id,
                c.category_name,
                f.file_id,
                f.file_name
            FROM categories c
            LEFT JOIN files f ON c.category_id = f.category_id
            ORDER BY c.category_name, f.file_name
        """
        
        results = execute_query(query)
        
        categories_dict = {}
        
        for row in results:
            category_id = row['category_id']
            
            if category_id not in categories_dict:
                categories_dict[category_id] = {
                    'category_id': category_id,
                    'category_name': row['category_name'],
                    'files': []
                }
            
            if row['file_id']:
                categories_dict[category_id]['files'].append({
                    'file_id': row['file_id'],
                    'file_name': row['file_name']
                })
        
        return list(categories_dict.values())
        
    except DatabaseError as e:
        documents_logger.error(f"Database error in get_all_categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")
    except Exception as e:
        documents_logger.error(f"Unexpected error in get_all_categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def create_category(category: CategoryCreate, db_check=Depends(check_db_health)):
    """Create a new category."""
    try:
        if check_record_exists('categories', 'category_name', category.category_name):
            raise HTTPException(
                status_code=409, 
                detail=f"Category '{category.category_name}' already exists"
            )
        
        query = """
            INSERT INTO categories (category_name) 
            VALUES (%s) 
            RETURNING category_id
        """
        
        category_id = execute_insert(query, (category.category_name,))
        
        documents_logger.info(f"Created category: {category.category_name} with ID: {category_id}")
        
        return {
            "message": "Category created successfully",
            "category_id": category_id,
            "category_name": category.category_name
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in create_category: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")
    except Exception as e:
        documents_logger.error(f"Unexpected error in create_category: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def update_category(category: CategoryUpdate, db_check=Depends(check_db_health)):
    """Update category"""
    try:
        if not check_record_exists('categories', 'category_id', category.category_id):
            raise HTTPException(
                status_code=409,
                detail=f"Category '{category.category_name}' doesn't exist"
            )
            
        query = """
            UPDATE categories
            SET category_name = %s
            WHERE category_id = %s 
            RETURNING category_id
        """
        
        category_id = execute_insert(query, (category.category_name, category.category_id,))
        
        documents_logger.info(f"Updated category with ID: {category_id}. New category name is {category.category_name}.")
        
        return {
            "message": "Category updated successfully",
            "category_id": category_id,
            "category_name": category.category_name
        }
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in create_category: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")
    except Exception as e:
        documents_logger.error(f"Unexpected error in create_category: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def delete_category(category_id: int, db_check=Depends(check_db_health)):
    """Delete a category and all its associated files and texts."""
    try:
        if not check_record_exists('categories', 'category_id', category_id):
            raise HTTPException(status_code=404, detail="Category not found")
        
        file_query = "SELECT file_name FROM files WHERE category_id = %s"
        files = execute_query(file_query, (category_id,))
        
        total_deleted_texts = 0
        for file_row in files:
            file_name = file_row['file_name']
            deleted_count = soft_delete_all_texts_for_file(file_name)
            total_deleted_texts += deleted_count
        
        delete_files_query = "DELETE FROM files WHERE category_id = %s"
        execute_delete(delete_files_query, (category_id,))
        
        delete_category_query = "DELETE FROM categories WHERE category_id = %s"
        deleted_count = execute_delete(delete_category_query, (category_id,))
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        
        documents_logger.info(f"Deleted category ID: {category_id} with {len(files)} files and {total_deleted_texts} text entries")
        
        return {
            "message": "Category and all associated data deleted successfully",
            "deleted_files_count": len(files),
            "deleted_texts_count": total_deleted_texts
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in delete_category: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete category")
    except Exception as e:
        documents_logger.error(f"Unexpected error in delete_category: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== FILE ENDPOINTS ====================

async def create_file(file: FileCreate, db_check=Depends(check_db_health)):
    """Create a new file within a specific category."""
    try:
        if not check_record_exists('categories', 'category_id', file.category_id):
            raise HTTPException(status_code=404, detail="Category not found")
        
        duplicate_check_query = """
            SELECT 1 FROM files 
            WHERE category_id = %s AND file_name = %s
        """
        if execute_single_query(duplicate_check_query, (file.category_id, file.file_name)):
            raise HTTPException(
                status_code=409,
                detail=f"File '{file.file_name}' already exists in this category"
            )
        
        insert_query = """
            INSERT INTO files (category_id, file_name)
            VALUES (%s, %s)
            RETURNING file_id
        """
        
        file_id = execute_insert(insert_query, (file.category_id, file.file_name))
        
        documents_logger.info(f"Created file: {file.file_name} with ID: {file_id} in category: {file.category_id}")
        
        return {
            "message": "File created successfully",
            "file_id": file_id,
            "file_name": file.file_name,
            "category_id": file.category_id,
            "note": "File is ready to receive text entries that will be stored with embeddings"
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in create_file: {e}")
        raise HTTPException(status_code=500, detail="Failed to create file")
    except Exception as e:
        documents_logger.error(f"Unexpected error in create_file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def delete_file(file_id: int, db_check=Depends(check_db_health)):
    """Delete a specific file and all its associated text entries."""
    try:
        file_query = "SELECT file_name FROM files WHERE file_id = %s"
        file_info = execute_single_query(file_query, (file_id,))
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_name = file_info['file_name']
        
        deleted_texts_count = soft_delete_all_texts_for_file(file_name)
        
        delete_query = "DELETE FROM files WHERE file_id = %s"
        deleted_count = execute_delete(delete_query, (file_id,))
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="File not found")
        
        documents_logger.info(f"Deleted file ID: {file_id} ({file_name}) with {deleted_texts_count} text entries")
        
        return {
            "message": "File and associated text entries deleted successfully",
            "file_name": file_name,
            "deleted_texts_count": deleted_texts_count
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in delete_file: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")
    except Exception as e:
        documents_logger.error(f"Unexpected error in delete_file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== TEXT ENDPOINTS ====================

async def search_texts(query: str, page: int = 1, size: int = 10, db_check=Depends(check_db_health)):
    """Search texts using full-text search on the qa_texts table."""
    if len(query.strip()) < 2: raise HTTPException(status_code=400, detail="Query is too short")
    if page < 1 or size < 1: raise HTTPException(status_code=400, detail="Page and size must be positive")
    texts, total = search_texts_in_qa_table(query, page, size)
    return SearchResponse(query=query, texts=texts, current_page=page, page_size=size, total_texts=total)


async def get_texts_by_file(file_id: int, db_check=Depends(check_db_health)):
    """Retrieve all texts for a file from the qa_texts table."""
    file_info = execute_single_query("SELECT file_name FROM files WHERE file_id = %s", (file_id,))
    if not file_info: raise HTTPException(status_code=404, detail="File not found")
    texts = get_texts_from_qa_table(file_info['file_name'])
    return FileTextsResponse(file_id=file_id, file_name=file_info['file_name'], texts=texts, total_count=len(texts))


async def create_text_entries(file_id: int, data: Union[TextCreate, TextCreateBatch], db_check=Depends(check_db_health)):
    """Create new text entry(ies) in both qa_texts and the vector store."""
    file_info = execute_single_query("SELECT file_name FROM files WHERE file_id = %s", (file_id,))
    if not file_info: raise HTTPException(status_code=404, detail="File not found")
    texts = data.texts if isinstance(data, TextCreateBatch) else [data]
    if not texts: raise HTTPException(status_code=400, detail="No text entries provided")
    
    to_create = [(t.question, t.answer, t.text_author) for t in texts]
    text_ids = create_text_entries_in_db(to_create, file_info['file_name'])
    
    if isinstance(data, TextCreateBatch):
        return {"message": f"Successfully created {len(text_ids)} entries", "created_ids": text_ids}
    return {"message": "Text entry created", "text_id": text_ids[0]}


async def update_text_entries(text_data: Union[TextUpdate, TextUpdateBatch], db_check=Depends(check_db_health)):
    """Update existing text entry(ies) in both qa_texts and the vector store."""
    try:
        texts_to_update = []
        if isinstance(text_data, TextUpdateBatch):
            texts_to_update = [(t.text_id, t.question, t.answer, t.text_author) for t in text_data.texts]
        else:
            texts_to_update = [(text_data.text_id, text_data.question, text_data.answer, text_data.text_author)]
            
        if not texts_to_update:
            raise HTTPException(status_code=400, detail="No text entries to update")
        
        updated_count = update_text_entries_in_db(texts_to_update)
        
        documents_logger.info(f"Updated {updated_count} text entries.")
        
        if isinstance(text_data, TextUpdateBatch):
            return {
                "message": f"Successfully updated {updated_count} text entries",
                "total_updated": updated_count
            }
        else:
            return {
                "message": "Text entry updated successfully",
                "text_id": text_data.text_id
            }

    except HTTPException:
        raise
    except Exception as e:
        documents_logger.error(f"Unexpected error in update_text_entries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def update_text_single(text_id: str, payload: TextCreate, db_check=Depends(check_db_health)):
    """Update a single text entry."""
    body = TextUpdate(text_id=text_id, **payload.model_dump())
    update_text_entries_in_db([(body.text_id, body.question, body.answer, body.text_author)])
    return {"message": "Text entry updated successfully", "text_id": text_id}


async def update_text_batch(data: TextUpdateBatch, db_check=Depends(check_db_health)):
    """Update a batch of text entries."""
    if not data.texts: raise HTTPException(status_code=400, detail="No entries to update")
    to_update = [(t.text_id, t.question, t.answer, t.text_author) for t in data.texts]
    count = update_text_entries_in_db(to_update)
    return {"message": f"Successfully updated {count} entries", "total_updated": count}


async def delete_text_batch(data: TextDeleteBatch, db_check=Depends(check_db_health)):
    """Delete a batch of text entries."""
    if not data.text_ids: raise HTTPException(status_code=400, detail="No text IDs provided")
    count = soft_delete_text_entries_in_db(data.text_ids)
    return {"message": f"Successfully deleted {count} entries", "deleted_ids": data.text_ids}


async def delete_text_single(text_id: str, db_check=Depends(check_db_health)):
    """Delete a single text entry."""
    count = soft_delete_text_entries_in_db([text_id])
    if count == 0: raise HTTPException(status_code=404, detail="Text ID not found")
    return {"message": "Text entry deleted successfully", "text_id": text_id}


async def delete_text_single(text_id: str, db_check=Depends(check_db_health)):
    """Delete a single text entry."""
    count = soft_delete_text_entries_in_db([text_id])
    if count == 0: raise HTTPException(status_code=404, detail="Text ID not found")
    return {"message": "Text entry deleted successfully", "text_id": text_id}
    

# ==================== INCIDENTS ENDPOINTS ====================
async def get_all_incidents(db_check=Depends(check_db_health)):
    """
    Retrieve all incidents with their associated files.
    """
    try:
        query = """
            SELECT *
            FROM incidents
            ORDER BY incident_startdate ASC
        """
        
        results = execute_query(query)
        
        incidents_dict = {}
        
        for row in results:
            incident_id = row['incident_id']
            
            if incident_id not in incidents_dict:
                incidents_dict[incident_id] = {
                    'incident_id': incident_id,
                    'incident_name': row['incident_name'],
                    'incident_description': row['incident_description'],
                    'incident_script': row['incident_script'],
                    'incident_startdate': row['incident_startdate'],
                    'incident_enddate': row['incident_enddate']
                }
        
        return list(incidents_dict.values())
        
    except DatabaseError as e:
        documents_logger.error(f"Database error in get_all_incidents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve incidents")
    except Exception as e:
        documents_logger.error(f"Unexpected error in get_all_incidents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def create_incident(incident: IncidentCreate, db_check=Depends(check_db_health)):
    """
    Create a new incident.
    """
    try:
        query = """
            INSERT INTO incidents (incident_name, incident_description, incident_script, incident_startdate, incident_enddate) 
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING incident_id
        """
        
        incident_id = execute_insert(query, (incident.incident_name,
                                             incident.incident_description,
                                             incident.incident_script,
                                             incident.incident_startdate,
                                             incident.incident_enddate))
        
        documents_logger.info(f"Created incident: {incident.incident_name} with ID: {incident_id}")
        
        return {
            "message": "Incident created successfully",
            "incident_id": incident_id,
            "incident_name": incident.incident_name,
            "incident_description": incident.incident_description
        }
    
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in create_incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to create incident")
    except Exception as e:
        documents_logger.error(f"Unexpected error in create_incident: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

async def update_incident(incident: IncidentUpdate, db_check=Depends(check_db_health)):
    try:
        incident_id = incident.incident_id
        update_data = incident.model_dump(exclude_unset=True)
        
        update_data.pop("incident_id", None)
        
        if not update_data:
            return {"message": "No update data provided. Incident remains unchanged."}
        
        incident_query = "SELECT incident_id FROM incidents WHERE incident_id = %s LIMIT 1"
        incident_result = execute_single_query(incident_query, (incident_id,))
        
        if not incident_result:
            raise HTTPException(status_code=404, detail=f"Incident with id {incident_id} not found")
        
        set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
        update_values = list(update_data.values())
        
        update_query = f"UPDATE incidents SET {set_clause} WHERE incident_id = %s"
        
        params = tuple(update_values) + (incident_id,)
        
        execute_update(update_query, params)
        
        documents_logger.info(f"Updated incident entry with id {incident_id}")
        
        return {
            "message": "Incident entry updated successfully",
            "incident_id": incident_id
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in update_incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to update incident due to a database error.")
    except Exception as e:
        documents_logger.error(f"Unexpected error in update_incident: {e}")
        raise HTTPException(status_code=500, detail="An unexpected internal server error occurred.")


async def delete_incident(incident_id: int, db_check=Depends(check_db_health)):
    """Delete an incident."""
    try:
        if not check_record_exists('incidents', 'incident_id', incident_id):
            raise HTTPException(status_code=404, detail="Incident not found")
        
        delete_incident_query = "DELETE FROM incidents WHERE incident_id = %s"
        execute_delete(delete_incident_query, (incident_id,))
        
        documents_logger.info(f"Deleted incident ID: {incident_id}")
        
        return {
            "message": "Incident deleted successfully"
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        documents_logger.error(f"Database error in delete_incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete incident")
    except Exception as e:
        documents_logger.error(f"Unexpected error in delete_incident: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")