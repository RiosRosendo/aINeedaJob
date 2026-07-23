#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

import asyncio
from tools.search_adzuna import search_adzuna
from tools.search_occ import search_occ_for_mexico

async def test_mexico_search():
    user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

    print("=" * 70)
    print("MEXICO-ONLY JOB SEARCH")
    print("=" * 70)

    roles = ['AI Engineer', 'Machine Learning Engineer', 'Robotics Engineer']

    print("\n[SEARCH] Searching Mexico with English roles...")
    jobs_en = search_adzuna(roles, 'mx', salary_min=80000)
    print(f"  Adzuna (English): {len(jobs_en)} jobs")

    print("\n[TRANSLATE] Getting Spanish translations...")
    # Simple Spanish translations for testing
    spanish_roles = [
        'Ingeniero de Inteligencia Artificial',
        'Ingeniero de Aprendizaje Automático',
        'Ingeniero de Robótica'
    ]

    jobs_es = search_adzuna(spanish_roles, 'mx', salary_min=80000)
    print(f"  Adzuna (Spanish): {len(jobs_es)} jobs")

    print("\n[OCC] Searching OCC Mundial (Mexico job board)...")
    jobs_occ = search_occ_for_mexico(spanish_roles)
    print(f"  OCC Mundial: {len(jobs_occ)} jobs")

    # Combine results
    all_mexico_jobs = jobs_en + jobs_es + jobs_occ
    unique_urls = set(j.get('url') for j in all_mexico_jobs if j.get('url'))

    print("\n" + "=" * 70)
    print("MEXICO SEARCH RESULTS")
    print("=" * 70)
    print(f"\nTotal jobs found: {len(all_mexico_jobs)}")
    print(f"Unique URLs: {len(unique_urls)}")
    print(f"\nBreakdown:")
    print(f"  • Adzuna English: {len(jobs_en)}")
    print(f"  • Adzuna Spanish: {len(jobs_es)}")
    print(f"  • OCC Mundial: {len(jobs_occ)}")
    print(f"  • Duplicates: {len(all_mexico_jobs) - len(unique_urls)}")

    # Show sample jobs
    if all_mexico_jobs:
        print(f"\nSample jobs found in Mexico:")
        for job in all_mexico_jobs[:5]:
            title = job.get('title', 'N/A')[:50]
            company = job.get('company', 'N/A')[:30]
            salary = job.get('salary_max', 'N/A')
            print(f"  • {title}")
            print(f"    Company: {company}, Salary: {salary}")

    print("\n" + "=" * 70)
    print("Next: These jobs would be saved with search_country='mx'")
    print("=" * 70)

asyncio.run(test_mexico_search())
