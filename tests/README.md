# aINeedJob Test Suite

End-to-end tests for the V1 job search pipeline.

## What This Tests

The `test_pipeline.py` script validates the complete workflow:

1. **Job Discovery** — Search Adzuna + The Muse (mocked)
2. **Job Saving** — Deduplication + database persistence
3. **Job Parsing** — Extract structured fields via LLM (mocked)
4. **Job Scoring** — Hard filters + skill overlap + LLM scoring (mocked)
5. **Decision Routing** — Route based on fit score (apply/review/ignore)

## Key Testing Strategies

- **All external APIs mocked**: Adzuna, The Muse, LLM calls are intercepted
- **Real database**: Uses actual PostgreSQL (test data cleaned up after)
- **Fixture-based cleanup**: `setup_test_user` fixture creates and destroys test data
- **No API credits consumed**: All LLM calls and API calls are mocked
- **Clear assertions**: Each test validates specific behavior

## Running the Tests

### Prerequisites
```bash
pip install pytest pytest-mock
```

### Run all tests
```bash
pytest tests/test_pipeline.py -v
```

### Run specific test
```bash
pytest tests/test_pipeline.py::TestPipelineEndToEnd::test_01_job_discovery_adzuna -v
```

### Run with output
```bash
pytest tests/test_pipeline.py -v -s
```

## Test Structure

```
TestPipelineEndToEnd
├── test_01_job_discovery_adzuna     — Mock Adzuna API, verify jobs returned
├── test_02_job_discovery_themuse    — Mock The Muse API, verify jobs returned
├── test_03_save_jobs                — Verify deduplication + DB persistence
├── test_04_parse_job                — Mock LLM, verify field extraction
├── test_05_score_job                — Mock LLM, verify scoring + hard filters
└── test_06_decision_routing         — Verify routing (score >= 85 → apply)

test_summary()                        — Print final test summary
```

## Fixtures

### `setup_test_user`
- Creates test user in `users` table
- Creates test profile in `user_profiles` table
- Cleans up all test data after test completes

## Mocking Strategy

### External APIs
- **Adzuna**: Mocked to return 1 mock job
- **The Muse**: Mocked to return 1 mock job

### LLM Calls
- **Parse**: Returns mock parsed job with title, skills, salary, etc.
- **Score**: Returns mock score (88/100) with decision "apply"

### What's NOT Mocked
- **Database**: Real PostgreSQL queries (test data cleaned up)
- **Tool functions**: Actual tool code runs (search_adzuna, parse_job, etc.)

## Expected Output

```
test_pipeline.py::TestPipelineEndToEnd::test_01_job_discovery_adzuna PASSED
test_pipeline.py::TestPipelineEndToEnd::test_02_job_discovery_themuse PASSED
test_pipeline.py::TestPipelineEndToEnd::test_03_save_jobs PASSED
test_pipeline.py::TestPipelineEndToEnd::test_04_parse_job PASSED
test_pipeline.py::TestPipelineEndToEnd::test_05_score_job PASSED
test_pipeline.py::TestPipelineEndToEnd::test_06_decision_routing PASSED
test_pipeline.py::test_summary PASSED

======================================================================
PIPELINE TEST SUMMARY
======================================================================

✓ TEST 1: Job Discovery (Adzuna) - Mock API returns jobs
✓ TEST 2: Job Discovery (The Muse) - Mock API returns jobs
✓ TEST 3: Save Jobs - Database persistence + deduplication
✓ TEST 4: Parse Job - LLM extraction (mocked)
✓ TEST 5: Score Job - Hard filters + skill overlap + LLM scoring
✓ TEST 6: Decision Routing - Routes based on score

All tests passed! Pipeline is working end-to-end.
```

## Manual API Testing (Later)

Once you're ready to test against real APIs, create a separate test file with real credentials:

```python
# tests/test_pipeline_live.py (NOT COMMITTED)
# Use real API keys from .env
# Run with: pytest tests/test_pipeline_live.py --real-apis
```

This suite focuses on **logic correctness**, not external dependencies.

## Adding New Tests

1. Add method to `TestPipelineEndToEnd` class
2. Use `setup_test_user` fixture for test data
3. Mock external APIs
4. Assert on database state
5. Cleanup happens automatically

Example:
```python
def test_07_my_feature(self, setup_test_user):
    """Test: My new feature."""
    print("\n[TEST 7] My Feature")
    # Test code here
    print("  ✓ Feature works")
```
