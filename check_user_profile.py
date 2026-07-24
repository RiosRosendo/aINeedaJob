#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

# Get user profile
user = execute_query(
    "SELECT target_roles, preferred_modality, preferred_countries, salary_min FROM user_profiles WHERE user_id = %s",
    (user_id,)
)

if user:
    profile = user[0]
    print("User Profile:")
    print(f"  Target roles: {profile.get('target_roles')}")
    print(f"  Preferred modality: {profile.get('preferred_modality')}")
    print(f"  Preferred countries: {profile.get('preferred_countries')}")
    print(f"  Min salary: ${profile.get('salary_min'):,}" if profile.get('salary_min') else "  Min salary: Not set")
else:
    print("User not found")
