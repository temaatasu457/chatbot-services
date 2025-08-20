import uuid
from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from env import load_config
from psycopg2.extras import execute_values
from documents_logger import documents_logger
from fastapi import HTTPException
from typing import Any, Dict, List
from utils import execute_query, db_connection
from config import TRASH_COLLECTION_ID


config = load_config('env-path')
emb_model = OpenAIEmbeddings(model='text-embedding-3-small', api_key=config.api_key.openai_api_key)
vector_db = PGVector(embeddings=emb_model, collection_name="chatbot_base", connection=config.vdb.database_url)


def create_text_entries_in_db(texts_data: List[tuple], file_name: str) -> List[str]:
    """Adds texts to BOTH the vector DB (without newlines) and the qa_texts table (with newlines)."""
    vector_texts, text_ids, qa_texts_data = [], [], []

    for question, answer, author in texts_data:
        text_id = f"{file_name}-{str(uuid.uuid4())}"
        text_ids.append(text_id)

        full_content_with_newlines = f'Вопрос: {question} Ответ: {answer}'
        qa_texts_data.append((text_id, full_content_with_newlines, author))
        
        full_content_without_newlines = full_content_with_newlines.replace("\n", " ")
        vector_texts.append(full_content_without_newlines)

    conn = db_connection.get_connection()
    try:
        with conn.cursor() as cur:
            insert_query = "INSERT INTO qa_texts (text_id, text_content, text_author) VALUES %s"
            execute_values(cur, insert_query, qa_texts_data)
            
            vector_db.add_texts(texts=vector_texts, ids=text_ids)
            
            conn.commit()
            documents_logger.info(f"Successfully added {len(text_ids)} texts to both qa_texts and vector DB.")
            return text_ids
    except Exception as e:
        conn.rollback()
        documents_logger.error(f"Error creating text entries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create text entries: {str(e)}")


def update_text_entries_in_db(texts_data: List[tuple]):
    """Updates texts in BOTH the vector DB (without newlines) and the qa_texts table (with newlines)."""
    text_ids = [data[0] for data in texts_data]
    if not text_ids: return 0

    conn = db_connection.get_connection()
    try:
        with conn.cursor() as cur:
            update_query = """
                UPDATE qa_texts SET text_content = data.text_content, text_author = data.text_author, updated_at = CURRENT_TIMESTAMP
                FROM (VALUES %s) AS data(text_id, text_content, text_author)
                WHERE qa_texts.text_id = data.text_id
            """
            update_values_with_newlines = [(d[0], f'Вопрос: {d[1]} Ответ: {d[2]}', d[3]) for d in texts_data]
            execute_values(cur, update_query, update_values_with_newlines)

            vector_db.delete(ids=text_ids)
            
            new_vector_texts_without_newlines = []
            for d in texts_data:
                q = d[1].replace("\n", " ")
                a = d[2].replace("\n", " ")
                new_vector_texts_without_newlines.append(f"Вопрос: {q} Ответ: {a}")
            vector_db.add_texts(texts=new_vector_texts_without_newlines, ids=text_ids)
            
            conn.commit()
            documents_logger.info(f"Successfully updated {len(text_ids)} entries in both tables.")
            return len(text_ids)
    except Exception as e:
        conn.rollback()
        documents_logger.error(f"Error updating text entries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update entries: {str(e)}")


def soft_delete_text_entries_in_db(text_ids: List[str]):
    """Deletes from qa_texts and soft-deletes from vector DB."""
    if not text_ids: return 0

    conn = db_connection.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM qa_texts WHERE text_id = ANY(%s)", (text_ids,))
            deleted_rows = cur.rowcount
            
            update_query = "UPDATE langchain_pg_embedding SET collection_id = %s WHERE id = ANY(%s)"
            cur.execute(update_query, (TRASH_COLLECTION_ID, text_ids))
            
            conn.commit()
            documents_logger.info(f"Deleted {deleted_rows} from qa_texts and soft-deleted {cur.rowcount} from vector DB.")
            return deleted_rows
    except Exception as e:
        conn.rollback()
        documents_logger.error(f"Error deleting entries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete text entries: {str(e)}")


def soft_delete_all_texts_for_file(file_name: str):
    """Soft delete all texts for a file from vector DB and hard delete from qa_texts."""
    id_query = "SELECT text_id FROM qa_texts WHERE text_id LIKE %s"
    results = execute_query(id_query, (f"{file_name}-%",))
    text_ids = [result["text_id"] for result in results]
    return soft_delete_text_entries_in_db(text_ids) if text_ids else 0


def _parse_qa_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to parse a row from qa_texts into the desired response format."""
    text_content = row.get("text_content", "")
    parts = text_content.split(" Ответ:", 1)
    question = parts[0][8:] if parts[0].startswith("Вопрос: ") else ""
    answer = parts[1][1:] if len(parts) > 1 else ""
    return {
        "text_id": row["text_id"], "file_name": row["text_id"].split("-")[0],
        "question": question, "answer": answer, "text_author": row["text_author"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def get_texts_from_qa_table(file_name: str) -> List[Dict[str, Any]]:
    """Retrieves all texts for a file directly from the `qa_texts` table."""
    try:
        query = "SELECT * FROM qa_texts WHERE text_id LIKE %s ORDER BY created_at"
        results = execute_query(query, (f"{file_name}-%",))
        return [_parse_qa_row(row) for row in results]
    except Exception as e:
        documents_logger.error(f"Error retrieving texts from qa_texts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve texts: {str(e)}")


def hard_delete_texts_from_vector_db(text_ids: List[str]):
    """
    Hard delete multiple texts from vector database by IDs.
    
    Args:
        text_ids: List of text IDs to hard delete
    """
    try:
        vector_db.delete(ids=text_ids)
        documents_logger.info(f"Successfully hard deleted {len(text_ids)} texts from vector DB")
    except Exception as e:
        documents_logger.error(f"Error hard deleting texts from vector database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to hard delete text entries: {str(e)}")


def search_texts_in_qa_table(query_text: str, page: int, size: int):
    """Performs full-text search directly on the `qa_texts.text_content` column."""
    try:
        offset = (page - 1) * size
        query = """
            SELECT *, COUNT(*) OVER() AS total_texts
            FROM qa_texts, plainto_tsquery('simple', %s) AS query
            WHERE to_tsvector('simple', text_content) @@ query
            ORDER BY ts_rank_cd(to_tsvector('simple', text_content), query) DESC, created_at DESC
            LIMIT %s OFFSET %s;
        """
        results = execute_query(query, (query_text, size, offset))
        if not results: return [], 0
        texts = [_parse_qa_row(row) for row in results]
        total_texts = results[0]["total_texts"]
        return texts, total_texts
    except Exception as e:
        documents_logger.error(f"Error searching texts in qa_texts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search texts: {str(e)}")


def get_texts_from_qa_table(file_name: str) -> List[Dict[str, Any]]:
    """
    Retrieves all texts for a specific file directly from the `qa_texts` table.
    """
    try:
        query = """
            SELECT 
                text_id,
                text_content,
                text_author,
                created_at,
                updated_at
            FROM qa_texts
            WHERE text_id LIKE %s
            ORDER BY created_at
        """
        results = execute_query(query, (f"{file_name}-%",))
        
        return [_parse_qa_row(row) for row in results]
        
    except Exception as e:
        documents_logger.error(f"Error retrieving texts from qa_texts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve texts: {str(e)}")