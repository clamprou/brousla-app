"""Stripe integration for subscription management."""
import os
import logging
from typing import Optional, Tuple
import stripe
from app.config import settings
from app.database import update_user_subscription, get_user_by_id, get_user_by_stripe_subscription_id
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
    Create a Stripe checkout session for subscription.
    
    Args:
        user_id: User ID
        user_email: User email
        plan: Subscription plan ('basic', 'plus', or 'pro')
    
    Returns:
        (checkout_url, session_id)
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
                "plan": plan
            },
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "plan": plan
                }
            }
        )
        
        return session.url, session.id
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise Exception(f"Failed to create checkout session: {str(e)}")


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
    
    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info(f"Received Stripe webhook: {event_type}")
    
    if event_type == "checkout.session.completed":
        # Subscription was created
        session = data
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan")
        subscription_id = session.get("subscription")
        
        if user_id and plan and subscription_id:
            # Get subscription details
            subscription = stripe.Subscription.retrieve(subscription_id)
            customer_id = subscription.customer
            
            # Get price metadata from the subscription's price
            monthly_workflow_limit = None
            plan_from_metadata = plan
            
            if subscription.get("items") and len(subscription["items"]["data"]) > 0:
                price_id = subscription["items"]["data"][0].get("price", {}).get("id")
                if price_id:
                    try:
                        price = stripe.Price.retrieve(price_id)
                        price_metadata = price.get("metadata", {})
                        # Get plan and monthly_workflow_limit from price metadata
                        plan_from_metadata = price_metadata.get("plan", plan)
                        monthly_workflow_limit_str = price_metadata.get("monthly_workflow_limit")
                        if monthly_workflow_limit_str:
                            try:
                                monthly_workflow_limit = int(monthly_workflow_limit_str)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid monthly_workflow_limit in price metadata: {monthly_workflow_limit_str}")
                    except stripe.error.StripeError as e:
                        logger.error(f"Error retrieving price {price_id}: {e}")
            
            # Calculate dates
            start_date = datetime.fromtimestamp(subscription.current_period_start)
            end_date = datetime.fromtimestamp(subscription.current_period_end)
            
            # Update user subscription with metadata from Stripe
            update_user_subscription(
                user_id=user_id,
                plan=plan_from_metadata,
                status="active",
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                monthly_workflow_limit=monthly_workflow_limit
            )
            logger.info(f"Updated subscription for user {user_id}: {plan_from_metadata}, limit: {monthly_workflow_limit}")
            return True
    
    elif event_type == "customer.subscription.updated":
        # Subscription was updated (e.g., plan change, renewal)
        subscription = data
        subscription_id = subscription["id"]
        customer_id = subscription["customer"]
        
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
        
        # Get plan and monthly_workflow_limit from price metadata
        monthly_workflow_limit = None
        plan = None
        
        if subscription.get("items") and len(subscription["items"]["data"]) > 0:
            price_id = subscription["items"]["data"][0].get("price", {}).get("id")
            if price_id:
                try:
                    price = stripe.Price.retrieve(price_id)
                    price_metadata = price.get("metadata", {})
                    # Get plan and monthly_workflow_limit from price metadata
                    plan = price_metadata.get("plan")
                    monthly_workflow_limit_str = price_metadata.get("monthly_workflow_limit")
                    if monthly_workflow_limit_str:
                        try:
                            monthly_workflow_limit = int(monthly_workflow_limit_str)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid monthly_workflow_limit in price metadata: {monthly_workflow_limit_str}")
                except stripe.error.StripeError as e:
                    logger.error(f"Error retrieving price {price_id}: {e}")
        
        # Fallback to subscription metadata or existing user data if price metadata not available
        if not plan:
            metadata = subscription.get("metadata", {})
            plan = metadata.get("plan") or (user.get("subscription_plan") if user else None)
        
        status = subscription["status"]
        
        # Map Stripe status to our status
        if status in ["active", "trialing"]:
            our_status = "active"
        elif status in ["canceled", "unpaid", "past_due"]:
            our_status = "cancelled"
        else:
            our_status = "expired"
        
        # Calculate dates
        start_date = datetime.fromtimestamp(subscription["current_period_start"])
        end_date = datetime.fromtimestamp(subscription["current_period_end"])
        
        # Update user subscription with metadata from Stripe
        update_user_subscription(
            user_id=user_id,
            plan=plan,
            status=our_status,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            monthly_workflow_limit=monthly_workflow_limit
        )
        logger.info(f"Updated subscription for user {user_id}: {plan}, status: {our_status}, limit: {monthly_workflow_limit}")
        return True
    
    elif event_type == "customer.subscription.deleted":
        # Subscription was cancelled
        subscription = data
        subscription_id = subscription["id"]
        
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
    
    # Event not handled
    return False

