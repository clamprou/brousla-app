# Stripe Integration Review - Billing Correctness & Data Consistency

## Executive Summary

This review focuses on billing correctness and data consistency in the Stripe integration. Several critical issues were identified that could lead to billing errors, data inconsistencies, and incorrect subscription state handling.

---

## 1. Subscription States Handling

### ✅ Correctly Handled States
- `active` - Correctly mapped to "active"
- `trialing` - Correctly mapped to "active"
- `past_due` - Correctly mapped to "past_due" and allowed in execution checks
- `canceled`/`cancelled` - Correctly mapped to "cancelled"
- `unpaid` - Correctly mapped to "unpaid"

### ⚠️ Issues Found

#### Issue 1.1: Missing State Handling
**Location:** `api-server/app/stripe_service.py:302-315`

**Problem:** The code has a catch-all that maps unknown states to "expired", but several Stripe states are not explicitly handled:
- `incomplete` - Subscription created but payment not completed
- `incomplete_expired` - Payment attempt expired
- `paused` - Subscription paused (Billing Portal feature)

**Impact:** These states may be incorrectly treated as "expired", potentially blocking access when subscription is still valid or allowing access when it shouldn't.

**Recommendation:**
```python
# Add explicit handling for these states
elif status == "incomplete":
    our_status = "incomplete"
elif status == "incomplete_expired":
    our_status = "expired"
elif status == "paused":
    our_status = "paused"
```

#### Issue 1.2: past_due Access Logic
**Location:** `api-server/app/database.py:760-768`

**Problem:** Users with `past_due` status are allowed to execute workflows. While this may be intentional (grace period), there's no documentation or time limit on how long `past_due` access continues.

**Impact:** Users could potentially use the service indefinitely while in `past_due` state if Stripe doesn't eventually cancel.

**Recommendation:** Consider adding a grace period check (e.g., allow `past_due` for 7 days, then block).

#### Issue 1.3: Status Update on invoice.paid
**Location:** `api-server/app/stripe_service.py:362-405`

**Problem:** The `invoice.paid` handler always sets status to "active" without checking the actual subscription status from Stripe. If a subscription is `past_due` and payment succeeds, it should become `active`, but if the subscription was already `canceled`, it should remain `canceled`.

**Impact:** Could incorrectly reactivate a canceled subscription if an old invoice is paid.

**Recommendation:** Retrieve and check the actual subscription status before updating:
```python
subscription = stripe.Subscription.retrieve(subscription_id)
actual_status = subscription.status
if actual_status in ["active", "trialing"]:
    our_status = "active"
elif actual_status == "past_due":
    our_status = "past_due"
# ... handle other statuses
```

---

## 2. Webhook Event Ordering and Retries

### ⚠️ Critical Issues

#### Issue 2.1: No Idempotency Protection
**Location:** `api-server/app/stripe_service.py:84-408`

**Problem:** The webhook handler has **no idempotency protection**. Stripe can send the same event multiple times (retries, network issues). The code will process duplicate events, potentially:
- Updating subscription data multiple times
- Canceling old subscriptions multiple times
- Resetting usage counters multiple times

**Impact:** 
- Data inconsistency
- Potential double-charging scenarios
- Incorrect usage counts

**Recommendation:** Implement idempotency using Stripe event IDs:
```python
# Add event ID tracking table
# In handle_stripe_webhook:
event_id = event["id"]
if is_event_processed(event_id):
    logger.info(f"Event {event_id} already processed, skipping")
    return True  # Return True to acknowledge receipt

# Mark event as processed before processing
mark_event_processed(event_id)
```

#### Issue 2.2: No Event Ordering Guarantee
**Location:** `api-server/app/stripe_service.py:263-334` (customer.subscription.updated)

**Problem:** Webhook events can arrive out of order. For example:
1. `customer.subscription.updated` (status: canceled) arrives first
2. `invoice.paid` (old invoice) arrives later
3. The later event overwrites the cancellation

**Impact:** Subscription state could be incorrectly restored after cancellation.

**Recommendation:** 
1. Use event timestamps to ensure only newer events update state
2. Or check current Stripe subscription status before applying updates:
```python
# Before updating, verify current state in Stripe
current_subscription = stripe.Subscription.retrieve(subscription_id)
if current_subscription.status != subscription["status"]:
    # Subscription state changed since event was created
    # Use current state instead
    subscription["status"] = current_subscription.status
```

#### Issue 2.3: Webhook Response Handling
**Location:** `api-server/app/routes_subscription.py:341-370`

**Problem:** The webhook endpoint returns 200 even when `handle_stripe_webhook` returns `False` (event ignored). This is correct, but there's no distinction between:
- Event processed successfully
- Event ignored (not relevant)
- Event processing failed

**Impact:** Stripe will retry failed events, but we can't distinguish between "ignored" and "failed" for monitoring.

**Recommendation:** Return appropriate HTTP status codes:
```python
if event_handled:
    return {"status": "success"}
else:
    # Event was ignored (not an error)
    return {"status": "ignored"}, 200
# Errors should raise HTTPException (already done)
```

---

## 3. Cancel-at-Period-End Behavior

### ⚠️ Issues Found

#### Issue 3.1: Immediate Database Update
**Location:** `api-server/app/routes_subscription.py:219-229`

**Problem:** When canceling at period end, the code updates the database immediately with `cancel_at_period_end=True`, but doesn't wait for webhook confirmation. If the Stripe API call fails silently or the webhook arrives out of order, the database could be out of sync.

**Impact:** Database shows `cancel_at_period_end=True` but Stripe subscription might not be updated.

**Recommendation:** Verify the Stripe subscription was updated:
```python
subscription = stripe.Subscription.modify(
    stripe_subscription_id,
    cancel_at_period_end=True
)
# Verify the update succeeded
if not subscription.cancel_at_period_end:
    raise HTTPException(...)
```

#### Issue 3.2: Access During Cancel-at-Period-End
**Location:** `api-server/app/database.py:763-766`

**Problem:** Users with `cancel_at_period_end=True` and status "cancelled" can still access the service until `current_period_end`. However, the check only verifies `end_date` is not expired, but doesn't verify the subscription is still active in Stripe.

**Impact:** If Stripe cancels the subscription early (e.g., due to payment failure), the user might still have access until the local `current_period_end` date.

**Recommendation:** Consider checking Stripe subscription status for critical operations, or rely more heavily on webhook updates.

#### Issue 3.3: Missing Webhook for Period End
**Location:** `api-server/app/stripe_service.py` (all handlers)

**Problem:** When a subscription with `cancel_at_period_end=True` reaches the period end, Stripe sends `customer.subscription.deleted`. However, the handler only sets status to "cancelled" but doesn't handle the transition from "active" + `cancel_at_period_end=True` to fully cancelled.

**Impact:** Minor - the current handling should work, but the logic could be clearer.

**Recommendation:** Add explicit logging when a subscription with `cancel_at_period_end=True` is fully cancelled.

---

## 4. Failed Payments / past_due

### ⚠️ Critical Issues

#### Issue 4.1: Missing invoice.payment_failed Handler
**Location:** `api-server/app/stripe_service.py` (webhook handler)

**Problem:** The code does **not handle `invoice.payment_failed`** events. When a payment fails:
- Stripe sends `invoice.payment_failed`
- Subscription status may change to `past_due`
- But the code only handles `customer.subscription.updated` which may not fire immediately

**Impact:** 
- Database may not reflect `past_due` status immediately
- User might lose access unexpectedly
- No notification/logging of payment failures

**Recommendation:** Add handler:
```python
elif event_type == "invoice.payment_failed":
    invoice = data
    subscription_id = invoice.get("subscription")
    
    if subscription_id:
        # Update subscription to past_due
        user = get_user_by_stripe_subscription_id(subscription_id)
        if user:
            update_user_subscription(
                user_id=user["id"],
                status="past_due"
            )
            logger.warning(f"Payment failed for user {user['id']}, subscription {subscription_id}")
    return True
```

#### Issue 4.2: Missing invoice.payment_action_required Handler
**Location:** `api-server/app/stripe_service.py` (webhook handler)

**Problem:** For 3D Secure or other payment authentication, Stripe sends `invoice.payment_action_required`. The code doesn't handle this.

**Impact:** User might not be notified that payment requires action.

**Recommendation:** Add handler to notify user or update subscription status appropriately.

#### Issue 4.3: past_due Recovery Not Handled
**Location:** `api-server/app/stripe_service.py:362-405` (invoice.paid)

**Problem:** When a `past_due` subscription payment succeeds, `invoice.paid` fires and sets status to "active". However, if the subscription was already canceled due to prolonged `past_due`, this could incorrectly reactivate it.

**Impact:** Could reactivate subscriptions that should remain canceled.

**Recommendation:** Check subscription status before reactivating (see Issue 1.3).

---

## 5. Plan Changes and Proration

### ⚠️ Critical Issues

#### Issue 5.1: No Proration Handling
**Location:** `api-server/app/stripe_service.py:197-259` (checkout.session.completed)

**Problem:** When a user upgrades/downgrades, the code:
1. Creates a new checkout session (new subscription)
2. Cancels the old subscription
3. **Does not handle proration or billing cycle alignment**

**Impact:**
- Users may be charged twice (old subscription + new subscription)
- No credit for unused time on old plan
- Billing cycles may not align properly

**Recommendation:** Use Stripe's subscription modification API instead of creating new subscriptions:
```python
# Instead of creating new checkout session for upgrades:
existing_subscription = stripe.Subscription.retrieve(old_subscription_id)
stripe.Subscription.modify(
    old_subscription_id,
    items=[{
        'id': existing_subscription['items']['data'][0].id,
        'price': new_price_id,
    }],
    proration_behavior='create_prorations',  # or 'always_invoice'
    billing_cycle_anchor='unchanged'  # or 'now' for immediate
)
```

#### Issue 5.2: Old Subscription Cancellation Race Condition
**Location:** `api-server/app/stripe_service.py:197-259`

**Problem:** The code cancels the old subscription **after** creating the new one in the webhook handler. However:
- If the webhook for the new subscription arrives before the old subscription is fully canceled
- Or if the old subscription cancellation fails
- The user could have two active subscriptions

**Impact:** Double billing, incorrect usage limits.

**Recommendation:** 
1. Cancel old subscription **before** creating checkout session (in `create_checkout_session`)
2. Or use subscription modification instead of new subscription

#### Issue 5.3: Usage Reset on Upgrade
**Location:** `api-server/app/stripe_service.py:243-251`

**Problem:** When upgrading, the code resets `monthly_workflows_used` to 0. This is correct for a new billing cycle, but if the upgrade happens mid-cycle, the user loses their current month's usage count.

**Impact:** 
- User might exceed limits if upgrade happens mid-cycle
- Or user might get extra usage if downgrade happens mid-cycle

**Recommendation:** 
- For upgrades: Keep current usage, apply new limit immediately
- For downgrades: If usage exceeds new limit, block until reset or prorate

#### Issue 5.4: No Downgrade Handling
**Location:** `api-server/app/stripe_service.py` (all handlers)

**Problem:** The code doesn't explicitly handle downgrades. If a user downgrades:
- New subscription is created
- Old subscription is canceled
- But usage limits might not be enforced correctly if current usage exceeds new plan's limit

**Impact:** User might continue using higher-tier features after downgrade.

**Recommendation:** Check usage against new plan limit immediately on downgrade.

---

## 6. Additional Data Consistency Issues

### Issue 6.1: Missing Subscription Validation
**Location:** `api-server/app/database.py:714-794` (check_user_can_execute)

**Problem:** The execution check relies on local database state. If webhooks fail or are delayed, the database might be out of sync with Stripe.

**Impact:** Users might be blocked when they should have access, or vice versa.

**Recommendation:** Consider periodic sync job or optional Stripe API check for critical operations.

### Issue 6.2: Date Parsing Edge Cases
**Location:** `api-server/app/database.py:645-677` (increment_user_execution_count)

**Problem:** Date parsing uses `datetime.fromisoformat()` with timezone handling, but there are edge cases:
- Invalid date formats from database
- Timezone mismatches
- Missing dates

**Impact:** Monthly reset might not work correctly, leading to incorrect usage counts.

**Recommendation:** Add more robust date validation and logging.

### Issue 6.3: Concurrent Webhook Processing
**Location:** `api-server/app/routes_subscription.py:341-370`

**Problem:** If multiple webhook events arrive simultaneously for the same subscription, they could be processed concurrently, leading to race conditions.

**Impact:** Data corruption, incorrect subscription state.

**Recommendation:** Add locking mechanism (e.g., database-level lock on subscription row) or use async queue with single worker per subscription.

---

## Summary of Critical Issues

1. **No idempotency protection** - Duplicate webhook events will cause data corruption
2. **No proration handling** - Users may be double-charged on plan changes
3. **Missing payment failure handlers** - `invoice.payment_failed` not handled
4. **Race conditions in plan changes** - Old subscription cancellation timing issues
5. **No event ordering protection** - Out-of-order events can cause incorrect state

---

## Recommended Priority Fixes

### High Priority (Billing Impact)
1. Add idempotency protection for webhooks
2. Implement proper proration for plan changes
3. Add `invoice.payment_failed` handler
4. Fix old subscription cancellation in upgrade flow

### Medium Priority (Data Consistency)
5. Add event ordering protection
6. Add `invoice.payment_action_required` handler
7. Improve cancel-at-period-end validation
8. Add usage limit enforcement on downgrade

### Low Priority (Edge Cases)
9. Handle additional subscription states (`incomplete`, `paused`)
10. Add periodic subscription sync job
11. Improve date parsing robustness
12. Add concurrent webhook processing protection

