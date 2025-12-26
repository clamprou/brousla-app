# Usage Tracking, Limits, and Data Consistency Review

## Executive Summary

This review focuses on concurrency safety, atomic operations, usage reset timing, and limit bypass vulnerabilities in the usage tracking system. Several critical race conditions were identified that could allow users to exceed their limits.

---

## 1. Concurrency Safety Issues

### ⚠️ Critical Issue 1.1: TOCTOU Race Condition in Check-Then-Increment Pattern

**Location:** `api-server/app/routes_subscription.py:60-69`, `api-server/app/routes_ai.py:140-148`

**Problem:** The code follows a "check-then-increment" pattern:
1. Check if user can execute (`check_user_can_execute`)
2. If yes, increment count (`increment_user_execution_count`)

These are **two separate operations** with no locking mechanism between them.

**Race Condition Scenario:**
```
Time    Request A                    Request B                    Database State
─────────────────────────────────────────────────────────────────────────────
T1      check_user_can_execute()    (waiting)                    monthly_workflows_used = 499
T2      → returns True (499 < 500)   check_user_can_execute()     monthly_workflows_used = 499
T3      increment_user_execution()  → returns True (499 < 500)   monthly_workflows_used = 499
T4      → UPDATE ... + 1            increment_user_execution()    monthly_workflows_used = 500
T5      (commits)                   → UPDATE ... + 1            monthly_workflows_used = 501
T6      (done)                      (commits)                   monthly_workflows_used = 501
```

**Impact:** 
- Users can exceed their monthly limit
- Multiple concurrent requests can all pass the check and increment
- Limit of 500 could allow 501, 502, or more executions

**Evidence:**
- `routes_subscription.py:60-69`: Check then increment (separate calls)
- `routes_ai.py:140-148`: Check then increment (separate calls)
- No database-level locking or row-level locking
- No transaction isolation that prevents concurrent reads

**Recommendation:** Use atomic check-and-increment in a single database operation:
```python
def increment_user_execution_count_if_allowed(user_id: str) -> tuple[bool, str]:
    """Atomically check limit and increment if allowed."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get current state
        subscription = get_user_subscription(user_id)
        usage = get_user_usage(user_id)
        
        if not subscription:
            # Trial user
            cursor.execute("""
                UPDATE usage 
                SET trial_workflows_used = trial_workflows_used + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? 
                  AND trial_workflows_used < 5
            """, (user_id,))
            
            if cursor.rowcount == 0:
                return False, "Trial limit reached"
            return True, "OK"
        else:
            # Paid subscription - check limit and increment atomically
            # This requires fetching limit first, then using it in UPDATE
            # For now, use a subquery approach or fetch limit, then update with WHERE clause
            monthly_limit = get_monthly_workflow_limit_from_stripe(...)
            
            cursor.execute("""
                UPDATE usage 
                SET monthly_workflows_used = monthly_workflows_used + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? 
                  AND monthly_workflows_used < ?
            """, (user_id, monthly_limit))
            
            if cursor.rowcount == 0:
                return False, "Monthly limit reached"
            return True, "OK"
```

### ⚠️ Issue 1.2: No Row-Level Locking

**Location:** `api-server/app/database.py:601-692` (increment_user_execution_count)

**Problem:** SQLite uses connection-level locking, but the `get_db_connection()` context manager creates a new connection for each call. Multiple concurrent requests will get separate connections, allowing concurrent reads and writes.

**Impact:**
- Multiple transactions can read the same usage count simultaneously
- All can increment based on the same "old" value
- No serialization of concurrent increments

**Recommendation:** Use `BEGIN IMMEDIATE` transaction mode to acquire write lock immediately:
```python
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(str(_DB_FILE))
    conn.row_factory = sqlite3.Row
    # Acquire write lock immediately
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Note:** This helps but doesn't fully solve the check-then-increment race condition. The atomic check-and-increment approach is still needed.

---

## 2. Atomic Increments

### ✅ Partially Correct: SQL Increments Are Atomic

**Location:** `api-server/app/database.py:630, 677`

**Good:** The SQL UPDATE statements use atomic operations:
```sql
SET monthly_workflows_used = monthly_workflows_used + 1
```

This is atomic at the SQL level - the increment itself cannot be partially executed.

### ⚠️ Issue 2.1: Non-Atomic Check-and-Increment

**Problem:** While the SQL increment is atomic, the **check** happens in a separate operation before the increment. The overall "check-then-increment" is not atomic.

**Impact:** See Issue 1.1 - limits can be bypassed.

### ⚠️ Issue 2.2: Reset Logic Not Atomic with Increment

**Location:** `api-server/app/database.py:656-690`

**Problem:** The reset logic checks `if reset_dt <= now` and then either resets or increments. If two requests arrive at the exact reset boundary:
- Both can read `reset_dt <= now` as True
- Both can execute the reset branch
- The second reset overwrites the first

**Example:**
```
Time    Request A                    Request B                    Database State
─────────────────────────────────────────────────────────────────────────────
T1      Read reset_dt (Jan 1 00:00)  (waiting)                    monthly_workflows_used = 100
T2      reset_dt <= now? → True     Read reset_dt (Jan 1 00:00)   monthly_workflows_used = 100
T3      UPDATE ... SET = 1          reset_dt <= now? → True       monthly_workflows_used = 100
T4      (commits)                   UPDATE ... SET = 1           monthly_workflows_used = 1
T5      (done)                      (commits)                     monthly_workflows_used = 1
```

**Impact:**
- If a user had 100 executions and the month resets, concurrent requests could both reset to 1
- The first execution after reset might be lost
- Or worse: if one request increments and another resets, the increment could be lost

**Recommendation:** Use a single atomic UPDATE that handles both reset and increment:
```python
# Use a CASE statement or subquery to atomically check and update
cursor.execute("""
    UPDATE usage 
    SET monthly_workflows_used = CASE 
            WHEN last_reset_date IS NULL OR datetime(last_reset_date) <= datetime('now') 
            THEN 1 
            ELSE monthly_workflows_used + 1 
        END,
        last_reset_date = CASE 
            WHEN last_reset_date IS NULL OR datetime(last_reset_date) <= datetime('now') 
            THEN datetime('now', '+1 month', 'start of month')
            ELSE last_reset_date 
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = ?
""", (user_id,))
```

---

## 3. Usage Reset Timing

### ⚠️ Issue 3.1: Reset Happens During Increment, Not Proactively

**Location:** `api-server/app/database.py:656-690`

**Problem:** The reset check only happens when `increment_user_execution_count()` is called. If a user doesn't execute anything for a month, the counter won't reset until their next execution.

**Impact:**
- Minor: Not a security issue, but could cause confusion
- If a user has 499/500 executions and waits until next month, the counter should reset
- Currently, it only resets when they try to execute again

**Recommendation:** This is acceptable behavior, but consider adding a periodic cleanup job to reset counters for inactive users.

### ⚠️ Issue 3.2: Timezone Handling in Reset Logic

**Location:** `api-server/app/database.py:659-661`

**Problem:** The code uses `datetime.utcnow()` but stores ISO format strings. The timezone handling is inconsistent:
```python
reset_dt = datetime.fromisoformat(reset_date.replace('Z', '+00:00'))
if reset_dt.tzinfo:
    reset_dt = reset_dt.replace(tzinfo=None)  # Removes timezone info
now = datetime.utcnow()  # No timezone info
```

**Impact:**
- If `reset_date` has timezone info, it's stripped
- Comparison might be incorrect if timezones are involved
- Edge case: if database stores local time but code uses UTC

**Recommendation:** Standardize on UTC everywhere and ensure consistent timezone handling.

### ⚠️ Issue 3.3: Reset Boundary Race Condition

**Location:** `api-server/app/database.py:664-672`

**Problem:** At the exact moment of reset (e.g., Jan 1 00:00:00 UTC), multiple concurrent requests can all see `reset_dt <= now` as True and all execute the reset branch.

**Impact:** See Issue 2.2 - concurrent resets can overwrite each other.

---

## 4. Limit Bypass Vulnerabilities

### 🔴 Critical: Limits Can Be Bypassed via Concurrent Requests

**Location:** Multiple locations (see Issue 1.1)

**Attack Vector:**
1. User has 499/500 executions remaining
2. User sends 10 concurrent requests simultaneously
3. All 10 requests pass `check_user_can_execute()` (all see 499 < 500)
4. All 10 requests increment the counter
5. User now has 509/500 executions

**Proof of Concept:**
```python
# Concurrent requests (simulated)
import asyncio
import aiohttp

async def execute_workflow(session, token):
    # Check
    async with session.post('/api/subscription/check-execution', 
                          headers={'Authorization': f'Bearer {token}'}) as resp:
        data = await resp.json()
        if data['can_execute']:
            # Increment
            async with session.post('/api/subscription/increment-execution',
                                  headers={'Authorization': f'Bearer {token}'}) as resp2:
                return await resp2.json()

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [execute_workflow(session, token) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        # All 10 requests could pass the check and increment
```

**Impact:**
- Users can exceed their plan limits
- Revenue loss (users getting more than they paid for)
- Unfair advantage over other users

### ⚠️ Issue 4.2: No Rate Limiting on Increment Endpoint

**Location:** `api-server/app/routes_subscription.py:49-78`

**Problem:** The `/increment-execution` endpoint has no rate limiting. A malicious user could:
1. Spam the increment endpoint
2. Even if checks are added, rapid requests could exploit timing windows

**Recommendation:** Add rate limiting to increment endpoints (e.g., max 1 request per second per user).

### ⚠️ Issue 4.3: Internal Endpoint Has Same Vulnerability

**Location:** `api-server/app/routes_subscription.py:169-202`

**Problem:** The internal endpoint (`/increment-execution-internal`) has the same check-then-increment pattern. While it's only accessible from localhost, if the workflow server makes concurrent calls, the same race condition exists.

---

## 5. Additional Data Consistency Issues

### Issue 5.1: Trial Limit Check After Increment

**Location:** `api-server/app/database.py:636-637`

**Problem:** The trial limit check happens AFTER incrementing:
```python
cursor.execute("UPDATE ... SET trial_workflows_used = trial_workflows_used + 1 ...")
if new_trial_used >= 5:
    _deactivate_all_user_workflows(user_id)
```

**Impact:**
- If user is at 4/5 and makes a request, they'll increment to 5/5
- The check happens after, so they've already used their 5th execution
- This is actually correct behavior, but the variable `new_trial_used` is calculated before the increment, which could be misleading

**Recommendation:** The logic is correct, but the variable name is misleading. Consider checking the database value after increment.

### Issue 5.2: No Validation of Increment Result

**Location:** `api-server/app/database.py:601-692`

**Problem:** After incrementing, the code doesn't verify that the increment actually happened. If the UPDATE fails silently (e.g., user_id doesn't exist), the function returns normally.

**Impact:**
- Silent failures could go unnoticed
- Usage might not be tracked correctly

**Recommendation:** Check `cursor.rowcount` after UPDATE to ensure the row was actually updated.

---

## Summary of Critical Issues

1. **🔴 CRITICAL: TOCTOU Race Condition** - Limits can be bypassed via concurrent requests
2. **🔴 CRITICAL: Reset Boundary Race Condition** - Concurrent resets can cause data loss
3. **⚠️ HIGH: No Atomic Check-and-Increment** - Separate check and increment operations
4. **⚠️ MEDIUM: No Row-Level Locking** - Concurrent transactions can interfere
5. **⚠️ MEDIUM: No Rate Limiting** - Increment endpoints can be spammed

---

## Recommended Priority Fixes

### High Priority (Security & Billing Impact)
1. **Implement atomic check-and-increment** - Combine check and increment in a single SQL operation with WHERE clause
2. **Add row-level locking** - Use `BEGIN IMMEDIATE` to acquire write locks early
3. **Fix reset logic** - Use atomic CASE statement for reset-or-increment

### Medium Priority (Data Consistency)
4. **Add rate limiting** - Limit increment requests to prevent abuse
5. **Validate increment results** - Check `cursor.rowcount` after UPDATE
6. **Standardize timezone handling** - Use UTC consistently everywhere

### Low Priority (Edge Cases)
7. **Add periodic reset job** - Reset counters for inactive users
8. **Improve error handling** - Better logging and validation

---

## Example Fix: Atomic Check-and-Increment

```python
def increment_user_execution_count_if_allowed(user_id: str) -> tuple[bool, str]:
    """
    Atomically check limit and increment if allowed.
    Returns (success: bool, message: str)
    """
    from datetime import datetime
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get subscription and limit
        subscription = get_user_subscription(user_id)
        usage = get_user_usage(user_id)
        
        if not subscription:
            # Trial user - atomic increment with limit check
            cursor.execute("""
                UPDATE usage 
                SET trial_workflows_used = trial_workflows_used + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? 
                  AND trial_workflows_used < 5
            """, (user_id,))
            
            if cursor.rowcount == 0:
                # Check if limit reached or user doesn't exist
                cursor.execute("SELECT trial_workflows_used FROM usage WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row and row[0] >= 5:
                    return False, "Free trial limit reached. Please upgrade to continue using AI workflows."
                return False, "Usage record not found"
            
            # Check if we just hit the limit
            cursor.execute("SELECT trial_workflows_used FROM usage WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[0] >= 5:
                _deactivate_all_user_workflows(user_id)
            
            return True, "OK"
        else:
            # Paid subscription
            monthly_limit = get_monthly_workflow_limit_from_stripe(
                subscription.get("stripe_price_id")
            )
            
            if monthly_limit is None:
                # Fallback to default limits
                plan = subscription.get("subscription_plan")
                monthly_limit = {"basic": 500, "plus": 2000, "pro": 5000}.get(plan, 0)
            
            # Atomic increment with limit check and reset logic
            now = datetime.utcnow()
            next_month_start = _first_day_next_month(now).isoformat()
            
            cursor.execute("""
                UPDATE usage 
                SET monthly_workflows_used = CASE 
                        WHEN last_reset_date IS NULL 
                             OR datetime(last_reset_date) <= datetime(?)
                        THEN 1
                        ELSE monthly_workflows_used + 1
                    END,
                    last_reset_date = CASE 
                        WHEN last_reset_date IS NULL 
                             OR datetime(last_reset_date) <= datetime(?)
                        THEN ?
                        ELSE last_reset_date
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? 
                  AND (
                    -- Reset case: allow if reset needed
                    (last_reset_date IS NULL OR datetime(last_reset_date) <= datetime(?))
                    OR
                    -- Increment case: allow if under limit
                    (datetime(last_reset_date) > datetime(?) AND monthly_workflows_used < ?)
                  )
            """, (now.isoformat(), now.isoformat(), next_month_start, user_id, 
                  now.isoformat(), now.isoformat(), monthly_limit))
            
            if cursor.rowcount == 0:
                # Check why it failed
                cursor.execute("""
                    SELECT monthly_workflows_used, last_reset_date 
                    FROM usage 
                    WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                if row:
                    used = row[0] or 0
                    if used >= monthly_limit:
                        return False, f"Monthly execution limit reached ({used}/{monthly_limit}). Please upgrade your plan for more executions."
                return False, "Usage record not found"
            
            return True, "OK"
```

This approach:
- ✅ Atomically checks limit and increments in a single SQL operation
- ✅ Prevents concurrent requests from bypassing limits
- ✅ Handles reset logic atomically
- ✅ Returns clear error messages

