#!/usr/bin/env python3
"""Migration: Add follow-up and interview prep support."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db import get_connection


def migrate():
    """Add follow-up columns and interview_prep table."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if follow_up_sent_at column already exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='applications' AND column_name='follow_up_sent_at'
        """)

        if not cursor.fetchone():
            print("[MIGRATE] Adding follow-up columns to applications table...")
            cursor.execute("""
                ALTER TABLE applications
                ADD COLUMN follow_up_sent_at TIMESTAMP NULL,
                ADD COLUMN follow_up_attempt_count INTEGER DEFAULT 0;
            """)
            print("[MIGRATE] Added follow-up columns to applications")
        else:
            print("[MIGRATE] Follow-up columns already exist")

        # Check if interview_prep table exists
        cursor.execute("""
            SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='interview_prep')
        """)

        if not cursor.fetchone()[0]:
            print("[MIGRATE] Creating interview_prep table...")
            cursor.execute("""
                CREATE TABLE interview_prep (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    application_id UUID NOT NULL,
                    job_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    questions JSONB,
                    talking_points JSONB,
                    company_research TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (application_id) REFERENCES applications(id),
                    FOREIGN KEY (job_id) REFERENCES jobs(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """)
            print("[MIGRATE] Created interview_prep table")
        else:
            print("[MIGRATE] interview_prep table already exists")

        # Check if company_emails table exists (for storing company contact emails)
        cursor.execute("""
            SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='company_emails')
        """)

        if not cursor.fetchone()[0]:
            print("[MIGRATE] Creating company_emails table...")
            cursor.execute("""
                CREATE TABLE company_emails (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_name VARCHAR(255) NOT NULL,
                    contact_email VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE (company_name)
                );
            """)
            print("[MIGRATE] Created company_emails table")
        else:
            print("[MIGRATE] company_emails table already exists")

        conn.commit()
        cursor.close()
        conn.close()

        print("[MIGRATE] All migrations completed successfully")
        return True

    except Exception as e:
        print(f"[MIGRATE] Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
