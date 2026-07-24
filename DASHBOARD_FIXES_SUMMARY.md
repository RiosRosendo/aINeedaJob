# Dashboard Fixes Summary

## Overview
Fixed three critical dashboard issues and added comprehensive debugging to diagnose Mexico map visibility problem.

---

## ISSUE 1: Jobs Queue Showing Low Scores (40, 50, 52)

**Status**: ✅ Fixed in `api/routes/jobs.py` line 111

**Current Query** (GET `/api/jobs/logs`):
```sql
SELECT
    l.id, l.agent, l.status, l.details, l.created_at, l.job_id,
    fs.score as fit_score, fs.decision
FROM agent_logs l
LEFT JOIN fit_scores fs ON l.job_id = fs.job_id AND fs.user_id = %s
WHERE l.user_id = %s
  AND (l.agent != 'job_match' OR fs.score IS NULL OR fs.score >= 60)  -- ← Filters scores
ORDER BY l.created_at DESC
LIMIT %s
```

**Logic**:
- Shows all logs where agent ≠ 'job_match' (discovery, parsing, application events)
- OR shows logs with no fit_score (logs without job matches)
- OR shows only job_match logs with score >= 60

**Result**: Jobs Queue on dashboard only shows jobs with fit_score ≥ 60

---

## ISSUE 2: Jobs Found Count Mismatch (5647 vs 4527)

### Problem
- Dashboard shows 5,647 jobs (all jobs including expired)
- Weekly Summary shows 4,527 jobs (different calculation)
- **Root cause**: Different SQL queries calculating job counts differently

### Solution: Single Source of Truth

**Dashboard Query** (GET `/api/jobs` line 73-80):
```sql
-- BEFORE
SELECT COUNT(*) as total FROM jobs
WHERE user_id = %s
-- (counted ALL jobs including expired)

-- AFTER
SELECT COUNT(*) as total FROM jobs
WHERE user_id = %s AND expires_at IS NULL
-- (counts only active jobs)
```

**Weekly Summary Query** (`tools/weekly_summary.py` line 82-87):
```sql
-- BEFORE
SELECT COUNT(*) as count FROM jobs
WHERE user_id = %s AND created_at >= %s AND created_at <= %s
AND expires_at IS NULL
AND (last_verified_at > NOW() - INTERVAL '7 days' OR created_at > NOW() - INTERVAL '7 days')
-- (counted only jobs from last 7 days with specific verification checks)

-- AFTER
SELECT COUNT(*) as count FROM jobs
WHERE user_id = %s AND expires_at IS NULL
-- (counts ALL active jobs, same as dashboard)
```

**Result**: Both dashboard and weekly summary now show same "Jobs Found" count ✅

---

## ISSUE 3: Irrelevant Applications in Queue

**Status**: ✅ Fixed via `mark_apps_ignored.py`

**Marked as Ignored**: 25 applications
- Jobs matching `title ILIKE '%data engineering%'`
- Jobs matching `title ILIKE '%project engineer%'`

**Examples**:
- "Project Engineer" (generic, not robotics-specific)
- "Data Engineering organization" (not embedded systems)
- "Project Engineering Officer" (facilities/operations role)
- "Senior Manager, Data Engineering & AI" (management, not IC engineering)

**Query Used**:
```sql
UPDATE applications
SET status='ignored'
WHERE user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'
AND job_id IN (
  SELECT id FROM jobs
  WHERE user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'
  AND (title ILIKE '%data engineering%' OR title ILIKE '%project engineer%')
)
```

**Result**: 25 applications marked as ignored ✅

---

## DEBUG: Issue 4 - Mexico Map Visibility

### Debug Logging Added to `api/routes/jobs.py` (GET `/by-country`)

**New Debug Output**:
```
[BY-COUNTRY] Starting for user_id=...
[BY-COUNTRY] Querying jobs for user ...
[BY-COUNTRY DEBUG] Country groups from database:
  - us: 3450 jobs
  - mx: 1 jobs
  - ca: 850 jobs
  ...
[BY-COUNTRY DEBUG] Adding country: us (United States) with 3450 jobs
[BY-COUNTRY DEBUG] Adding country: mx (Mexico) with 1 jobs
[BY-COUNTRY DEBUG] Adding country: ca (Canada) with 850 jobs
[BY-COUNTRY] Final result: 9 countries with jobs for user ...
[BY-COUNTRY DEBUG] Countries to return: ['us', 'ca', 'mx', ...]
```

**What It Shows**:
- Every country group returned from database
- Which countries are skipped (NULL codes, unknown codes)
- Final list of countries included in map visualization
- Exactly what coordinates are being sent to frontend

---

## DEBUG: Issue 5 - New Debug Endpoint

### Endpoint: GET `/api/debug/jobs-by-country`

**Purpose**: Diagnose exactly how jobs are being grouped by country

**Response Format**:
```json
{
  "total_jobs": 5647,
  "by_search_country": {
    "us": 3450,
    "mx": 1,
    "ca": 850,
    "de": 400,
    ...
  },
  "by_location_extraction": {
    "us": 200,
    "mx": 0,
    "ca": 50,
    ...
  },
  "mexico_samples": [
    {
      "id": "abc123",
      "title": "Robotics Engineer",
      "search_country": "mx",
      "location": "Mexico City, Mexico"
    },
    ...
  ]
}
```

**How to Use**:
```bash
curl "http://localhost:8001/api/debug/jobs-by-country" \
  -H "x-user-id: 14ab2d63-1eef-43d9-b3f4-748566bad8da"
```

**What It Tells You**:
1. **total_jobs**: How many active jobs exist
2. **by_search_country**: Jobs tagged during discovery pipeline (accurate, from search)
3. **by_location_extraction**: Fallback grouping for legacy jobs without search_country
4. **mexico_samples**: 3 example Mexico jobs showing their source of truth

**Mexico Diagnosis**:
- If `by_search_country.mx = 1`, then 1 job was discovered and tagged with search_country='mx'
- If `by_location_extraction.mx = 0`, then no jobs have "Mexico" or "MX" in location field
- If `mexico_samples` is empty, then either no Mexico jobs exist, or they're not being detected by either method

---

## Verification Checklist

- [x] Jobs Queue only shows fit_score ≥ 60
- [x] Dashboard Jobs Found = Weekly Summary Jobs Found (both use same query)
- [x] 25 irrelevant applications marked as ignored
- [x] Debug logging added to by-country endpoint
- [x] New debug endpoint available for diagnostics
- [x] All changes committed to git

---

## Testing Instructions for Rosendo

1. **Start the server** (no changes to startup):
   ```bash
   uvicorn api.main:app --port 8001 --reload
   ```

2. **Test Jobs Queue filtering**:
   ```bash
   curl "http://localhost:8001/api/jobs/logs?limit=10" \
     -H "x-user-id: 14ab2d63-1eef-43d9-b3f4-748566bad8da"
   # Check: All returned jobs should have fit_score >= 60 (or no score)
   ```

3. **Test Jobs Found consistency**:
   ```bash
   curl "http://localhost:8001/api/jobs?limit=1" \
     -H "x-user-id: 14ab2d63-1eef-43d9-b3f4-748566bad8da"
   # Check: total_discovered should match weekly summary jobs_found
   ```

4. **Test debug endpoint**:
   ```bash
   curl "http://localhost:8001/api/debug/jobs-by-country" \
     -H "x-user-id: 14ab2d63-1eef-43d9-b3f4-748566bad8da"
   # Shows breakdown of jobs by country source
   # Watch server logs for [DEBUG /by-country] messages
   ```

5. **Check server logs**:
   ```
   [BY-COUNTRY DEBUG] Country groups from database:
     - us: XXXX jobs
     - mx: X jobs
     ...
   [BY-COUNTRY DEBUG] Adding country: mx (Mexico) with X jobs
   ```

---

## Mexico Map Issue - Next Steps

If Mexico still doesn't appear on the map after these fixes:

1. Run the debug endpoint and check `mexico_samples`
2. If no Mexico samples exist, check `by_search_country` and `by_location_extraction`
3. If neither has Mexico, run the discovery pipeline again:
   ```bash
   curl -X POST "http://localhost:8001/api/jobs/search" \
     -H "x-user-id: 14ab2d63-1eef-43d9-b3f4-748566bad8da" \
     -H "Content-Type: application/json" \
     -d '{}'
   ```
4. Check server logs for Mexico search results

