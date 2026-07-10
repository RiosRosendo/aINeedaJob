"""
aINeedJob FastAPI Backend

Multi-user SaaS API for autonomous job search and application.
Every endpoint is user-scoped. User ID is extracted from request context.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="aINeedJob API",
    description="Autonomous job search and application automation",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from api.routes import jobs, applications, users, auth, cv, gmail

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(cv.router, prefix="/api/cv", tags=["cv"])
app.include_router(gmail.router, prefix="/api/gmail", tags=["gmail"])

# Initialize scheduler (will be started on app startup)
scheduler = BackgroundScheduler()


def run_daily_job_search():
    """
    Run daily job discovery for all users.

    Iterates through each user and triggers the job discovery pipeline
    to fetch new jobs matching their profile.
    """
    try:
        from tools.db import execute_query
        from agents.pipeline import graph, JobState

        print("[SCHEDULER] Starting daily job search for all users...", flush=True)

        # Get all active users
        users_result = execute_query(
            """
            SELECT u.id, u.email, up.target_roles, up.preferred_countries
            FROM users u
            LEFT JOIN user_profiles up ON u.id = up.user_id
            WHERE u.is_active = TRUE
            ORDER BY u.created_at DESC
            """,
            ()
        )

        if not users_result:
            print("[SCHEDULER] No active users found", flush=True)
            return

        total_users = len(users_result)
        processed_users = 0
        jobs_discovered = 0

        for user in users_result:
            user_id = user.get('id')
            email = user.get('email')
            target_roles = user.get('target_roles', [])
            preferred_countries = user.get('preferred_countries', [])

            try:
                print(f"[SCHEDULER] Running daily job search for user {email}", flush=True)

                # Initialize pipeline state
                state = JobState(
                    user_id=user_id,
                    raw_jobs=[],
                    unprocessed_jobs=[],
                    processed_count=0,
                    applied_count=0,
                    review_count=0,
                    ignored_count=0,
                    error="",
                    roles=target_roles or ["AI Engineer"],  # Default role if not set
                    profile={
                        "target_roles": target_roles,
                        "preferred_countries": preferred_countries,
                    },
                    summary={}
                )

                # Run the discovery pipeline
                result = graph.invoke(state)

                raw_jobs_count = len(result.get('raw_jobs', []))
                processed_count = result.get('processed_count', 0)
                applied_count = result.get('applied_count', 0)
                review_count = result.get('review_count', 0)

                jobs_discovered += raw_jobs_count
                processed_users += 1

                print(
                    f"[SCHEDULER] User {email}: discovered={raw_jobs_count}, "
                    f"processed={processed_count}, applied={applied_count}, review={review_count}",
                    flush=True
                )

            except Exception as e:
                print(
                    f"[SCHEDULER] ERROR for user {email} ({user_id}): {type(e).__name__}: {str(e)}",
                    flush=True
                )
                import traceback
                print(traceback.format_exc(), flush=True)
                continue

        print(
            f"[SCHEDULER] Daily job search complete! "
            f"Processed {processed_users}/{total_users} users, "
            f"discovered {jobs_discovered} new jobs",
            flush=True
        )
        sys.stdout.flush()

    except Exception as e:
        print(f"[SCHEDULER] FATAL ERROR: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        sys.stdout.flush()


@app.on_event("startup")
async def startup_event():
    """
    Start the background scheduler when the server starts.
    Runs daily job discovery at 8:00 AM.
    """
    try:
        print("[SCHEDULER] Starting background scheduler...", flush=True)

        # Schedule daily job search at 8:00 AM every day
        scheduler.add_job(
            run_daily_job_search,
            trigger=CronTrigger(hour=8, minute=0),
            id='daily_job_search',
            name='Daily Job Search',
            replace_existing=True,
            misfire_grace_time=60
        )

        scheduler.start()
        print("[SCHEDULER] Background scheduler started successfully", flush=True)
        print("[SCHEDULER] Daily job search scheduled for 8:00 AM every day", flush=True)

    except Exception as e:
        print(f"[SCHEDULER] Failed to start scheduler: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Stop the background scheduler when the server shuts down.
    """
    try:
        if scheduler.running:
            print("[SCHEDULER] Shutting down background scheduler...", flush=True)
            scheduler.shutdown(wait=True)
            print("[SCHEDULER] Background scheduler stopped successfully", flush=True)
    except Exception as e:
        print(f"[SCHEDULER] Error during scheduler shutdown: {type(e).__name__}: {str(e)}", flush=True)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "aINeedJob API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
