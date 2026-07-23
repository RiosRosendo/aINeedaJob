#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

try:
    from api.routes.jobs import extract_country_from_location

    # Test the function
    test_cases = [
        'New York, US',
        'Toronto, ON, Canada',
        'Mexico City, Mexico',
        'Berlin, Germany',
        'Remote'
    ]

    for test in test_cases:
        result = extract_country_from_location(test)
        print(f'{test!r} -> {result!r}')

except Exception as e:
    import traceback
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    traceback.print_exc()
