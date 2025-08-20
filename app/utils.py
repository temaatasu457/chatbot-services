import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple
import os

DB_CONFIG = {
    "host" : os.getenv("DB_HOST", "localhost"),
    "port" : os.getenv("DB_PORT", "6024"),
    "database" : os.getenv("DB_NAME", "chatbot_base"),
    "user" : os.getenv("DB_USER", "chatbot_base"),
    "password" : os.getenv("DB_PASSWORD", "chatbot_base")
}   
    
def get_connection_string() -> str:
    return "host=" + DB_CONFIG["host"] + " port=" + DB_CONFIG["port"] + " dbname=" + DB_CONFIG["database"] + " user=" + DB_CONFIG["user"] + " password=" + DB_CONFIG["password"]


class DatabaseError(Exception):
    pass


class DatabaseConnection:
    
    def __init__(self):
        self._connection = None
    
    def get_connection(self):
        if self._connection is None or self._connection.closed:
            try:
                self._connection = psycopg2.connect(
                    get_connection_string(),
                    cursor_factory=RealDictCursor
                )
                self._connection.autocommit = False
            except psycopg2.Error as e:
                raise DatabaseError(f"Failed to connect to database: {e}")
        
        return self._connection
    
    def close_connection(self):
        if self._connection and not self._connection.closed:
            self._connection.close()


db_connection = DatabaseConnection()


@contextmanager
def get_db_cursor():
    conn = db_connection.get_connection()
    cursor = conn.cursor()
    
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise DatabaseError(f"Database operation failed: {e}")
    finally:
        cursor.close()


def execute_query(query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries.
    
    Args:
        query: SQL query string with placeholders
        params: Query parameters tuple
    
    Returns:
        List of dictionaries representing query results
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchall()


def execute_single_query(query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
    """
    Execute a SELECT query and return single result as dictionary.
    
    Args:
        query: SQL query string with placeholders
        params: Query parameters tuple
    
    Returns:
        Dictionary representing single query result or None
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchone()


def execute_insert(query: str, params: Optional[Tuple] = None) -> int:
    """
    Execute an INSERT query and return the ID of inserted record.
    
    Args:
        query: SQL INSERT query with RETURNING id clause
        params: Query parameters tuple
    
    Returns:
        ID of the inserted record
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        result = cursor.fetchone()
        if result and 'id' in result:
            return result['id']
        elif result:
            return list(result.values())[0]
        raise DatabaseError("Insert query did not return an ID")


def execute_update(query: str, params: Optional[Tuple] = None) -> int:
    """
    Execute an UPDATE query and return number of affected rows.
    
    Args:
        query: SQL UPDATE query string
        params: Query parameters tuple
    
    Returns:
        Number of rows affected by the update
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.rowcount


def execute_delete(query: str, params: Optional[Tuple] = None) -> int:
    """
    Execute a DELETE query and return number of deleted rows.
    
    Args:
        query: SQL DELETE query string
        params: Query parameters tuple
    
    Returns:
        Number of rows deleted
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.rowcount


def check_record_exists(table: str, condition_column: str, condition_value: Any) -> bool:
    """
    Check if a record exists in specified table with given condition.
    
    Args:
        table: Table name to check
        condition_column: Column name for condition
        condition_value: Value to check for
    
    Returns:
        True if record exists, False otherwise
    """
    query = f"SELECT 1 FROM {table} WHERE {condition_column} = %s LIMIT 1"
    result = execute_single_query(query, (condition_value,))
    return result is not None


def get_table_count(table: str, condition: Optional[str] = None, params: Optional[Tuple] = None) -> int:
    """
    Get count of records in table with optional condition.
    
    Args:
        table: Table name to count records from
        condition: Optional WHERE condition
        params: Parameters for the condition
    
    Returns:
        Number of records matching the condition
    """
    base_query = f"SELECT COUNT(*) as count FROM {table}"
    if condition:
        query = f"{base_query} WHERE {condition}"
    else:
        query = base_query
    
    result = execute_single_query(query, params)
    return result['count'] if result else 0


def check_database_health() -> Dict[str, Any]:
    """
    Check database connectivity and return health status.
    
    Returns:
        Dictionary with health status information
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1 as health_check")
            result = cursor.fetchone()
            
            if result and result['health_check'] == 1:
                return {
                    "status": "healthy",
                    "database": DB_CONFIG["database"],
                    "host": DB_CONFIG["host"]
                }
            else:
                return {"status": "unhealthy", "error": "Unexpected response"}
                
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}