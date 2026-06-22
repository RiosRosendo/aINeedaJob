"""
Database connection utilities for aINeedJob.

Provides reusable PostgreSQL connection and query execution helpers.

Required environment variables:
  - DATABASE_URL: PostgreSQL connection string
    (e.g., postgresql://user:pass@localhost:5432/aineedjob)

Example usage:
  from tools.db import execute_query, execute_update

  # SELECT query
  results = execute_query('SELECT * FROM users WHERE id = %s', (user_id,))

  # INSERT/UPDATE/DELETE
  rows_affected = execute_update(
    'INSERT INTO jobs (user_id, title) VALUES (%s, %s)',
    (user_id, 'AI Engineer')
  )
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env")


def get_connection():
    """
    Get a PostgreSQL connection.

    Returns:
        psycopg2 connection object

    Raises:
        Exception: If connection fails
    """
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        raise Exception(f"Database connection failed: {str(e)}")


def execute_query(query, params=None, conn=None):
    """
    Execute a SELECT query and return results.

    Args:
        query (str): SQL query with %s placeholders for parameters
        params (tuple): Query parameters for parameterized query
        conn: Connection object (creates new if None)

    Returns:
        list: List of result rows as dictionaries

    Raises:
        Exception: If query execution fails
    """
    close_conn = conn is None
    conn = conn or get_connection()

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        cursor.close()
        conn.commit()
        return results
    except Exception as e:
        conn.rollback()
        raise Exception(f"Query failed: {str(e)}")
    finally:
        if close_conn:
            conn.close()


def execute_update(query, params=None, conn=None):
    """
    Execute an INSERT/UPDATE/DELETE query.

    Args:
        query (str): SQL query with %s placeholders
        params (tuple): Query parameters
        conn: Connection object (creates new if None)

    Returns:
        int: Number of rows affected

    Raises:
        Exception: If query execution fails
    """
    close_conn = conn is None
    conn = conn or get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        rows_affected = cursor.rowcount
        cursor.close()
        conn.commit()
        return rows_affected
    except Exception as e:
        conn.rollback()
        raise Exception(f"Update failed: {str(e)}")
    finally:
        if close_conn:
            conn.close()
