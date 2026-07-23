"""
Clean up historical applications that are not relevant to user's profile.
Uses LLM to evaluate title relevance for each application.
"""

import sys
from tools.db import execute_query, execute_update
from tools.llm import call_llm

ROSENDO_USER_ID = "14ab2d63-1eef-43d9-b3f4-748566bad8da"


def cleanup_irrelevant_applications(user_id=ROSENDO_USER_ID):
    """
    Find applications with non-relevant titles and mark them as ignored.

    Returns: {total_checked, marked_ignored, errors}
    """
    print(f"[CLEANUP] Starting cleanup for user {user_id}")

    # Get user profile
    profile_result = execute_query(
        "SELECT target_roles FROM user_profiles WHERE user_id = %s",
        (user_id,)
    )
    if not profile_result:
        print(f"[CLEANUP] User profile not found")
        return {"total_checked": 0, "marked_ignored": 0, "errors": 1}

    target_roles = profile_result[0].get("target_roles", [])
    print(f"[CLEANUP] User target roles: {target_roles}")

    # Fetch all applications that might have low relevance
    applications = execute_query(
        """
        SELECT a.id, a.job_id, j.title, j.company, j.id as job_id_check
        FROM applications a
        LEFT JOIN jobs j ON a.job_id = j.id
        WHERE a.user_id = %s
        AND a.status IN ('pending_approval', 'pending_application', 'requires_manual')
        AND j.id IS NOT NULL
        ORDER BY a.created_at DESC
        """,
        (user_id,)
    )

    if not applications:
        print(f"[CLEANUP] No applications to check")
        return {"total_checked": 0, "marked_ignored": 0, "errors": 0}

    print(f"[CLEANUP] Found {len(applications)} applications to evaluate")

    total_checked = 0
    marked_ignored = 0
    errors = 0

    for app in applications:
        app_id = app.get("id")
        job_id = app.get("job_id")
        title = app.get("title", "Unknown")
        company = app.get("company", "Unknown")

        print(f"\n[CLEANUP] Evaluating: {title} at {company}")

        try:
            # Check if title is relevant using LLM
            is_relevant = _is_title_relevant(title, target_roles)
            total_checked += 1

            if not is_relevant:
                print(f"[CLEANUP] MARKING AS IGNORED: {title}")
                # Mark application as ignored
                execute_update(
                    "UPDATE applications SET status = %s, updated_at = NOW() WHERE id = %s",
                    ("ignored", app_id)
                )
                marked_ignored += 1
            else:
                print(f"[CLEANUP] KEEPING (relevant): {title}")

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"[CLEANUP] Error evaluating {title}: {error_msg}")
            errors += 1

    result = {
        "total_checked": total_checked,
        "marked_ignored": marked_ignored,
        "errors": errors
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
