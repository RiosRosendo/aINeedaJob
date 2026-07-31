#!/usr/bin/env python3
"""Migration script to add priority_country column to user_profiles table."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db import get_connection

def migrate():
    """Add priority_country column if it doesn't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='user_profiles' AND column_name='priority_country'
        """)

        if cursor.fetchone():
            print("[MIGRATE] priority_country column already exists")
            cursor.close()
            conn.close()
            return True

        # Add the column
        print("[MIGRATE] Adding priority_country column to user_profiles table...")
        cursor.execute("""
            ALTER TABLE user_profiles
            ADD COLUMN priority_country VARCHAR(100) NULL DEFAULT NULL;
        """)

        conn.commit()
        print("[MIGRATE] Successfully added priority_country column")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[MIGRATE] Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
