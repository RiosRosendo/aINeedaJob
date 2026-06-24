#!/usr/bin/env python3
"""Run batch job processing multiple times to score unprocessed jobs."""

import requests
import sys
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
USER_ID = os.getenv('USER_ID', '550e8400-e29b-41d4-a716-446655440000')

def process_batch(batch_num: int, batch_size: int = 10):
    """Run one batch of job processing."""
    print(f"\n[BATCH {batch_num}] Processing {batch_size} jobs...")

    try:
        response = requests.post(
            f'{API_BASE_URL}/api/jobs/process',
            params={'batch_size': batch_size},
            headers={'x-user-id': USER_ID},
            timeout=60
        )

        if response.status_code != 200:
            print(f"  ❌ Error: {response.status_code}")
            print(f"  {response.text}")
            return False

        data = response.json()
        print(f"  ✓ Processed: {data.get('jobs_processed', 0)} jobs")
        print(f"    - Apply: {data.get('applied', 0)}")
        print(f"    - Review: {data.get('review', 0)}")
        print(f"    - Ignored: {data.get('ignored', 0)}")

        return True

    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
        return False


def main():
    """Run batch processing N times."""
    num_batches = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"Starting {num_batches} batch(es) of {batch_size} jobs each...")
    print(f"Total jobs to process: {num_batches * batch_size}")
    print(f"API: {API_BASE_URL}")
    print(f"User: {USER_ID}")

    total_processed = 0
    total_applied = 0
    total_review = 0
    total_ignored = 0

    for i in range(1, num_batches + 1):
        try:
            response = requests.post(
                f'{API_BASE_URL}/api/jobs/process',
                params={'batch_size': batch_size},
                headers={'x-user-id': USER_ID},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                processed = data.get('jobs_processed', 0)
                applied = data.get('applied', 0)
                review = data.get('review', 0)
                ignored = data.get('ignored', 0)

                print(f"\n[BATCH {i}/{num_batches}] ✓ Processed {processed} jobs")
                print(f"  Apply: {applied}, Review: {review}, Ignored: {ignored}")

                total_processed += processed
                total_applied += applied
                total_review += review
                total_ignored += ignored

                if processed == 0:
                    print(f"  No more jobs to process. Stopping.")
                    break
            else:
                print(f"\n[BATCH {i}/{num_batches}] ❌ Error: {response.status_code}")
                print(f"  {response.text}")
                break

        except Exception as e:
            print(f"\n[BATCH {i}/{num_batches}] ❌ Exception: {str(e)}")
            break

    print(f"\n{'='*50}")
    print(f"SUMMARY: {total_processed} jobs processed")
    print(f"  Apply: {total_applied}")
    print(f"  Review: {total_review}")
    print(f"  Ignored: {total_ignored}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
