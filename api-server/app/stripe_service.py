"""Stripe integration for subscription management."""
import os
import logging
from typing import Optional, Tuple
import stripe
from app.config import settings
from app.database import (
    update_user_subscription, 
    get_user_by_id, 
    get_user_by_stripe_subscription_id,
    is_stripe_event_processed,
    mark_stripe_event_processed
)
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key or os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = settings.stripe_webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Plan price IDs - these should be set in environment variables or config
STRIPE_BASIC_PRICE_ID = settings.stripe_basic_price_id or os.getenv("STRIPE_BASIC_PRICE_ID", "")
STRIPE_PLUS_PRICE_ID = settings.stripe_plus_price_id or os.getenv("STRIPE_PLUS_PRICE_ID", "")
STRIPE_PRO_PRICE_ID = settings.stripe_pro_price_id or os.getenv("STRIPE_PRO_PRICE_ID", "")


def create_checkout_session(user_id: str, user_email: str, plan: str) -> Tuple[str, str]:
    """
    Create a Stripe checkout session for subscription, or modify existing subscription.
    
    If user has an existing subscription, modifies it with proration instead of creating new.
    If user has no subscription, creates a new checkout session.
    
    Args:
        user_id: User ID
        user_email: User email
        plan: Subscription plan ('basic', 'plus', or 'pro')
    
    Returns:
        (checkout_url, session_id)
        For new subscriptions: (checkout_url, session_id)
        For existing subscriptions: ("modified", subscription_id) - frontend should handle this
    """
    if not stripe.api_key:
        raise ValueError("STRIPE_SECRET_KEY not configured")
    
    if plan == "basic":
        price_id = STRIPE_BASIC_PRICE_ID
    elif plan == "plus":
        price_id = STRIPE_PLUS_PRICE_ID
    elif plan == "pro":
        price_id = STRIPE_PRO_PRICE_ID
    else:
        raise ValueError(f"Invalid plan: {plan}")
    
    if not price_id:
        raise ValueError(f"Stripe price ID not configured for plan: {plan}")
    
    # Check if user has existing subscription
    from app.database import get_user_subscription
    existing_subscription = get_user_subscription(user_id)
    
    if existing_subscription and existing_subscription.get("stripe_subscription_id"):
        # User has existing subscription - modify it instead of creating new
        stripe_subscription_id = existing_subscription["stripe_subscription_id"]
        current_price_id = existing_subscription.get("stripe_price_id")
        
        # Check if they're trying to change to the same plan
        if current_price_id == price_id:
            raise ValueError(f"User is already on the {plan} plan")
        
        try:
            # Retrieve current subscription to get subscription item ID
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            
            # Get the subscription item ID (needed for modification)
            if not subscription.get("items") or len(subscription["items"]["data"]) == 0:
                raise ValueError("Subscription has no items")
            
            subscription_item_id = subscription["items"]["data"][0].id
            
            # Modify subscription with proration
            modified_subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                items=[{
                    "id": subscription_item_id,
                    "price": price_id,
                }],
                proration_behavior="create_prorations",  # Create prorations for plan change
                billing_cycle_anchor="unchanged",  # Keep billing cycle unchanged
                metadata={
                    "user_id": user_id,
                    "plan": plan,
                    "price_id": price_id
                }
            )
            
            # Update database immediately (webhook will also update, but this ensures consistency)
            update_user_subscription(
                user_id=user_id,
                plan=plan,
                stripe_price_id=price_id,
                status="active"  # Keep active during plan change
            )
            
            logger.info(f"Modified subscription {stripe_subscription_id} for user {user_id} to plan {plan} with proration")
            
            # Return special value to indicate modification (not checkout)
            # Frontend should handle this case differently
            return "modified", stripe_subscription_id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error modifying subscription: {e}")
            raise Exception(f"Failed to modify subscription: {str(e)}")
    
    # No existing subscription - create new checkout session
    # Get app base URL for success/cancel URLs
    app_base_url = getattr(settings, "app_base_url", "http://localhost:5173")
    
    try:
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{app_base_url}/profile?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{app_base_url}/profile?cancelled=true",
            metadata={
                "user_id": user_id,
                "plan": plan,
                "price_id": price_id
            },
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "plan": plan,
                    "price_id": price_id
                }
            }
        )
        
        return session.url, session.id
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise Exception(f"Failed to create checkout session: {str(e)}")


def _should_process_subscription_event(event: dict, subscription_id: str) -> bool:
    """
    Check if a subscription-related event should be processed based on timestamp.
    
    Fetches current subscription from Stripe and compares event timestamp with
    subscription's updated timestamp to prevent out-of-order events from overwriting newer state.
    
    Args:
        event: Stripe webhook event object
        subscription_id: Stripe subscription ID
    
    Returns:
        True if event should be processed (event is newer or equal), False if event is older
    """
    try:
        # Get event timestamp
        event_created = event.get("created")
        if not event_created:
            # If event has no timestamp, process it (shouldn't happen, but be safe)
            logger.warning(f"Event {event.get('id')} has no created timestamp, processing anyway")
            return True
        
        event_timestamp = datetime.fromtimestamp(event_created)
        
        # Fetch current subscription from Stripe to get its updated timestamp
        try:
            current_subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Get subscription's updated timestamp (when it was last modified in Stripe)
            # Stripe subscriptions have 'updated' field which is a Unix timestamp
            subscription_updated = current_subscription.get("updated")
            if subscription_updated:
                subscription_timestamp = datetime.fromtimestamp(subscription_updated)
                
                # Only process if event is newer than or equal to current subscription state
                if event_timestamp < subscription_timestamp:
                    logger.info(
                        f"Skipping event {event.get('id')} for subscription {subscription_id}: "
                        f"event timestamp ({event_timestamp.isoformat()}) is older than "
                        f"current subscription state ({subscription_timestamp.isoformat()})"
                    )
                    return False
                else:
                    logger.debug(
                        f"Processing event {event.get('id')}: event timestamp ({event_timestamp.isoformat()}) "
                        f"is newer than or equal to subscription state ({subscription_timestamp.isoformat()})"
                    )
                    return True
            else:
                # No updated timestamp on subscription, process the event
                logger.debug(f"Subscription {subscription_id} has no updated timestamp, processing event")
                return True
                
        except stripe.error.StripeError as e:
            # If we can't retrieve subscription, log warning but process event anyway
            # (subscription might have been deleted, or API issue)
            logger.warning(f"Could not retrieve subscription {subscription_id} to check timestamp: {e}. Processing event anyway.")
            return True
            
    except Exception as e:
        # If timestamp comparison fails, process event anyway (fail open)
        logger.warning(f"Error checking event timestamp for subscription {subscription_id}: {e}. Processing event anyway.")
        return True


def handle_stripe_webhook(payload: bytes, sig_header: str) -> bool:
    """
    Handle Stripe webhook events.
    
    Args:
        payload: Raw webhook payload
        sig_header: Stripe signature header
    
    Returns:
        True if event was handled, False if ignored
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured, skipping webhook verification")
        return False
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return False
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return False
    
    # Check idempotency - skip if event already processed
    event_id = event.get("id")
    if event_id:
        if is_stripe_event_processed(event_id):
            logger.info(f"Event {event_id} already processed, skipping (idempotency)")
            return True  # Return True to acknowledge receipt to Stripe
    
    # Mark event as processed before processing (prevents race conditions)
    # If processing fails, the event will still be marked, preventing infinite retries
    if event_id:
        mark_stripe_event_processed(event_id)
    
    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info(f"Received Stripe webhook: {event_type} (event_id: {event_id})")
    
    if event_type == "checkout.session.completed":
        # Subscription was created
        session = data
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        plan = metadata.get("plan")
        price_id = metadata.get("price_id")  # Read price_id from session metadata
        subscription_id = session.get("subscription")
        
        if not user_id or not subscription_id:
            logger.warning(f"checkout.session.completed missing required fields: user_id={user_id}, subscription_id={subscription_id}")
            return False
        
        # Get subscription details
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            customer_id = subscription.customer
        except Exception as e:
            logger.error(f"Error retrieving subscription {subscription_id}: {e}")
            return False
        
        # Get plan from price metadata
        plan_from_metadata = plan
        
        # Use price_id from session metadata if available, otherwise get from subscription
        if not price_id and subscription.get("items") and len(subscription["items"]["data"]) > 0:
            price_id = subscription["items"]["data"][0].get("price", {}).get("id")
        
        if price_id:
            try:
                price = stripe.Price.retrieve(price_id)
                price_metadata = price.get("metadata", {})
                # Get plan from price metadata
                plan_from_metadata = price_metadata.get("plan", plan)
            except stripe.error.StripeError as e:
                logger.error(f"Error retrieving price {price_id}: {e}")
        
        # Calculate dates (optional metadata - don't block update if unavailable)
        current_period_start = None
        current_period_end = None
        cancel_at_period_end = False
        
        # Try to access current_period_start/end - dates are in items.data[0] for flexible billing
        try:
            # First try root level (for standard subscriptions)
            if hasattr(subscription, 'current_period_start') and subscription.current_period_start:
                current_period_start = datetime.fromtimestamp(subscription.current_period_start)
                current_period_end = datetime.fromtimestamp(subscription.current_period_end)
                cancel_at_period_end = getattr(subscription, 'cancel_at_period_end', False) or False
            # Try dictionary access at root level
            elif subscription.get("current_period_start") if hasattr(subscription, 'get') else None:
                current_period_start = datetime.fromtimestamp(subscription["current_period_start"])
                current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
                cancel_at_period_end = subscription.get("cancel_at_period_end", False) if hasattr(subscription, 'get') else False
            # Fallback: get from items.data[0] (for flexible billing subscriptions)
            else:
                items = subscription.get("items") if hasattr(subscription, 'get') else getattr(subscription, 'items', None)
                if items:
                    items_data = items.get("data") if hasattr(items, 'get') else (items.data if hasattr(items, 'data') else None)
                    if items_data and len(items_data) > 0:
                        first_item = items_data[0]
                        # Get period dates from subscription item
                        item_period_start = first_item.get("current_period_start") if hasattr(first_item, 'get') else getattr(first_item, 'current_period_start', None)
                        item_period_end = first_item.get("current_period_end") if hasattr(first_item, 'get') else getattr(first_item, 'current_period_end', None)
                        
                        if item_period_start and item_period_end:
                            current_period_start = datetime.fromtimestamp(item_period_start)
                            current_period_end = datetime.fromtimestamp(item_period_end)
                            cancel_at_period_end = subscription.get("cancel_at_period_end", False) if hasattr(subscription, 'get') else getattr(subscription, 'cancel_at_period_end', False) or False
                        else:
                            raise ValueError("Period dates not found in subscription items")
                    else:
                        raise ValueError("No subscription items found")
                else:
                    raise ValueError("Subscription items not accessible")
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Could not retrieve subscription dates for {subscription_id}: {e}. Continuing without dates.")
        
        # Update user subscription with metadata from Stripe
        # Dates are optional - never block update if dates are unavailable
        try:
            # Check if this is a new subscription or an existing one being updated
            from app.database import get_user_subscription, get_db_connection
            existing_subscription = get_user_subscription(user_id)
            
            # If user already has this subscription ID, it's an update (plan change via modify)
            # If user has a different subscription ID, it's a new subscription (shouldn't happen with modify, but handle it)
            is_new_subscription = not existing_subscription or existing_subscription.get("stripe_subscription_id") != subscription_id
            
            update_user_subscription(
                user_id=user_id,
                plan=plan_from_metadata,
                status="active",
                stripe_subscription_id=subscription_id,
                stripe_price_id=price_id,
                current_period_start=current_period_start.isoformat() if current_period_start else None,
                current_period_end=current_period_end.isoformat() if current_period_end else None,
                cancel_at_period_end=cancel_at_period_end
            )
            
            if is_new_subscription:
                logger.info(f"Created new subscription for user {user_id}: {plan_from_metadata}, price_id: {price_id}")
                # Reset monthly workflows for new subscription (not for plan changes)
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE usage 
                        SET monthly_workflows_used = 0,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (user_id,))
                    conn.commit()
            else:
                logger.info(f"Updated subscription for user {user_id}: {plan_from_metadata}, price_id: {price_id}")
                # For plan changes, keep usage count (proration handles billing)
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {e}")
            return False
        
        return True
    
    elif event_type == "customer.subscription.updated":
        # Subscription was updated (e.g., plan change, renewal)
        subscription = data
        subscription_id = subscription["id"]
        customer_id = subscription["customer"]
        
        # Check event ordering - don't process if event is older than current subscription state
        if not _should_process_subscription_event(event, subscription_id):
            logger.info(f"Skipping out-of-order event {event_id} for subscription {subscription_id}")
            return True  # Return True to acknowledge receipt, but don't process
        
        # Try to find user by subscription ID first
        user = get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            # Fall back to metadata
            metadata = subscription.get("metadata", {})
            user_id = metadata.get("user_id")
            if not user_id:
                logger.warning(f"Could not find user for subscription {subscription_id}")
                return False
        else:
            user_id = user["id"]
        
        # Get plan from price metadata
        plan = None
        price_id = None
        
        if subscription.get("items") and len(subscription["items"]["data"]) > 0:
            price_id = subscription["items"]["data"][0].get("price", {}).get("id")
            if price_id:
                try:
                    price = stripe.Price.retrieve(price_id)
                    price_metadata = price.get("metadata", {})
                    # Get plan from price metadata
                    plan = price_metadata.get("plan")
                except stripe.error.StripeError as e:
                    logger.error(f"Error retrieving price {price_id}: {e}")
        
        # Fallback to subscription metadata or existing user data if price metadata not available
        if not plan:
            metadata = subscription.get("metadata", {})
            plan = metadata.get("plan") or (user.get("subscription_plan") if user else None)
        
        status = subscription["status"]
        # Keep Stripe semantics: "past_due" is not the same as "canceled".
        # We persist a small set of statuses that the execution gate understands.
        if status in ["active", "trialing"]:
            our_status = "active"
        elif status == "past_due":
            our_status = "past_due"
        elif status in ["canceled", "cancelled"]:
            our_status = "cancelled"
        elif status == "unpaid":
            our_status = "unpaid"
        else:
            # Covers: incomplete, incomplete_expired, paused, etc.
            our_status = status or "expired"
        
        # Calculate dates
        current_period_start = datetime.fromtimestamp(subscription["current_period_start"])
        current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
        cancel_at_period_end = subscription.get("cancel_at_period_end", False)
        
        # Update user subscription with metadata from Stripe
        update_user_subscription(
            user_id=user_id,
            plan=plan,
            status=our_status,
            stripe_subscription_id=subscription_id,
            stripe_price_id=price_id,
            current_period_start=current_period_start.isoformat(),
            current_period_end=current_period_end.isoformat(),
            cancel_at_period_end=cancel_at_period_end
        )
        logger.info(f"Updated subscription for user {user_id}: {plan}, status: {our_status}, price_id: {price_id}")
        return True
    
    elif event_type == "customer.subscription.deleted":
        # Subscription was cancelled
        subscription = data
        subscription_id = subscription["id"]
        
        # For deleted subscriptions, we still check ordering using the event timestamp
        # vs the subscription's deleted timestamp (if available) or updated timestamp
        # Note: Deleted subscriptions may not be retrievable, so we check before trying
        try:
            # Try to retrieve subscription to check timestamp (might fail if already deleted)
            current_subscription = stripe.Subscription.retrieve(subscription_id)
            if not _should_process_subscription_event(event, subscription_id):
                logger.info(f"Skipping out-of-order deletion event {event_id} for subscription {subscription_id}")
                return True
        except stripe.error.StripeError:
            # Subscription already deleted or not found - process the deletion event
            logger.debug(f"Subscription {subscription_id} not found in Stripe, processing deletion event")
        
        # Try to find user by subscription ID
        user = get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            # Fall back to metadata
            metadata = subscription.get("metadata", {})
            user_id = metadata.get("user_id")
            if not user_id:
                logger.warning(f"Could not find user for cancelled subscription {subscription_id}")
                return False
        else:
            user_id = user["id"]
        
        # Set subscription to cancelled
        update_user_subscription(
            user_id=user_id,
            status="cancelled"
        )
        logger.info(f"Cancelled subscription for user {user_id}")
        return True
    
    elif event_type == "invoice.paid":
        # Recurring payment was successful
        invoice = data
        subscription_id = invoice.get("subscription")
        
        if not subscription_id:
            logger.warning("invoice.paid event missing subscription_id")
            return False
        
        # Check event ordering - don't process if event is older than current subscription state
        if not _should_process_subscription_event(event, subscription_id):
            logger.info(f"Skipping out-of-order invoice.paid event {event_id} for subscription {subscription_id}")
            return True  # Return True to acknowledge receipt, but don't process
        
        # Try to find user by subscription ID
        user = get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            logger.warning(f"Could not find user for subscription {subscription_id} in invoice.paid event")
            return False
        
        user_id = user["id"]
        
        # Retrieve subscription to get current period end
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            current_period_start = datetime.fromtimestamp(subscription.current_period_start)
            cancel_at_period_end = subscription.get("cancel_at_period_end", False)
            
            # Get price_id from subscription
            price_id = None
            if subscription.get("items") and len(subscription["items"]["data"]) > 0:
                price_id = subscription["items"]["data"][0].get("price", {}).get("id")
            
            # Update subscription (renewal)
            update_user_subscription(
                user_id=user_id,
                current_period_start=current_period_start.isoformat(),
                current_period_end=current_period_end.isoformat(),
                cancel_at_period_end=cancel_at_period_end,
                status="active",
                stripe_price_id=price_id
            )
            logger.info(f"Updated subscription renewal for user {user_id}, new period end: {current_period_end.isoformat()}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving subscription {subscription_id} in invoice.paid handler: {e}")
            return False
    
    elif event_type == "invoice.payment_failed":
        # Payment attempt failed - update subscription to past_due
        invoice = data
        subscription_id = invoice.get("subscription")
        
        if not subscription_id:
            logger.warning("invoice.payment_failed event missing subscription_id")
            return False
        
        # Check event ordering - don't process if event is older than current subscription state
        if not _should_process_subscription_event(event, subscription_id):
            logger.info(f"Skipping out-of-order invoice.payment_failed event {event_id} for subscription {subscription_id}")
            return True  # Return True to acknowledge receipt, but don't process
        
        # Try to find user by subscription ID
        user = get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            logger.warning(f"Could not find user for subscription {subscription_id} in invoice.payment_failed event")
            return False
        
        user_id = user["id"]
        
        # Retrieve current subscription status from Stripe to ensure accuracy
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_status = subscription.status
            
            # Only update to past_due if subscription is still active or past_due
            # If subscription is already canceled, don't change it
            if current_status in ["active", "past_due", "trialing"]:
                # Update subscription status to past_due
                update_user_subscription(
                    user_id=user_id,
                    status="past_due"
                )
                logger.warning(f"Payment failed for user {user_id}, subscription {subscription_id} - updated to past_due")
                return True
            else:
                # Subscription already in a terminal state (canceled, unpaid, etc.)
                logger.info(f"Payment failed for subscription {subscription_id}, but subscription status is already {current_status} - not updating")
                return True
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving subscription {subscription_id} in invoice.payment_failed handler: {e}")
            # Still update to past_due as a fallback if we can't retrieve from Stripe
            update_user_subscription(
                user_id=user_id,
                status="past_due"
            )
            logger.warning(f"Payment failed for user {user_id}, subscription {subscription_id} - updated to past_due (fallback)")
            return True
    
    # Event not handled
    return False

