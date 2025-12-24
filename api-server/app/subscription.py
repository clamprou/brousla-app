"""Subscription middleware and utilities."""
from fastapi import Depends, HTTPException, status
from typing import Optional
from datetime import datetime

from app.auth import get_current_user
from app.database import check_user_can_execute, get_user_subscription, get_user_usage, get_monthly_workflow_limit_from_stripe


def check_subscription_required(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to check if user has valid subscription for AI API calls.
    
    Raises HTTPException if subscription check fails.
    """
    user_id = current_user["id"]
    can_execute, message = check_user_can_execute(user_id)
    
    if not can_execute:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )
    
    return current_user


def can_user_execute_workflow(user_id: str) -> tuple[bool, str]:
    """
    Check if user can execute workflows.
    
    Returns:
        (can_execute: bool, message: str)
    """
    return check_user_can_execute(user_id)


def get_subscription_status(user_id: str) -> dict:
    """
    Get current subscription status for user.
    
    Returns:
        dict with subscription information
    """
    subscription = get_user_subscription(user_id)
    usage = get_user_usage(user_id)
    
    if not usage:
        return {
            "subscription_plan": None,
            "subscription_status": None,
            "trial_workflows_used": 0,
            "monthly_workflows_used": 0,
            "can_execute": False,
            "message": "Usage record not found"
        }
    
    can_execute, message = check_user_can_execute(user_id)
    
    # If no subscription, user is on trial
    if not subscription:
        trial_used = usage.get("trial_workflows_used", 0)
        usage_info = {
            "type": "trial",
            "used": trial_used,
            "limit": 5,
            "remaining": max(0, 5 - trial_used)
        }
        
        return {
            "subscription_plan": None,
            "subscription_status": None,
            "trial_workflows_used": trial_used,
            "monthly_workflows_used": 0,
            "current_period_start": None,
            "current_period_end": None,
            "last_reset_date": usage.get("last_reset_date"),
            "can_execute": can_execute,
            "message": message,
            "usage": usage_info
        }
    
    # Paid subscription
    subscription_plan = subscription.get("subscription_plan")
    monthly_used = usage.get("monthly_workflows_used", 0)
    
    # Fetch monthly limit from Stripe
    stripe_price_id = subscription.get("stripe_price_id")
    monthly_limit = get_monthly_workflow_limit_from_stripe(stripe_price_id)
    
    if monthly_limit is None:
        # Fallback to default limits (shouldn't happen if Stripe metadata is set correctly)
        if subscription_plan == "basic":
            monthly_limit = 500
        elif subscription_plan == "plus":
            monthly_limit = 2000
        elif subscription_plan == "pro":
            monthly_limit = 5000
        else:
            monthly_limit = 0
    
    usage_info = {
        "type": "monthly",
        "used": monthly_used,
        "limit": monthly_limit,
        "remaining": max(0, monthly_limit - monthly_used)
    }
    
    return {
        "subscription_plan": subscription_plan,
        "subscription_status": subscription.get("subscription_status"),
        "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
        "trial_workflows_used": usage.get("trial_workflows_used", 0),
        "monthly_workflows_used": monthly_used,
        "current_period_start": subscription.get("current_period_start"),
        "current_period_end": subscription.get("current_period_end"),
        "last_reset_date": usage.get("last_reset_date"),
        "can_execute": can_execute,
        "message": message,
        "usage": usage_info
    }

