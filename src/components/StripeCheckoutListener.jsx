import React, { useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { BASE_API_URL } from '../config/api.js'

/**
 * Persistent listener for Stripe checkout events.
 * This component is always mounted to ensure events are received
 * even when modals are closed or pages are navigated.
 * 
 * On successful checkout, polls subscription status until plan is updated
 * (webhook may take a few seconds to process).
 */
export default function StripeCheckoutListener() {
  const { token, fetchSubscriptionStatus } = useAuth()

  useEffect(() => {
    if (!window.electronAPI || !token) return

    /**
     * Poll subscription status until plan changes from trial to active plan
     * or max attempts reached
     */
    const pollSubscriptionStatus = async (maxAttempts = 15) => {
      if (!token) return

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          // Fetch status directly to check response
          const response = await fetch(`${BASE_API_URL}/api/subscription/status`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          })

          if (response.ok) {
            const data = await response.json()
            const currentPlan = data?.subscription_plan
            
            // Check if subscription has been activated
            if (currentPlan && currentPlan !== 'trial' && currentPlan !== null) {
              // Subscription activated - update context and return
              if (fetchSubscriptionStatus) {
                await fetchSubscriptionStatus()
              }
              return
            }
          }
        } catch (error) {
          console.error('Error polling subscription status:', error)
        }
        
        // Wait 2 seconds before next poll (except on last attempt)
        if (attempt < maxAttempts - 1) {
          await new Promise(resolve => setTimeout(resolve, 2000))
        }
      }
      
      // If we get here, polling timed out - still refresh status once
      if (fetchSubscriptionStatus) {
        await fetchSubscriptionStatus()
      }
      console.warn('Subscription activation polling timed out after 30 seconds')
    }

    const handleSuccess = async (url) => {
      // User returned from successful checkout
      // Poll subscription status until webhook updates it
      await pollSubscriptionStatus()
    }

    const handleCancelled = () => {
      // User cancelled checkout - no action needed
    }

    const handleClosed = () => {
      // Window was closed - poll once to check if payment was completed
      if (token) {
        // Poll subscription status in case payment was completed
        pollSubscriptionStatus(5) // Fewer attempts for window close
      }
    }

    window.electronAPI.onStripeCheckoutSuccess(handleSuccess)
    window.electronAPI.onStripeCheckoutCancelled(handleCancelled)
    window.electronAPI.onStripeCheckoutClosed(handleClosed)

    return () => {
      if (window.electronAPI && window.electronAPI.removeStripeListeners) {
        window.electronAPI.removeStripeListeners()
      }
    }
  }, [token, fetchSubscriptionStatus])

  // This component doesn't render anything
  return null
}

