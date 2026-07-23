#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

try:
    import asyncio
    from api.routes.jobs import get_jobs_by_country

    user_id = "14ab2d63-1eef-43d9-b3f4-748566bad8da"
    result = asyncio.run(get_jobs_by_country(user_id=user_id))

    print("SUCCESS! Result:")
    for country in result:
        print(f"  {country['country']}: {country['count']} jobs")
except Exception as e:
    import traceback
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
