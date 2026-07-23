#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

import asyncio
from agents.pipeline import graph, JobState

async def test_discovery():
    """Test job discovery with all 9 preferred countries"""

    print("[DISCOVERY TEST] Starting job discovery for user with 9 countries...")

    user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'
    target_roles = ['AI Engineer', 'Machine Learning Engineer', 'Robotics Engineer']
    preferred_countries = ['US', 'Canada', 'Mexico', 'Japan', 'Italy', 'France', 'Germany', 'UAE', 'China']

    print(f"\nInitial state:")
    print(f"  User: {user_id}")
    print(f"  Target roles: {target_roles}")
    print(f"  Preferred countries: {preferred_countries}")

    # Run discovery for just 30 seconds to see if it searches all countries
    print("\nStarting discovery pipeline (checking for all 9 countries in logs)...\n")

    try:
        # This will run the discovery pipeline
        input_state = {
            "user_id": user_id,
            "target_roles": target_roles,
            "preferred_countries": preferred_countries
        }

        # Call the discovery_node directly to see logs
        from agents.pipeline import discovery_node
        result = await discovery_node(input_state)

        print(f"\nDiscovery complete!")
        print(f"  Jobs discovered: {result.get('discovered_count', 0)}")
        print(f"  Countries searched: {result.get('countries_searched', [])}")

    except Exception as e:
        import traceback
        print(f"Error during discovery: {type(e).__name__}: {str(e)}")
        traceback.print_exc()

# Run the test
asyncio.run(test_discovery())
