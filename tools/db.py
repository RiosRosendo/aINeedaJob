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


def get_source_quality_metrics(user_id):
    """
    Get relevance rate for each job source (relevant_jobs / total_jobs).

    Used for autonomous source selection: deprioritize sources < 10% relevance.

    Returns:
        dict: {'adzuna': 0.75, 'themuse': 0.45, ...}
    """
    try:
        results = execute_query(
            """
            SELECT
                source,
                COUNT(*) as total,
                SUM(CASE WHEN fs.score >= 60 THEN 1 ELSE 0 END) as relevant
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s AND j.expires_at IS NULL
            GROUP BY source
            """,
            (user_id, user_id)
        )

        metrics = {}
        for row in results:
            source = row.get('source', 'unknown')
            total = row.get('total', 0)
            relevant = row.get('relevant', 0)
            rate = (relevant / total) if total > 0 else 0
            metrics[source] = rate

        return metrics
    except Exception as e:
        print(f"[ERROR] Failed to get source metrics: {str(e)}")
        return {}


def should_use_source(user_id, source):
    """
    Autonomously decide whether to use a source based on historical performance.

    Returns False if source has < 10% relevance rate (too many irrelevant jobs).

    Returns:
        bool: True if source quality is acceptable, False if deprioritized
    """
    metrics = get_source_quality_metrics(user_id)
    relevance_rate = metrics.get(source, 0.5)  # Default to 50% if no history
    return relevance_rate >= 0.10  # Deprioritize if < 10% relevant
