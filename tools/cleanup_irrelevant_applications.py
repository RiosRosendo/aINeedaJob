"""
Clean up historical applications that are not relevant to user's profile.
Uses LLM to evaluate title relevance for each application.

IMPORTANT: Only marks jobs as ignored if BOTH conditions are met:
1. fit_score < 60 (low relevance score)
2. Title is not relevant to user's target roles

Never touches jobs with fit_score >= 60 regardless of title relevance.
"""

import sys
from tools.db import execute_query, execute_update
from tools.llm import call_llm

ROSENDO_USER_ID = "14ab2d63-1eef-43d9-b3f4-748566bad8da"


def cleanup_irrelevant_applications(user_id=ROSENDO_USER_ID):
    """
    Find applications with low fit_score AND non-relevant titles, mark as ignored.

    Returns: {total_checked, marked_ignored, errors, skipped_high_score}
    """
    print(f"[CLEANUP] Starting cleanup for user {user_id}")

    # Get user profile
    profile_result = execute_query(
        "SELECT target_roles FROM user_profiles WHERE user_id = %s",
        (user_id,)
    )
    if not profile_result:
        print(f"[CLEANUP] User profile not found")
        return {"total_checked": 0, "marked_ignored": 0, "errors": 0, "skipped_high_score": 0}

    target_roles = profile_result[0].get("target_roles", [])
    print(f"[CLEANUP] User target roles: {target_roles}")

    # Fetch all applications with their fit scores
    applications = execute_query(
        """
        SELECT a.id, a.job_id, a.status, j.title, j.company, fs.score
        FROM applications a
        LEFT JOIN jobs j ON a.job_id = j.id
        LEFT JOIN fit_scores fs ON a.job_id = fs.job_id AND fs.user_id = a.user_id
        WHERE a.user_id = %s
        AND a.status IN ('pending_approval', 'pending_application', 'requires_manual', 'ignored')
        AND j.id IS NOT NULL
        ORDER BY fs.score DESC NULLS LAST
        """,
        (user_id,)
    )

    if not applications:
        print(f"[CLEANUP] No applications to check")
        return {"total_checked": 0, "marked_ignored": 0, "errors": 0, "skipped_high_score": 0}

    print(f"[CLEANUP] Found {len(applications)} applications to evaluate")

    total_checked = 0
    marked_ignored = 0
    errors = 0
    skipped_high_score = 0

    for app in applications:
        app_id = app.get("id")
        job_id = app.get("job_id")
        title = app.get("title", "Unknown")
        company = app.get("company", "Unknown")
        fit_score = app.get("score") or 0

        print(f"\n[CLEANUP] Evaluating: {title} at {company} (score={fit_score})")

        # SAFETY CHECK: Never touch jobs with fit_score >= 60
        if fit_score >= 60:
            print(f"[CLEANUP] SKIPPING (fit_score >= 60): {title}")
            skipped_high_score += 1
            continue

        total_checked += 1

        try:
            # Only evaluate low-score jobs for title relevance
            is_relevant = _is_title_relevant(title, target_roles)

            if not is_relevant:
                print(f"[CLEANUP] MARKING AS IGNORED (low score + irrelevant): {title}")
                # Mark application as ignored
                execute_update(
                    "UPDATE applications SET status = %s, updated_at = NOW() WHERE id = %s",
                    ("ignored", app_id)
                )
                marked_ignored += 1
            else:
                print(f"[CLEANUP] KEEPING (low score but relevant): {title}")

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"[CLEANUP] Error evaluating {title}: {error_msg}")
            errors += 1

    result = {
        "total_checked": total_checked,
        "marked_ignored": marked_ignored,
        "errors": errors,
        "skipped_high_score": skipped_high_score
    }
    print(f"\n[CLEANUP] Summary: {result}")
    return result


def _is_title_relevant(title, target_roles):
    """Check if job title is relevant to target roles using LLM."""
    if not title or not target_roles:
        return True

    try:
        roles_str = ", ".join(target_roles)
        prompt = f"""Is this job title DIRECTLY relevant to robotics, embedded systems, AI/ML, or autonomous systems?

Job Title: {title}
Target Roles: {roles_str}

STRICT RULES:
- REJECT: Controls Engineer, Process Engineer, Manufacturing Engineer, Quality Engineer, Civil Engineer, Mechanical Engineer, Industrial Engineer, Layout Engineer
- REJECT titles containing: Controls, Process, Manufacturing, Quality, Civil, Industrial, Facilities, Operations, Support Grid
- ACCEPT: Robotics, Embedded, Autonomous, Vision, AI, ML, ROS, Computer Vision, Deep Learning, Neural, Firmware, Software/Embedded

Answer only YES or NO."""

        response = call_llm(prompt).strip().upper()
        is_relevant = response.startswith("YES")

        print(f"[CLEANUP LLM] LLM response: {response} (relevant={is_relevant})")
        return is_relevant

    except Exception as e:
        error_msg = str(e)[:50]
        print(f"[CLEANUP LLM] Error evaluating '{title}': {error_msg}")
        return True  # On error, assume relevant to be conservative


if __name__ == "__main__":
    result = cleanup_irrelevant_applications()
    print(f"\n[CLEANUP] Final result: {result}")
    sys.exit(0 if result["errors"] == 0 else 1)
