"""Subscription middleware and utilities."""
from fastapi import Depends, HTTPException, status
from typing import Optional
from datetime import datetime

from app.auth import get_current_user
from app.database import check_user_can_execute, get_user_subscription


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
    if not subscription:
        return {
            "subscription_plan": None,
            "subscription_status": None,
            "trial_executions_used": 0,
            "executions_used_this_month": 0,
            "can_execute": False,
            "message": "No subscription found"
        }
    
    can_execute, message = check_user_can_execute(user_id)
    
    # Determine usage limits
    usage_info = {}
    if subscription["subscription_plan"] == "trial" or subscription["subscription_plan"] is None:
        usage_info = {
            "type": "trial",
            "used": subscription["trial_executions_used"],
            "limit": 5,
            "remaining": max(0, 5 - subscription["trial_executions_used"])
        }
    elif subscription["subscription_plan"] in ("basic", "plus", "pro"):
        # Use monthly_workflow_limit from Stripe metadata, fallback to defaults if not set
        monthly_limit = subscription.get("monthly_workflow_limit")
        if monthly_limit is None:
            # Fallback to default limits (shouldn't happen if Stripe metadata is set correctly)
            if subscription["subscription_plan"] == "basic":
                monthly_limit = 500
            elif subscription["subscription_plan"] == "plus":
                monthly_limit = 2000
            elif subscription["subscription_plan"] == "pro":
                monthly_limit = 5000
            else:
                monthly_limit = 0
        
        executions_used = subscription["executions_used_this_month"]
        usage_info = {
            "type": "monthly",
            "used": executions_used,
            "limit": monthly_limit,
            "remaining": max(0, monthly_limit - executions_used)
        }
    
    return {
        "subscription_plan": subscription["subscription_plan"],
        "subscription_status": subscription["subscription_status"],
        "trial_executions_used": subscription["trial_executions_used"],
        "executions_used_this_month": subscription["executions_used_this_month"],
        "subscription_start_date": subscription["subscription_start_date"],
        "subscription_end_date": subscription["subscription_end_date"],
        "executions_reset_date": subscription["executions_reset_date"],
        "monthly_workflow_limit": subscription.get("monthly_workflow_limit"),
        "can_execute": can_execute,
        "message": message,
        "usage": usage_info
    }

