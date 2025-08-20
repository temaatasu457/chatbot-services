import os, uuid
import requests
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from env import load_config
from psycopg2.extras import execute_values
from utils import db_connection
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

conn = db_connection.get_connection()

def new_load_knowledge_data_with_qa_texts(db, conn, file_path, text_author):
        
    raw_documents = PyMuPDFLoader(file_path).load()
    document_name = Path(raw_documents[0].metadata["source"]).stem
    full_text = "".join(doc.page_content for doc in raw_documents)

    qa_chunks = [chunk.strip() for chunk in full_text.split("Вопрос:")][1:]
    
    if not qa_chunks:
        print(f"Warning: No Q&A chunks found in {document_name}. Skipping file.")
        return

    text_ids, qa_texts_data_to_insert, vector_texts_to_add = [], [], []

    for chunk in qa_chunks:
        parts = chunk.split("Ответ:", 1)
        question = parts[0].strip()
        answer = parts[1].strip() if len(parts) > 1 else ""

        if not question:
            continue

        new_id = f"{document_name}-{uuid.uuid4()}"
        text_ids.append(new_id)
        
        qa_texts_data_to_insert.append(
            (new_id, question, answer, text_author)
        )
        
        combined_content = f"Вопрос: {question} Ответ: {answer}"
        vector_texts_to_add.append(combined_content.replace("\n", " "))
    
    try:
        with conn.cursor() as cur:
            print(f"Inserting {len(qa_texts_data_to_insert)} records into qa_texts...")
            insert_query = "INSERT INTO qa_texts (text_id, text_question, text_answer, text_author) VALUES %s"
            execute_values(cur, insert_query, qa_texts_data_to_insert)
            
            print(f"Adding {len(vector_texts_to_add)} vectors to the vector store...")
            db.add_texts(texts=vector_texts_to_add, ids=text_ids)
            
            conn.commit()
            print(f"Successfully loaded {len(text_ids)} Q&A pairs from {document_name}.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error loading data from {document_name}: {e}")
        raise e

def process_pdf_files(folder_path, db):
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            file_path = os.path.join(folder_path, filename)
            try:
                new_load_knowledge_data_with_qa_texts(db, conn, file_path, "Author")
                print(f"Processed {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

folder_path = "folder-path"
config = load_config('env-path')
emb_model = OpenAIEmbeddings(model='text-embedding-3-small', api_key=config.api_key.openai_api_key)
vector_db = PGVector(embeddings=emb_model, connection=config.vdb.database_url)

def main():
    process_pdf_files(folder_path, vector_db)

if __name__ == '__main__':
    main()